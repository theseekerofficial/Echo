# super_plugins/guardian/goodbye/goodbye_logic.py
import os
import re
import pytz
from loguru import logger
from datetime import datetime
from pymongo import MongoClient
from telegram.ext import CallbackContext, MessageHandler, Filters
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

from super_plugins.guardian.logger.logger_executor import log_user_leave

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def handle_chat_member_update(update: Update, context: CallbackContext):
    chat_member_update = update.chat_member
    chat = update.chat_member.chat
    chat_id = update.chat_member.chat.id
    new_status = chat_member_update.new_chat_member.status
    old_status = chat_member_update.old_chat_member.status
    bye_user_id = chat_member_update.new_chat_member.user.id
    
    try:
        chat_member = context.bot.get_chat_member(chat_id, bye_user_id)
        try:
            if chat_member.is_member:
                user_still_in_chat = True
            else:
                user_still_in_chat = False
        except Exception:
            user_still_in_chat = True
    except Exception:
        user_still_in_chat = False

    if old_status in ['member', 'administrator', 'restricted', 'creator'] and new_status in ['left', 'kicked', 'restricted']:
        if old_status == 'restricted' and new_status == 'restricted' and user_still_in_chat:
            return

        if old_status in ['member', 'administrator'] and new_status == 'restricted':
            return
            
        leaving_user = chat_member_update.old_chat_member.user
        goodbye_old_member(leaving_user, update, context)
        message_id = context.user_data.get('need_to_see_msg_id', None)
        doc = db[str(chat_id)].find_one({'identifier': 'goodbye'})
        try:
            if doc:
                gby_stats = doc.get('goodbye_state', False)
                if gby_stats:
                    log_user_leave(leaving_user, message_id, chat, update, context)
                else:
                    log_user_leave(leaving_user, None, chat, update, context)
            else:
                log_user_leave(leaving_user, None, chat, update, context)
        except Exception as e:
            logger.error(f"There was an error during user left logging: {e}")
            log_user_leave(leaving_user, None, chat, update, context)

def goodbye_old_member(leaving_user, update, context):
    chat_id = update.effective_chat.id
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'goodbye'})

    if doc and doc.get('goodbye_state', False):
        goodbye_msg = doc.get('goodbye_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        goodbye_buttons = doc.get('goodbye_buttons', None)
        topic_id = doc.get('topic_id', None)
        set_pm = doc.get('set_pm', False)

        admin_count = len(context.bot.get_chat_administrators(chat_id)) 
        goodbye_msg = replace_placeholders(goodbye_msg, leaving_user, update.effective_chat, admin_count, context)
        reply_markup = parse_buttons(goodbye_buttons, update.effective_chat, context) if goodbye_buttons else None

        try:
            if media_id and media_type:
                send_media_with_caption(context, chat_id, media_id, media_type, goodbye_msg, reply_markup, topic_id)
            else:
                message_thread_id = topic_id if topic_id else None
                msg = context.bot.send_message(chat_id=chat_id, text=goodbye_msg, parse_mode='HTML', reply_markup=reply_markup, message_thread_id=message_thread_id, disable_web_page_preview=True)
                context.user_data['need_to_see_msg_id'] = msg.message_id
                logger.info(f"Goodbye message sent for {leaving_user.id} in [{chat_id}]")
        except Exception as e:
            logger.error(f"Failed to send goodbye message for chat {chat_id}. Error: {e}")

        if set_pm:
            try:
                if media_id and media_type:
                    send_media_with_caption(context, leaving_user.id, media_id, media_type, goodbye_msg, reply_markup, None)
                else:
                    context.bot.send_message(chat_id=leaving_user.id, text=goodbye_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                    logger.info(f"PM Goodbye message sent to {leaving_user.id}")
            except Exception as e:
                logger.error(f"Failed to send PM goodbye message to {leaving_user.id}. The user may not have started the bot. Error: {e}")

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
            context.user_data['need_to_see_msg_id'] = msg.message_id
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

def preview_goodbye_message(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user 
    user_id = user.id
    chat_id = query.data.split('_')[-1]

    chat = context.bot.get_chat(chat_id) 
    admin_count = len(context.bot.get_chat_administrators(chat_id)) 

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'goodbye'})
    topic_id = None

    if doc and doc.get('goodbye_state', False):
        goodbye_msg = doc.get('goodbye_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        goodbye_buttons = doc.get('goodbye_buttons', None)

        goodbye_msg = replace_placeholders(goodbye_msg, user, chat, admin_count, context)

        reply_markup = parse_buttons(goodbye_buttons, chat, context) if goodbye_buttons else None

        try:
            if media_id and media_type:
                send_media_with_caption(context, user_id, media_id, media_type, goodbye_msg, reply_markup, topic_id)
                logger.info(f"Preview Snapshot of goodbye message sent to [{user_id}]")
            elif goodbye_msg:
                context.bot.send_message(chat_id=user_id, text=goodbye_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                logger.info(f"Preview Snapshot of goodbye message sent to [{user_id}]")
            query.answer("Preview sent to your PM.")
        except Exception as e:
            logger.error(f"Failed to send preview goodbye message. Error: {e}")
            query.answer("Failed to send preview. Check logs.")
    else:
        query.answer("No active goodbye message configuration or feature not enabled.")

def replace_placeholders(goodbye_msg, user, chat, admin_count, context):
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

    goodbye_msg = re.sub(r'\[time\((.*?)\)\]', lambda m: get_time_in_tz(m.group(1)), goodbye_msg)
    goodbye_msg = re.sub(r'\[date\((.*?)\)\]', lambda m: get_date_in_tz(m.group(1)), goodbye_msg)
    goodbye_msg = re.sub(r'\[time\]', datetime.utcnow().strftime('%H:%M:%S'), goodbye_msg)
    goodbye_msg = re.sub(r'\[date\]', datetime.utcnow().strftime('%Y-%m-%d'), goodbye_msg)

    for placeholder, value in placeholders.items():
        goodbye_msg = goodbye_msg.replace(placeholder, value)

    if '[invite_link]' in goodbye_msg:
        try:
            chat_for_link = context.bot.get_chat(chat.id)
            invite_link = chat_for_link.invite_link
            if not invite_link:
                invite_link = context.bot.export_chat_invite_link(chat.id)
            goodbye_msg = goodbye_msg.replace('[invite_link]', invite_link)
        except Exception as e:
            logger.error(f"Failed to fetch invite link for chat {chat.id}. Error: {e}")
            goodbye_msg = goodbye_msg.replace('[invite_link]', 'No invite link available')
    
    return goodbye_msg
