# super_plugins/guardian/welcomer/welcomer_logic.py
import os
import re
import pytz
from loguru import logger
from datetime import datetime
from pymongo import MongoClient
from telegram.ext import CallbackContext, MessageHandler, Filters
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

from super_plugins.guardian.logger.logger_executor import log_new_user_join
from super_plugins.guardian.captcha.captcha_logic import start_captcha_process

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def handle_chat_member_update(update: Update, context: CallbackContext):
    chat_member_update = update.chat_member
    chat_id = update.chat_member.chat.id
    new_status = chat_member_update.new_chat_member.status
    old_status = chat_member_update.old_chat_member.status
    hi_user_id = chat_member_update.new_chat_member.user.id

    if old_status == 'restricted':
        old_status_user_member = chat_member_update.old_chat_member.is_member
        if old_status_user_member:
            return
    
    if new_status == 'restricted' and old_status == 'restricted':
        old_status_user_member = chat_member_update.old_chat_member.is_member
    
    if old_status in ['left', 'kicked', 'restricted', None] and new_status in ['member', 'restricted']:
        if old_status == 'restricted' and new_status == 'restricted' and old_status_user_member:
            return

        try:
            if chat_member_update.from_user is not None:
                from_user_info = chat_member_update.from_user
                context.user_data[f'inviter_mode_activated'] = True
            else:
                from_user_info = None
        except:
            from_user_info = None

        new_user = chat_member_update.new_chat_member.user
        invt_link_info = chat_member_update.invite_link
        context.user_data['invite_link_info'] = invt_link_info
        context.user_data['new_user_info'] = new_user
        cpt_doc = db[str(chat_id)].find_one({'identifier': 'captcha'})
        
        if cpt_doc and cpt_doc.get('captcha_stats', False):
            start_captcha_process(update, context, new_user, chat_id, invt_link_info, from_user_info)
        else:
            welcome_new_member(chat_id, new_user, invt_link_info, update, context)
        doc = db[str(chat_id)].find_one({'identifier': 'welcomer'})
        if doc:
            wlc_stats = doc.get('welcomer_state', False)
            if not wlc_stats:
                log_new_user_join(new_user, invt_link_info, None, update, context)
        else:
            log_new_user_join(new_user, invt_link_info, None, update, context)
  
def welcome_new_member(chat_id, new_user, invt_link_info, update, context):
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'welcomer'})
    user_joined_link_info = invt_link_info

    if doc and doc.get('welcomer_state', False):
        welcome_msg = doc.get('welcome_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        welcome_buttons = doc.get('welcome_buttons', None)
        topic_id = doc.get('topic_id', None)
        set_pm = doc.get('set_pm', False)

        admin_count = len(context.bot.get_chat_administrators(chat_id)) 
        welcome_msg = replace_placeholders(welcome_msg, new_user, update.effective_chat, admin_count, context)
        reply_markup = parse_buttons(welcome_buttons, update.effective_chat, context) if welcome_buttons else None

        try:
            if media_id and media_type:
                send_media_with_caption(context, chat_id, media_id, media_type, welcome_msg, reply_markup, topic_id)
                msg_id_for_logger = context.user_data['msg_id_for_logger']
                log_new_user_join(new_user, user_joined_link_info, msg_id_for_logger, update, context)
            else:
                message_thread_id = topic_id if topic_id else None
                msg = context.bot.send_message(chat_id=chat_id, text=welcome_msg, parse_mode='HTML', reply_markup=reply_markup, message_thread_id=message_thread_id, disable_web_page_preview=True)
                msg_id_for_logger = msg.message_id
                log_new_user_join(new_user, user_joined_link_info, msg_id_for_logger, update, context)
                logger.info(f"Welcome message sent for {new_user.id} in [{chat_id}]")
        except Exception as e:
            logger.error(f"Failed to send welcome message for chat {chat_id}. Error: {e}")

        if set_pm:
            try:
                if media_id and media_type:
                    send_media_with_caption(context, new_user.id, media_id, media_type, welcome_msg, reply_markup, None)
                else:
                    context.bot.send_message(chat_id=new_user.id, text=welcome_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                    logger.info(f"PM welcome message sent to {new_user.id}")
            except Exception as e:
                logger.error(f"Failed to send PM welcome message to {new_user.id}. The user may not have started the bot. Error: {e}")

def send_media_with_caption(context, chat_id, media_id, media_type, caption, reply_markup, topic_id):
    send_function = {
        'photo': context.bot.send_photo,
        'video': context.bot.send_video,
        'audio': context.bot.send_audio,
        'document': context.bot.send_document
    }
    message_thread_id = topic_id if topic_id else None
    try:
        if media_type in send_function:
            msg = send_function[media_type](chat_id=chat_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup, message_thread_id=message_thread_id, **{media_type: media_id})
            context.user_data['msg_id_for_logger'] = msg.message_id
            logger.info(f"New User Welcome message sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send media with caption for chat {chat_id}, media type {media_type}. Error: {e}")

def parse_buttons(buttons_str, chat, context):
    button_rows = buttons_str.strip().split('\n')
    keyboard = []
    for row in button_rows:
        row_buttons = row.split(' | ')
        keyboard_row = []
        for button in row_buttons:
            parts = button.strip().split(' - ')
            if len(parts) == 2:
                button_text, button_url = parts[0].strip(), parts[1].strip()
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
            elif button.strip().lower() == 'rules':
                button_text = "⚜️Rules ⚜️"
                button_url = f"https://t.me/{context.bot.username}?start=show_rules_{chat.id}"
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
            elif button.strip().lower() == 'invite_link':
                try:
                    chat_for_link = context.bot.get_chat(chat.id)
                    invite_link = chat_for_link.invite_link
                    if not invite_link:
                        invite_link = context.bot.export_chat_invite_link(chat.id)
                    button_text = f"{chat.title}"
                    button_url = invite_link
                except Exception as e:
                    logger.error(f"Failed to create invite link for chat {chat.id}. Error: {e}")
                    continue
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
        if keyboard_row:
            keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)

def preview_welcome_message(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user 
    user_id = user.id
    chat_id = query.data.split('_')[-1]

    chat = context.bot.get_chat(chat_id) 
    admin_count = len(context.bot.get_chat_administrators(chat_id)) 

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'welcomer'})
    topic_id = None

    if doc and doc.get('welcomer_state', False):
        welcome_msg = doc.get('welcome_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        welcome_buttons = doc.get('welcome_buttons', None)

        welcome_msg = replace_placeholders(welcome_msg, user, chat, admin_count, context)
        
        reply_markup = parse_buttons(welcome_buttons, chat, context) if welcome_buttons else None

        try:
            if media_id and media_type:
                send_media_with_caption(context, user_id, media_id, media_type, welcome_msg, reply_markup, topic_id)
                logger.info(f"Preview Snapshot of welcome message sent to [{user_id}]")
            elif welcome_msg:
                context.bot.send_message(chat_id=user_id, text=welcome_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                logger.info(f"Preview Snapshot of welcome message sent to [{user_id}]")
            query.answer("Preview sent to your PM.")
        except Exception as e:
            logger.error(f"Failed to send preview welcome message. Error: {e}")
            query.answer("Failed to send preview. Check logs.")
    else:
        query.answer("No active welcome message configuration or feature not enabled.")

def replace_placeholders(welcome_msg, user, chat, admin_count, context):
    def get_time_in_tz(time_str):
        try:
            timezone = pytz.timezone(time_str)
            return datetime.now(timezone).strftime('%H:%M:%S')
        except pytz.exceptions.UnknownTimeZoneError:
            return datetime.utcnow().strftime('%H:%M:%S')

    def get_date_in_tz(date_str):
        try:
            timezone = pytz.timezone(date_str)
            return datetime.now(timezone).strftime('%Y-%m-%d')
        except pytz.exceptions.UnknownTimeZoneError:
            return datetime.utcnow().strftime('%Y-%m-%d')

    try:
        mention_text = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    except Exception as e:
        logger.info(f"An Error Occurred: {e}")
        mention_text = user.first_name 

    placeholders = {
        '[id]': str(user.id),
        '[first_name]': user.first_name,
        '[second_name]': user.last_name or '',
        '[username]': f"@{user.username}" if user.username else 'No username',
        '[group_name]': chat.title,
        '[group_id]': str(chat.id),
        '[admin_count]': str(admin_count),
        '[mention]': mention_text 
    }

    welcome_msg = re.sub(r'\[time\((.*?)\)\]', lambda m: get_time_in_tz(m.group(1)), welcome_msg)
    welcome_msg = re.sub(r'\[date\((.*?)\)\]', lambda m: get_date_in_tz(m.group(1)), welcome_msg)
    welcome_msg = re.sub(r'\[time\]', datetime.utcnow().strftime('%H:%M:%S'), welcome_msg)
    welcome_msg = re.sub(r'\[date\]', datetime.utcnow().strftime('%Y-%m-%d'), welcome_msg)
    
    for placeholder, value in placeholders.items():
        welcome_msg = welcome_msg.replace(placeholder, value)

    if '[invite_link]' in welcome_msg:
        try:
            chat_for_link = context.bot.get_chat(chat.id)
            invite_link = chat_for_link.invite_link
            if not invite_link:
                invite_link = context.bot.export_chat_invite_link(chat.id)
            welcome_msg = welcome_msg.replace('[invite_link]', invite_link)
        except Exception as e:
            logger.error(f"Failed to fetch invite link for chat {chat.id}. Error: {e}")
            welcome_msg = welcome_msg.replace('[invite_link]', 'No invite link available')

    return welcome_msg
