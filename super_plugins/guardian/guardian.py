# super_plugins/guardian/guardian.py
import os
from loguru import logger
from telegram import Update
from pymongo import MongoClient
from telegram.ext import CallbackContext
from modules.configurator import get_env_var_from_db
from telegram.ext import CommandHandler, MessageHandler, Filters

def is_user_admin(bot, user_id, chat_id):
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

def is_bot_admin(bot, chat_id):
    bot_member = bot.get_chat_member(chat_id, bot.id)
    return bot_member.status in ['administrator', 'creator']

def handle_reload(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    group_name = update.message.chat.title

    if update.message.chat.type not in ['group', 'supergroup']:
        return

    if not is_user_admin(context.bot, user_id, chat_id):
        update.message.reply_text("You need to be an admin to use this command.")
        return

    if not is_bot_admin(context.bot, chat_id):
        update.message.reply_text("I need to be an admin with necessary permissions to work properly!")
        return

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client['Echo_Guardian']
    collection = db['Group_Details']

    admin_ids = [admin.user.id for admin in context.bot.get_chat_administrators(chat_id)]
    
    collection.update_one(
        {'chat_id': chat_id},
        {'$set': {'admin_ids': admin_ids, 'group_name': group_name}},
        upsert=True
    )
    update.message.reply_text("🛑 Group Settings Reloaded\n🛑 Admin List Updated.\n🛑 Group Permission Updated")

def setup_guardian(dp):
    from super_plugins.guardian.menu import setup_menu
    dp.add_handler(CommandHandler("reload", handle_reload, Filters.chat_type.groups))
    setup_menu(dp)
