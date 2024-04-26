import os
import logging
from telegram import Update
from pymongo import MongoClient
from telegram.error import TelegramError
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, MessageHandler, Filters, Dispatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["Echo_Clonegram"]

def process_message(update: Update, context: CallbackContext) -> None:
    clonegram_plugin_enabled_str = get_env_var_from_db('CLONEGRAM_PLUGIN')
    clonegram_plugin_enabled = clonegram_plugin_enabled_str.lower() == 'true' if clonegram_plugin_enabled_str else False

    if not clonegram_plugin_enabled:
        return

    message = update.message or update.channel_post
    chat_id = str(message.chat.id)

    tasks = db["Clonegram_Tasks"].find({"source_chat_id": chat_id})

    for task in tasks:
        destination_chat_id = task['destination_chat_id']
        topic_id = task.get('topic_id', None)  
        clone_type = task.get('clone_type', 'forward')

        message_type_allowed = (
            (message.text and task['allow_text'] == "true") or
            (message.photo and task['allow_photos'] == "true") or
            (message.video and task['allow_videos'] == "true") or
            (message.document and task['allow_documents'] == "true") or
            (message.audio and task['allow_audios'] == "true") or
            (message.sticker and task['allow_stickers'] == "true")
        )

        if not message_type_allowed:
            logger.info(f"🚫 Message type is not allowed for cloning or forwarding. Chat ID: {chat_id}")
            continue

        try:
            kwargs = {}
            if topic_id:
                kwargs['message_thread_id'] = topic_id

            if clone_type == "forward":
                message.forward(destination_chat_id, **kwargs)
            elif clone_type == "clone":
                if message.text:
                    context.bot.send_message(destination_chat_id, message.text, **kwargs)
                elif message.photo:
                    context.bot.send_photo(destination_chat_id, photo=message.photo[-1].file_id, caption=message.caption, **kwargs)
                elif message.video:
                    context.bot.send_video(destination_chat_id, video=message.video.file_id, caption=message.caption, **kwargs)
                elif message.document:
                    context.bot.send_document(destination_chat_id, document=message.document.file_id, caption=message.caption, **kwargs)
                elif message.audio:
                    context.bot.send_audio(destination_chat_id, audio=message.audio.file_id, caption=message.caption, **kwargs)
                elif message.sticker:
                    context.bot.send_sticker(destination_chat_id, sticker=message.sticker.file_id, **kwargs)
            else:
                logger.warning(f"⚠️ Unknown clone type: {clone_type}")
        except TelegramError as e:
            logger.error(f"❌ Error processing message from {chat_id} to {destination_chat_id}: {e}")

def register_cg_executor_handlers(dp):
    dp.add_handler(MessageHandler(Filters.all & (Filters.update.message | Filters.update.channel_post), process_message), group=9)
