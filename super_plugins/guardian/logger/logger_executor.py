#super_plugins/guardian/logger/logger_executor.py
import os
from loguru import logger
from pymongo import MongoClient
from telegram.ext import CallbackContext
from telegram import Update, ParseMode, ChatInviteLink, User

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def log_new_user_join(new_user, invite_link, msg_id, update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    group_chat_name = update.effective_chat.title
    user_name = new_user.first_name
    user_id = new_user.id
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    if msg_id is None:
        see_msg_link = ''
    else:
        chat_id_for_link = str(chat_id)[4:]
        see_msg_link = f"<a href='http://t.me/c/{chat_id_for_link}/{msg_id}'>⬇️ See Message</a>"

    collection = db[str(chat_id)]
    logger_config = collection.find_one({'identifier': 'logger'})

    if logger_config and logger_config.get('logger_state', False) and logger_config.get('log_welcomer', False):
        log_chat = logger_config.get('log_chat', None)
        if log_chat:
            invite_info = fetch_invite_link_info(invite_link, chat_id)

            log_message = (
                f"➕ #New_User_Join 🎉\n\n"
                f"🟢 <i>Chat Name</i>: <b>{group_chat_name}</b> [<code>{chat_id}</code>]\n"
                f"⚜️ <i>User Name</i>: {user_link} [<code>{user_id}</code>]\n"
                f"{invite_info}\n"
                f"{see_msg_link}"
            )
            try:
                context.bot.send_message(chat_id=log_chat, text=log_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to log new user join in chat {log_chat}. Error: {e}")

            context.user_data.pop('invite_link_info', None)
            context.user_data.pop('new_user_info', None)
            context.user_data.pop('msg_id_for_logger', None)

def fetch_invite_link_info(invite_link_or_from_user, chat_id):
    try:
        if isinstance(invite_link_or_from_user, ChatInviteLink):
            link_creator_id = invite_link_or_from_user.creator.id
            link_creator_name = invite_link_or_from_user.creator.first_name
            c_user_link = f"<a href='tg://user?id={link_creator_id}'>{link_creator_name}</a>"
            link_details = [
                f"🔗 <i>Invite link</i>: {invite_link_or_from_user.invite_link}",
                f"👤 <i>Created by</i>: {c_user_link} [<code>{link_creator_id}</code>]",
                f"🏷️ <i>Link name</i>: {invite_link_or_from_user.name if invite_link_or_from_user.name else 'No name specified'}"
            ]
            return '\n'.join(link_details)
        elif isinstance(invite_link_or_from_user, User):
            inviter_id = invite_link_or_from_user.id
            inviter_name = invite_link_or_from_user.first_name
            inviter_user_link = f"<a href='tg://user?id={inviter_id}'>{inviter_name}</a>"
            inviter_details = [
                f"👤 <i>Inviter User</i>: {inviter_user_link} [<code>{inviter_id}</code>]"
            ]
            return '\n'.join(inviter_details)
        else:
            return "🔗 <i>No information about how the user joined the chat</i>"
    except Exception as e:
        logger.error(f"Failed to fetch invite link info for chat {chat_id}. Error: {e}")
        return "🔗 <i>Error fetching invite link information</i>"

def log_user_leave(leaving_user, msg_id, chat, update: Update, context: CallbackContext):
    chat_id = chat.id
    group_chat_name = chat.title
    user_name = leaving_user.first_name
    user_id = leaving_user.id
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    
    if msg_id is None:
        see_msg_link = ''
    else:
        chat_id_for_link = str(chat_id)[4:]
        see_msg_link = f"<a href='http://t.me/c/{chat_id_for_link}/{msg_id}'>⬇️ See Message</a>"

    collection = db[str(chat_id)]
    logger_config = collection.find_one({'identifier': 'logger'})

    if logger_config and logger_config.get('logger_state', False) and logger_config.get('log_goodbye', False):
        log_chat = logger_config.get('log_chat', None)
        if log_chat:

            log_message = (
                f"➖ #User_Left 🏃\n\n"
                f"🔴 <i>Chat Name</i>: <b>{group_chat_name}</b> [<code>{chat_id}</code>]\n"
                f"👤 <i>User Name</i>: {user_link} [<code>{user_id}</code>]\n"
                f"{see_msg_link}"
            )
            
            try:
                context.bot.send_message(chat_id=log_chat, text=log_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to log new user join in chat {log_chat}. Error: {e}")

            context.user_data.pop('need_to_see_msg_id', None)

def log_user_rules_read(read_user, msg_id, chat, update: Update, context: CallbackContext):
    chat_id = chat.id
    group_chat_name = chat.title
    user_name = read_user.first_name
    user_id = read_user.id
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    
    if msg_id is None:
        see_msg_link = ''
    else:
        chat_id_for_link = str(chat_id)[4:]
        see_msg_link = f"<a href='http://t.me/c/{chat_id_for_link}/{msg_id}'>⬇️ See Message</a>"

    collection = db[str(chat_id)]
    logger_config = collection.find_one({'identifier': 'logger'})

    if logger_config and logger_config.get('logger_state', False) and logger_config.get('log_rules', False):
        log_chat = logger_config.get('log_chat', None)
        if log_chat:

            log_message = (
                f"🔖 #User_Rules_Read 📖\n\n"
                f"⚪ <i>Chat Name</i>: <b>{group_chat_name}</b> [<code>{chat_id}</code>]\n"
                f"👤 <i>User Name</i>: {user_link} [<code>{user_id}</code>]\n"
                f"{see_msg_link}"
            )
            
            try:
                context.bot.send_message(chat_id=log_chat, text=log_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to log new user join in chat {log_chat}. Error: {e}")

            context.user_data.pop('ruls_need_to_see_msg_id', None)

def log_user_minor_changes(user, chat, info_text, update: Update, context: CallbackContext):
    chat_id = chat.id
    group_chat_name = chat.title
    user_name = user.first_name
    user_id = user.id
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    collection = db[str(chat_id)]
    logger_config = collection.find_one({'identifier': 'logger'})

    if logger_config and logger_config.get('logger_state', False) and logger_config.get('log_min_chngs', False):
        log_chat = logger_config.get('log_chat', None)
        if log_chat:

            log_message = (
                f"🔁 #Minor_Changes ⛏️\n\n"
                f"🟣 <i>Chat Name</i>: <b>{group_chat_name}</b> [<code>{chat_id}</code>]\n"
                f"👤 <i>User Name</i>: {user_link} [<code>{user_id}</code>]\n"
                f"{info_text}"
            )
            
            try:
                context.bot.send_message(chat_id=log_chat, text=log_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to log new user join in chat {log_chat}. Error: {e}")

def log_captcha_process_stats(user, chat, info_text, context: CallbackContext):
    chat_id = chat.id
    group_chat_name = chat.title
    user_name = user.first_name
    user_id = user.id
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    collection = db[str(chat_id)]
    logger_config = collection.find_one({'identifier': 'logger'})

    if logger_config and logger_config.get('logger_state', False) and logger_config.get('log_captcha', False):
        log_chat = logger_config.get('log_chat', None)
        if log_chat:

            log_message = (
                f"🧠 #Captcha_Status ⛏️\n\n"
                f"⚫ <i>Chat Name</i>: <b>{group_chat_name}</b> [<code>{chat_id}</code>]\n"
                f"👤 <i>User Name</i>: {user_link} [<code>{user_id}</code>]\n"
                f"{info_text}"
            )
            
            try:
                context.bot.send_message(chat_id=log_chat, text=log_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to log new user join in chat {log_chat}. Error: {e}")

