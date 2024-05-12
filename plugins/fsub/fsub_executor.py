import os
import logging
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db
from telegram.ext import MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, ParseMode


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client['Echo']

f_sub_plugin_enabled_str = get_env_var_from_db('F_SUB_PLUGIN')
f_sub_plugin_enabled = f_sub_plugin_enabled_str.lower() == 'true' if f_sub_plugin_enabled_str else False

fsub_info_in_pm_str = get_env_var_from_db('FSUB_INFO_IN_PM')
fsub_info_in_pm = fsub_info_in_pm_str.lower() == 'true' if fsub_info_in_pm_str else False

def check_membership_and_restrict(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    
    user = update.effective_user

    if not f_sub_plugin_enabled:
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        return

    monitoring_chat_id = str(message.chat.id)
    
    if is_user_admin(monitoring_chat_id, user.id, context):
        return
    
    fsub_config = db['Fsub_Configs'].find_one({'monitoring_chat_id': monitoring_chat_id})

    if not fsub_config:
        return

    checking_chat_ids = fsub_config['checking_chat_ids'].split(',')
    non_member_chats = []
    
    for chat_id in checking_chat_ids:
        if not user_is_member(chat_id, user.id, context):
            non_member_chats.append(chat_id)

    if non_member_chats:
        if message and non_member_chats:
            try:
                update.message.delete()
            except:
                logger.warning(f"⚠️ Failed to delete message")
        restrict_user(monitoring_chat_id, user.id, context)
        inform_user(update, non_member_chats, user.id, context, monitoring_chat_id)

def is_user_admin(chat_id: str, user_id: int, context: CallbackContext) -> bool:
    try:
        chat_member = context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except Exception as e:
        logger.warning(f"⚠️ Failed to check admin status for user {user_id} in chat {chat_id}: {e}")
        return False

def user_is_member(chat_id: str, user_id: int, context: CallbackContext) -> bool:
    try:
        chat_member = context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['member', 'restricted', 'administrator', 'creator']
    except Exception as e:
        logger.warning(f"⚠️ Failed to check membership for user {user_id} in chat {chat_id}: {e}")
        return False

def restrict_user(chat_id: str, user_id: int, context: CallbackContext) -> None:
    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=True, 
            can_pin_messages=False
        )
        context.bot.restrict_chat_member(chat_id, user_id, permissions)
        logger.info(f"🔇 User {user_id} has been restricted in chat {chat_id}.")
    except Exception as e:
        logger.error(f"🚫 Failed to restrict user {user_id} in chat {chat_id}: {e}")

def get_invite_link(chat_id: str, context: CallbackContext) -> str:
    try:
        chat = context.bot.get_chat(chat_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
            
        invite_link = chat.invite_link
        if not invite_link:
            invite_link = context.bot.export_chat_invite_link(chat_id)
        return invite_link
    except Exception as e:
        logger.error(f"🚫 Failed to get or generate invite link for chat {chat_id}: {e}")
        return ""

def get_chat_name(chat_id, context):
    try:
        chat = context.bot.get_chat(chat_id)
        return chat.title
    except Exception as e:
        logger.warning(f"⚠️ Warning: Error getting chat name for {chat_id}: {str(e)}")
        return None

def inform_user(update, non_member_chats: list, user_id: int, context: CallbackContext, monitoring_chat_id: str) -> None:
    chat_links = []

    for chat_id in non_member_chats:
        chat_name = get_chat_name(chat_id, context) or chat_id
        invite_link = get_invite_link(chat_id, context)
        if invite_link:
            chat_links.append((chat_name, invite_link))

    if not chat_links:
        logger.warning("No invite links available to inform the user.")
        return

    buttons = []
    for i in range(0, len(chat_links), 2):
        row = chat_links[i:i+2]
        buttons.append([InlineKeyboardButton(name, url=link) for name, link in row])

    buttons.append([InlineKeyboardButton("Try Now", callback_data=f"try_now_{user_id}_{monitoring_chat_id}")])
    reply_markup = InlineKeyboardMarkup(buttons)

    m_chat_name = chat_name = get_chat_name(monitoring_chat_id, context) or monitoring_chat_id
    
    user_name = update.effective_user.first_name
    inform_text = f"🚨 Attention: <a href='tg://user?id={user_id}'>{user_name}</a>\n\n🔴 You need to subscribe to the following chats in order to use <code>{m_chat_name}</code> group.\n\n🔴 After joining the below chat(s), click 'Try Now' to unmute yourself in <code>{m_chat_name}</code>:"

    if fsub_info_in_pm:
        try:
            context.bot.send_message(chat_id=user_id, text=inform_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to inform user {user_id} in PM: {e}")

        try:
            chat_name = get_chat_name(monitoring_chat_id, context) or monitoring_chat_id
            context.bot.send_message(chat_id=monitoring_chat_id, 
                                     text=inform_text, 
                                     reply_markup=reply_markup, 
                                     parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to inform user {user_id} in monitoring chat {monitoring_chat_id}: {e}")

    else:
        try:
            chat_name = get_chat_name(monitoring_chat_id, context) or monitoring_chat_id
            context.bot.send_message(chat_id=monitoring_chat_id, 
                                     text=inform_text, 
                                     reply_markup=reply_markup, 
                                     parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to inform user {user_id} in monitoring chat {monitoring_chat_id}: {e}")

def handle_try_now(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    parts = query.data.split('_')
    if len(parts) < 4:
        logger.error(f"Unexpected callback data format: {query.data}")
        return

    try:
        user_id = int(parts[2])
    except ValueError:
        logger.error(f"Invalid user ID extracted from callback data: {parts[1]}")
        return

    clicking_user_id = query.from_user.id

    if user_id != clicking_user_id:
        query.answer("Mind your own business 😑", show_alert=True)
        return    
    
    monitoring_chat_id = parts[3]
    chat_name = get_chat_name(monitoring_chat_id, context) or monitoring_chat_id   
    
    fsub_config = db['Fsub_Configs'].find_one({'monitoring_chat_id': monitoring_chat_id})
    if not fsub_config:
        logger.error("Monitoring chat configuration not found.")
        return
    
    checking_chat_ids = fsub_config['checking_chat_ids'].split(',')
    non_member_chats = [chat_id for chat_id in checking_chat_ids if not user_is_member(chat_id, user_id, context)]
    user_name = update.effective_user.first_name
    
    if not non_member_chats:
        unmute_user(monitoring_chat_id, user_id, context)
        query.message.delete()
        if fsub_info_in_pm:
            try:
                context.bot.send_message(chat_id=user_id, text=f"🫂 You have been unmuted in <code>{chat_name}</code>.", parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to inform user {user_id} in PM: {e}")
            context.bot.send_message(chat_id=monitoring_chat_id, text=f"<a href='tg://user?id={user_id}'>{user_name}</a>, 🫂 You have been unmuted in <code>{chat_name}</code>.", parse_mode=ParseMode.HTML)
        else:
            context.bot.send_message(chat_id=monitoring_chat_id, text=f"<a href='tg://user?id={user_id}'>{user_name}</a>, 🫂 You have been unmuted in <code>{chat_name}</code>.", parse_mode=ParseMode.HTML)
        
    else:
        query.message.delete()
        inform_user(update, non_member_chats, user_id, context, monitoring_chat_id)

def unmute_user(chat_id: str, user_id: int, context: CallbackContext) -> None:
    try:
        permissions = ChatPermissions(can_send_messages=True,
                                      can_send_media_messages=True,
                                      can_send_polls=True,
                                      can_send_other_messages=True,
                                      can_add_web_page_previews=True,
                                      can_change_info=False,
                                      can_invite_users=True,
                                      can_pin_messages=False)
        context.bot.restrict_chat_member(chat_id, user_id, permissions)
        logger.info(f"🔊 User {user_id} has been unmuted in chat {chat_id}.")
    except Exception as e:
        logger.error(f"🚫 Failed to unmute user {user_id} in chat {chat_id}: {e}")
