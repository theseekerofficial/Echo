# super_plugins/guardian/menu.py
import os
from loguru import logger
from pymongo import MongoClient
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent, ParseMode

from .welcomer.welcomer import setup_welcomer
from .goodbye.goodbye import setup_goodbye
from .rules.rules import setup_rules
from .logger.logger import setup_logger
from .captcha.captcha import setup_captcha

from .logger.logger_executor import log_user_minor_changes

def show_group_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        user_id = query.from_user.id
    else:
        user_id = update.message.from_user.id
        if update.message.chat.type != "private":
            message = "This command is limited to Bot PM due to Security concerns. Click below to start a chat in the bot pm."
            keyboard = [[InlineKeyboardButton("Start Chat", url=f"https://t.me/{context.bot.username}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(message, reply_markup=reply_markup)
            return
    
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client['Echo_Guardian']
    collection = db['Group_Details']

    count = collection.count_documents({'admin_ids': user_id})
    if count > 0:
        groups = collection.find({'admin_ids': user_id})
        keyboard = [
            [InlineKeyboardButton(group['group_name'], callback_data=f"manage_{group['chat_id']}")]
            for group in groups
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query:
            query.edit_message_text("""<code>█▓▒▒░░░ Ｇｕａｒｄｉａｎ ░░░▒▒▓█</code>
            
👥 Choose a group chat:\n\n<i><b>⚡ If your group chat is not showing here make sure we both are admins in your target group chat. if still not showing, send /reload command in your group chat and try again</b></i>""", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:    
            update.message.reply_text("""<code>█▓▒▒░░░ Ｇｕａｒｄｉａｎ ░░░▒▒▓█</code>
            
👥 Choose a group chat:\n\n<i><b>⚡ If your group chat is not showing here make sure we both are admins in your target group chat. if still not showing, send /reload command in your group chat and try again</b></i>""", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text("🤷 You are not an admin in any groups registered with this bot.\n\n<i><b>⚡ If your group chat is not showing in here make sure we both are admins in your target group chat. if still not showing, send /reload command in your group chat and try again</b></i>", parse_mode=ParseMode.HTML)

def is_user_admin(bot, user_id, chat_id):
    chat_member = bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ['administrator', 'creator']

def is_bot_admin(bot, chat_id):
    bot_member = bot.get_chat_member(chat_id, bot.id)
    return bot_member.status in ['administrator', 'creator']

def group_button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user = context.bot.get_chat(user_id)
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id) 

    if not is_user_admin(context.bot, user_id, chat_id) or not is_bot_admin(context.bot, chat_id):
        query.answer("Operation failed due to permission issues. Make sure we both are admins in the group chat.", show_alert=True)
        return

    try:
        chat = context.bot.get_chat(chat_id)
        chat_name = chat.title
        keyboard = [
            [InlineKeyboardButton("⫸ Welcomer ⫷", callback_data=f"set_welcomer_{chat_id}"), InlineKeyboardButton("⫷ Goodbye ⫸", callback_data=f"set_goodbye_{chat_id}")],
            [InlineKeyboardButton("✅ Rules ❎", callback_data=f"set_rules_{chat_id}"), InlineKeyboardButton("⌚ Logger 📝", callback_data=f"set_logger_{chat_id}")],
            [InlineKeyboardButton("🧩 Captcha 🧮", callback_data=f"set_captcha_{chat_id}")],
            [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"grd_back_to_main_main_prime_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=f"Guardian Moderation Menu for <code>{chat_name}</code>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        info_text = f"🚩 {user.first_name} [<code>{user.id}</code>] accessed the moderation menu in Echo"
        
    except Exception as e:
        logger.error(f"Failed to fetch chat details: {e}")
        query.answer("Failed to access chat details. Ensure the bot is still a member and has the correct permissions.", show_alert=True)
        info_text = f"⚠️ {user.first_name} [<code>{user_id}</code>] tried to access the moderation menu in Echo, but failed due to <code>{e}</code>"
    
    log_user_minor_changes(user, chat, info_text, update, context)

def setup_menu(dp):
    dp.add_handler(CommandHandler("guardian", show_group_menu))
    dp.add_handler(CallbackQueryHandler(group_button_callback, pattern=r"^manage_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(group_button_callback, pattern=r"^grd_back_to_primary_menu_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(show_group_menu, pattern=r"^grd_back_to_main_main_prime_menu$"))
    setup_welcomer(dp)
    setup_goodbye(dp)
    setup_rules(dp)
    setup_logger(dp)
    setup_captcha(dp)
