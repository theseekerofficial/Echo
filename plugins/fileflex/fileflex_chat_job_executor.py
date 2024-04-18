# plugins/fileflex/fileflex_chat_job_executor.py
import os
import logging
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, MessageHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client.Echo_FileFlex

def fileflex_chat_job_executor(update: Update, context: CallbackContext):  
    message_got = update.message or update.channel_post
    from plugins.fileflex.fileflex import process_caption
    chat_id = update.effective_chat.id
    fileflex_enabled_str = get_env_var_from_db('FILEFLEX_PLUGIN')
    fileflex_enabled = fileflex_enabled_str.lower() == 'true' if fileflex_enabled_str else False

    if not fileflex_enabled:
        return
    
    chat_job = db.FileFlex_Chat_Jobs.find_one({"chat_id": chat_id})
    if chat_job:
        user_id = chat_job['user_id']

        caption_record = db.FileFlex_G_Captions.find_one({"user_id": user_id})
        buttons_record = db.FileFlex_G_Buttons.find_one({"user_id": user_id})
        if not caption_record or not buttons_record:
            return  

        if message_got and not message_got.text:
            buttons_layout = []
            for line in buttons_record['buttons'].split('\n'):
                row = [InlineKeyboardButton(text=btn.split(" - ")[0].strip(), url=btn.split(" - ")[1].strip()) for btn in line.split('|') if " - " in btn]
                buttons_layout.append(row)

            reply_markup = InlineKeyboardMarkup(buttons_layout)
            caption = process_caption(caption_record['caption'], message_got, context)

            file_id = get_file_id(message_got)
            if file_id:
                send_file(update, context, message_got, chat_id, file_id, caption, reply_markup)

            try:
                context.bot.delete_message(chat_id=chat_id, message_id=message_got.message_id)
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

def get_file_id(message):
    if message.document:
        return message.document.file_id
    elif message.photo:
        return message.photo[-1].file_id  
    elif message.video:
        return message.video.file_id
    elif message.audio:
        return message.audio.file_id
    return None

def send_file(update, context, message_got, chat_id, file_id, caption, reply_markup):
    if message_got.photo:
        photo_file_id = message_got.photo[-1].file_id  
        context.bot.send_photo(chat_id=chat_id, photo=photo_file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif message_got.document:
        document_file_id = message_got.document.file_id
        context.bot.send_document(chat_id=chat_id, document=document_file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif message_got.video:
        video_file_id = message_got.video.file_id
        context.bot.send_video(chat_id=chat_id, video=video_file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif message_got.audio:
        audio_file_id = message_got.audio.file_id
        context.bot.send_audio(chat_id=chat_id, audio=audio_file_id, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
