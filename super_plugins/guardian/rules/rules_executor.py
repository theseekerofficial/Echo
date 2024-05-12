# super_plugins/guardian/rules/rules_executor.py
import os
import re
import pytz
from loguru import logger
from datetime import datetime
from pymongo import MongoClient
from telegram.ext import CallbackContext, MessageHandler, Filters
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

from super_plugins.guardian.logger.logger_executor import log_user_rules_read

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def rules_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_obj = context.bot.get_chat(user_id)
    chat_obj = context.bot.get_chat(chat_id)
    message_id = update.message.message_id

    if update.effective_chat.type not in ['group', 'supergroup']:
        return

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'rules'})

    if doc and doc.get('rules_state', False):
        rules_msg = doc.get('rules_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        rules_buttons = doc.get('rules_buttons', None)
        set_pm = doc.get('set_pm', False)

        rules_msg = replace_placeholders(rules_msg, update.effective_user, update.effective_chat, len(context.bot.get_chat_administrators(chat_id)), context)
        reply_markup = parse_buttons(rules_buttons, update.effective_chat, context) if rules_buttons else None

        if set_pm:
            try:
                if media_id and media_type:
                    context.bot.send_message(chat_id=user_id, text=f"⚜️ Group Rules of  <code>{update.effective_chat.title}</code> ⚜️", parse_mode='HTML')
                    send_media_with_caption(context, user_id, media_id, media_type, rules_msg, reply_markup, None, None)
                    logger.info(f"Rules message send to [{user_id}]")
                else:
                    context.bot.send_message(chat_id=user_id, text=f"⚜️ Group Rules of  <code>{update.effective_chat.title}</code> ⚜️", parse_mode='HTML')
                    context.bot.send_message(chat_id=user_id, text=rules_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                    logger.info(f"Rules message send to [{user_id}]")

                bot_username = context.bot.username
                bot_link = f"https://t.me/{bot_username}"
                check_rls_text = f"<i>Check {update.effective_chat.title} rules in PM</i> "
                reply_message = f"<a href='{bot_link}'>{check_rls_text}</a>."
                user_link = f"<a href='tg://user?id={user_id}'>{user_obj.first_name}</a>"
                msg = context.bot.send_message(chat_id=chat_id, text=f"{user_link}, {reply_message}", parse_mode='HTML', reply_to_message_id=message_id, disable_web_page_preview=True)
                log_user_rules_read(user_obj, msg.message_id, chat_obj, update, context)
                return
            except Exception as e:
                logger.error(f"Failed to send rules message to user PM [{user_id}]. Error: {e}")

        if media_id and media_type:
            send_media_with_caption(context, chat_id, media_id, media_type, rules_msg, reply_markup, None, message_id)
            msg_id = context.user_data['ruls_need_to_see_msg_id']
            log_user_rules_read(user_obj, msg_id, chat_obj, update, context)
            logger.info(f"Rules message send to [{chat_id}]")
        else:
            msg = context.bot.send_message(chat_id=chat_id, text=rules_msg, parse_mode='HTML', reply_markup=reply_markup, reply_to_message_id=message_id, disable_web_page_preview=True)
            log_user_rules_read(user_obj, msg.message_id, chat_obj, update, context)
            logger.info(f"Rules message send to [{chat_id}]")
    else:
        logger.info(f"No active rules configuration or feature not enabled for chat {chat_id}")

def send_media_with_caption(context, chat_id, media_id, media_type, caption, reply_markup, topic_id, rply_message_id):
    send_function = {
        'photo': context.bot.send_photo,
        'video': context.bot.send_video,
        'audio': context.bot.send_audio,
        'document': context.bot.send_document
    }
    message_thread_id = topic_id if topic_id else None
    try:
        if media_type in send_function:
            msg = send_function[media_type](chat_id=chat_id, caption=caption, parse_mode='HTML', reply_markup=reply_markup, reply_to_message_id=rply_message_id, message_thread_id=message_thread_id, **{media_type: media_id})
            context.user_data['ruls_need_to_see_msg_id'] = msg.message_id
            logger.info(f"Rules message sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send media with caption for chat {chat_id}, media type {media_type}. Error: {e}")

def parse_buttons(buttons_str, chat, context):
    button_rows = buttons_str.strip().split('\n')
    keyboard = []
    for row in button_rows:
        row_buttons = row.split('|')
        keyboard_row = []
        for button in row_buttons:
            parts = button.strip().split('-')
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

def preview_rules_message(update: Update, context: CallbackContext):
    query = update.callback_query
    rply_msg_id = query.message.message_id
    user = query.from_user 
    user_id = user.id
    chat_id = query.data.split('_')[-1]

    chat = context.bot.get_chat(chat_id) 
    admin_count = len(context.bot.get_chat_administrators(chat_id)) 

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'rules'})
    topic_id = None

    if doc and doc.get('rules_state', False):
        rules_msg = doc.get('rules_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        rules_buttons = doc.get('rules_buttons', None)

        rules_msg = replace_placeholders(rules_msg, user, chat, admin_count, context)

        reply_markup = parse_buttons(rules_buttons, chat, context) if rules_buttons else None

        try:
            if media_id and media_type:
                send_media_with_caption(context, user_id, media_id, media_type, rules_msg, reply_markup, topic_id, rply_msg_id)
                logger.info(f"Preview Snapshot of rules message sent to [{user_id}]")
            elif rules_msg:
                context.bot.send_message(chat_id=user_id, text=rules_msg, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                logger.info(f"Preview Snapshot of rules message sent to [{user_id}]")
            query.answer("Preview sent to your PM.")
        except Exception as e:
            logger.error(f"Failed to send preview rules message. Error: {e}")
            query.answer("Failed to send preview. Check logs.")
    else:
        query.answer("No active rules message configuration or feature not enabled.")

def replace_placeholders(rules_msg, user, chat, admin_count, context):
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

    rules_msg = re.sub(r'\[time\((.*?)\)\]', lambda m: get_time_in_tz(m.group(1)), rules_msg)
    rules_msg = re.sub(r'\[date\((.*?)\)\]', lambda m: get_date_in_tz(m.group(1)), rules_msg)
    rules_msg = re.sub(r'\[time\]', datetime.utcnow().strftime('%H:%M:%S'), rules_msg)
    rules_msg = re.sub(r'\[date\]', datetime.utcnow().strftime('%Y-%m-%d'), rules_msg)

    for placeholder, value in placeholders.items():
        rules_msg = rules_msg.replace(placeholder, value)

    if '[invite_link]' in rules_msg:
        try:
            chat_for_link = context.bot.get_chat(chat.id)
            invite_link = chat_for_link.invite_link
            if not invite_link:
                invite_link = context.bot.export_chat_invite_link(chat.id)
            rules_msg = rules_msg.replace('[invite_link]', invite_link)
        except Exception as e:
            logger.error(f"Failed to fetch invite link for chat {chat.id}. Error: {e}")
            rules_msg = rules_msg.replace('[invite_link]', 'No invite link available')
    
    return rules_msg

def send_rules_to_pm(chat_id, user_id, update, context):
    chat = context.bot.get_chat(chat_id)
    user_obj = context.bot.get_chat(user_id)
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'rules'})

    if doc and doc.get('rules_state', False):
        rules_msg = doc.get('rules_msg', '')
        media_id = doc.get('media_id', None)
        media_type = doc.get('media_type', None)
        rules_buttons = doc.get('rules_buttons', None)

        rules_msg = replace_placeholders(rules_msg, context.bot.get_chat_member(chat_id, user_id).user, chat, len(context.bot.get_chat_administrators(chat_id)), context)
        reply_markup = parse_buttons(rules_buttons, chat, context) if rules_buttons else None

        if media_id and media_type:
            context.bot.send_message(chat_id=user_id, text=f"⚜️ Group Rules of  <code>{context.bot.get_chat(chat_id).title}</code> ⚜️", parse_mode='HTML')
            send_media_with_caption(context, user_id, media_id, media_type, rules_msg, reply_markup, None, None)
            log_user_rules_read(user_obj, None, chat, update, context)
        else:
            context.bot.send_message(chat_id=user_id, text=f"⚜️ Group Rules of  <code>{context.bot.get_chat(chat_id).title}</code> ⚜️", parse_mode='HTML')
            context.bot.send_message(chat_id=user_id, text=rules_msg, parse_mode='HTML', reply_markup=reply_markup)
            log_user_rules_read(user_obj, None, chat, update, context)
    else:
        context.bot.send_message(chat_id=user_id, text=f"No active rules configuration or feature not enabled for <code>{context.bot.get_chat(chat_id).title}</code>.", parse_mode='HTML')
