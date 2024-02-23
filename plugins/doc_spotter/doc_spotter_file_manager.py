import os
import time
import logging
from pymongo import MongoClient
from telegram.ext import CallbackContext, MessageHandler, Filters, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["Echo_Doc_Spotter"]

last_process_time_per_user = {}

# Handler for "Delete Indexed Files" button
def delete_indexed_files_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    text = "Okay, now forward me the file(s) you want to delete from your file collection.\n\n<b>🚨 To prevent Echo from being rate-limited on Telegram, there is a one-second delay implemented for the deletion of multiple files.</b>\n\n<u><b>⚠️Remember to send /sdsfd when you are done deleting files from the database.</b></u>"
    query.edit_message_text(text=text, parse_mode='HTML')
    context.user_data['expecting_file_for_deletion'] = True

# Process forwarded files for deletion
def process_file_deletion(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    minimal_interval = 1
    now = time.time()
    last_process_time = last_process_time_per_user.get(user_id, now)

    time_since_last_process = now - last_process_time
    if time_since_last_process < minimal_interval:
        time_to_sleep = minimal_interval - time_since_last_process
        time.sleep(time_to_sleep)

    last_process_time_per_user[user_id] = time.time()
    
    if context.user_data.get('expecting_file_for_deletion', False):
        file_names = extract_file_names(update.message)

        if not file_names:
            update.message.reply_text("Please forward a file with a recognizable name.⚠️")
            return

        collection_name = f"DS_collection_{user_id}"
        collection = db[collection_name]

        if collection_name not in db.list_collection_names():
            update.message.reply_text("You do not have any file collection in my database. Create one champ! 😉")
            return

        deleted_files = []
        not_found_files = []

        for file_name in file_names:
            result = collection.delete_one({"file_name": file_name})
            if result.deleted_count > 0:
                deleted_files.append(file_name)
            else:
                not_found_files.append(file_name)

        if deleted_files:
            update.message.reply_text(f"✅ Deleted successfully: `{', '.join(deleted_files)}`", parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        if not_found_files:
            update.message.reply_text(f"⚠️ No matching file found for: `{', '.join(not_found_files)}`", parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

        # This ensures the bot is ready for the next file immediately
        context.user_data['expecting_file_for_deletion'] = True

def extract_file_names(message):
    """Extracts file names from a message that may contain various types of media."""
    file_names = []
    if message.document:
        file_names.append(message.document.file_name)
    if message.photo:
        file_names.append(message.photo[-1].file_name) 
    if message.video:
        file_names.append(message.video.file_name)
    if message.audio:
        file_names.append(message.audio.file_name)
    if message.animation:
        file_names.append(message.animation.file_name)

    return file_names

def done_forwarding_files(update: Update, context: CallbackContext) -> None:
    # Reset the flag
    context.user_data['expecting_file_for_deletion'] = False
    update.message.reply_text("⭕Doc Spotter File Deletion Stopped!")
