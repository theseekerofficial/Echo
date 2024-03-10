import os
from pymongo import MongoClient
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from modules.configurator import get_env_var_from_db

MONGODB_URI = get_env_var_from_db("MONGODB_URI")

def show_users(update: Update, context: CallbackContext) -> None:
    owner_id = get_env_var_from_db("OWNER")
    if str(update.effective_user.id) != owner_id:
        update.message.reply_text("You are not authorized to use this command.")
        return

    client = MongoClient(MONGODB_URI)
    db = client['Echo']
    collection = db['user_and_chat_data']

    users = collection.find({"telegram_username": {"$exists": True}})
    groups = collection.find({"group_name": {"$exists": True}})

    base_message = ""
    messages = []
    current_length = 0

    # Add users
    users_count = collection.count_documents({"telegram_username": {"$exists": True}})
    if users_count > 0:
        base_message += "👥 <b>Users:</b>\n"
    for user in users:
        user_line = f"💠 <b>{user['telegram_name']}</b> - <code>{user['user_id']}</code>\n"
        if current_length + len(user_line) + len(base_message) <= 4000:
            base_message += user_line
            current_length += len(user_line)
        else:
            messages.append(base_message)
            base_message = "👥 <b>Users Cont'd:</b>\n" + user_line
            current_length = len(user_line) + len("👥 <b>Users Cont'd:</b>\n")

    # Add groups
    groups_count = collection.count_documents({"group_name": {"$exists": True}})
    if groups_count > 0:
        if current_length + len("\n👥 <b>Groups:</b>\n") > 4000:
            messages.append(base_message)
            base_message = "👥 <b>Groups:</b>\n"
            current_length = len("👥 <b>Groups:</b>\n")
        else:
            base_message += "\n👥 <b>Groups:</b>\n"
            current_length += len("\n👥 <b>Groups:</b>\n")

    for group in groups:
        group_line = f"💠 <b>{group['group_name']}</b> - <code>{group['chat_id']}</code>\n"
        if current_length + len(group_line) <= 4000:
            base_message += group_line
            current_length += len(group_line)
        else:
            messages.append(base_message)
            base_message = "👥 <b>Groups Cont'd:</b>\n" + group_line
            current_length = len(group_line) + len("👥 <b>Groups Cont'd:</b>\n")

    # Add remaining part if exists
    if base_message:
        messages.append(base_message)

    for msg in messages:
        update.message.reply_text(msg, parse_mode=ParseMode.HTML)
