# modules/broadcast.py
import os
import pytz
import logging
from bson import ObjectId
from telegram import Update
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram.ext import CallbackContext
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaDocument, InputMediaAudio, InputMediaVideo, InputFile


# Access the environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config.env')  # Assuming 'config.env' is in the parent directory
load_dotenv(dotenv_path)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize the logger
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.get_database("Echo")

# Assign the environment variables to variables
AUTHORIZED_USERS = get_env_var_from_db("AUTHORIZED_USERS")

AUTHORIZED_USERS_LIST = [int(user_id) for user_id in AUTHORIZED_USERS.split(',')]

def is_authorized_user(user_id):
    return user_id in AUTHORIZED_USERS_LIST

# Function to set necessary variables from bot.py
def set_bot_variables(user_and_chat_data_collection, REMINDER_CHECK_TIMEZONE):
    globals()['user_and_chat_data_collection'] = user_and_chat_data_collection
    globals()['REMINDER_CHECK_TIMEZONE'] = REMINDER_CHECK_TIMEZONE

def start_broadcast(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not is_authorized_user(user_id):
        update.message.reply_text("""You are not authorized to use this command. 🚫 Only pre-authorized user(s) added during deployment can utilize this command or module.

If you want to create your own Echo, please visit the official repository at [https://github.com/theseekerofficial/Echo] and deploy it on the Render platform or a VPS.""")
        return

    # Path to the existing photo
    photo_path = 'assets/broadcast.jpg'

    # Prepare inline keyboard for broadcast options
    keyboard = [
        [
            InlineKeyboardButton("PM(s) Only", callback_data='broadcast_pm'),
            InlineKeyboardButton("Group(s) Only", callback_data='broadcast_group'),
        ],
        [InlineKeyboardButton("All Chat", callback_data='broadcast_all')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the existing photo with the caption and inline buttons
    with open(photo_path, 'rb') as photo:
        message = update.message.reply_photo(
            photo=photo,
            caption="""🎯Choose a method to proceed broadcast module (To what target you need to send your scheducast)""",
            reply_markup=reply_markup
        )

    # Update the message to handle button clicks
    context.user_data['broadcast_message'] = "Need to broadcast message"
    context.user_data['broadcast_target'] = None
    context.user_data['original_message'] = message.message_id
    
def handle_broadcast_button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_authorized_user(user_id):
        query.answer("You are not authorized to use this command.")
        return

    # Set the broadcast target based on the button clicked
    if query.data == 'broadcast_pm':
        context.user_data['broadcast_target'] = 'pm'
    elif query.data == 'broadcast_group':
        context.user_data['broadcast_target'] = 'group'
    elif query.data == 'broadcast_all':
        context.user_data['broadcast_target'] = 'all'

    # Update the original message to request the broadcast message
    query.edit_message_caption(
        caption="""🏹Now Send or Forward your message to broadcast (Text, Photo, Document, Audio, Gif)""",
        reply_markup=None  # Remove the inline keyboard
    )


# Function to handle broadcast message
def handle_broadcast_message(update: Update, context: CallbackContext) -> None:
    # Check if the broadcast command is active
    if 'broadcast_target' not in context.user_data:
        return

    # Access necessary variables through the bot module
    from bot import user_and_chat_data_collection, REMINDER_CHECK_TIMEZONE
    user_and_chat_data_collection = user_and_chat_data_collection
    REMINDER_CHECK_TIMEZONE = REMINDER_CHECK_TIMEZONE

    # Initialize counters for broadcast summary
    received_pm_users_count = 0
    received_group_chat_count = 0
    not_received_pm_users_count = 0
    not_received_group_chat_count = 0

    # Check if the update is a message and has text, a photo, or a document or a audio
    if update.message and (update.message.text or update.message.photo or update.message.document or update.message.audio or update.message.video):
        # Extract the message text, photo information, and document information and audio information
        message_text = update.message.text
        photo_file_id = None
        photo_caption = None
        document_file_id = None
        document_caption = None 
        audio_file_id = None
        audio_caption= None
        video_file_id = None
        video_caption = None

        if update.message.photo:
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            photo_file_id = photo.file_id

            # Check if the photo has a caption
            if update.message.caption:
                photo_caption = update.message.caption
        
        if update.message.document:
            # Get the document information
            document = update.message.document
            document_file_id = document.file_id

            # Check if the photo has a caption
            if update.message.caption:
                document_caption = update.message.caption

        if update.message.audio:
            # Get the audio information
            audio = update.message.audio
            audio_file_id = audio.file_id

            # Check if the audio has a caption
            if update.message.caption:
                audio_caption = update.message.caption

        if update.message.video:
            # Get the video information
            video = update.message.video
            video_file_id = video.file_id

            # Check if the video has a caption
            if update.message.caption:
                video_caption = update.message.caption
        
        # Get the user's choice from context.user_data
        broadcast_target = context.user_data.get('broadcast_target')

        try:
            # Extract broadcast initiation user info
            user = update.message.from_user
            user_info = f"""🎯 Broadcast Initiated User Info
⚡User's Name: {user.full_name}
⚡Username: @{user.username if user.username else "N/A"}
⚡Telegram ID: {user.id}
⚡Broadcast Type: {broadcast_target.capitalize()} Only
"""

            if broadcast_target == 'pm':
                # Broadcast to bot started PM users only
                pm_users = user_and_chat_data_collection.find({'chat_id': {'$gt': 0}})
                for pm_user in pm_users:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=pm_user['chat_id'], video=video_file_id, caption=video_caption)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=pm_user['chat_id'], audio=audio_file_id, caption=audio_caption)
                        elif document_file_id:
                            context.bot.send_document(chat_id=pm_user['chat_id'], document=document_file_id, caption=document_caption)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=pm_user['chat_id'], photo=photo_file_id, caption=photo_caption)
                        else:
                            context.bot.send_message(chat_id=pm_user['chat_id'], text=message_text)
                        received_pm_users_count += 1
                    except Exception as e:
                        not_received_pm_users_count += 1

                context.user_data.clear()  # Clear user_data after broadcasting

            elif broadcast_target == 'group':
                # Broadcast to bot added group chats only
                group_chats = user_and_chat_data_collection.find({'chat_id': {'$lt': 0}})
                for group_chat in group_chats:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=group_chat['chat_id'], video=video_file_id, caption=video_caption)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=group_chat['chat_id'], audio=audio_file_id, caption=audio_caption)
                        elif document_file_id:
                            context.bot.send_document(chat_id=group_chat['chat_id'], document=document_file_id, caption=document_caption)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=group_chat['chat_id'], photo=photo_file_id, caption=photo_caption)
                        else:
                            context.bot.send_message(chat_id=group_chat['chat_id'], text=message_text)
                        received_group_chat_count += 1
                    except Exception as e:
                        not_received_group_chat_count += 1

                context.user_data.clear()  # Clear user_data after broadcasting

            elif broadcast_target == 'all':
                # Broadcast to both bot started PM users and bot added group chats
                all_chats = user_and_chat_data_collection.find({})
                for chat in all_chats:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=chat['chat_id'], video=video_file_id, caption=video_caption)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=chat['chat_id'], audio=audio_file_id, caption=audio_caption)
                        elif document_file_id:
                            context.bot.send_document(chat_id=chat['chat_id'], document=document_file_id, caption=document_caption)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=chat['chat_id'], photo=photo_file_id, caption=photo_caption)
                        else:
                            context.bot.send_message(chat_id=chat['chat_id'], text=message_text)

                        if chat['chat_id'] > 0:
                            received_pm_users_count += 1
                        else:
                            received_group_chat_count += 1
                    except Exception as e:
                        if chat['chat_id'] > 0:
                            not_received_pm_users_count += 1
                        else:
                            not_received_group_chat_count += 1

                context.user_data.clear()  # Clear user_data after broadcasting

            # Broadcast summary information
            broadcast_summary = f"""Broadcast successfully sent.

{user_info}

📃 Broadcast Summary
❄️Received PM Users Count: {received_pm_users_count}
❄️Received Group Chat Count: {received_group_chat_count}
❄️Received Total Chat Count: {received_pm_users_count + received_group_chat_count}

❄️Not Received PM Users Count: {not_received_pm_users_count}
❄️Not Received Group Chat Count: {not_received_group_chat_count}
❄️Not Received Total Chat Count: {not_received_pm_users_count + not_received_group_chat_count}
"""
            # Log successful broadcast
            logger.info("Broadcast successful. Summary:\n%s", broadcast_summary)

            # Notify the user about the success of the broadcast and provide the summary
            update.message.reply_text(broadcast_summary)
           
            # Reset user_data
            context.user_data.pop('broadcast_target', None)
            context.user_data.pop('broadcast_message', None)

        except Exception as e:
            # Log the error
            logger.error("Error during broadcast: %s", str(e))

            # Notify the user about the error
            update.message.reply_text("Error during broadcast. Please check logs for details.")

            # Reset user_data
            context.user_data.pop('broadcast_target', None)
            context.user_data.pop('broadcast_message', None)
    
# Register the handlers
def register_handlers(dp):
    dp.add_handler(MessageHandler(Filters.command & Filters.regex(r'^/broadcast'), start_broadcast))
    dp.add_handler(CallbackQueryHandler(handle_broadcast_button_click, pattern='^broadcast_(pm|group|all)$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, handle_broadcast_message), group=1)
    dp.add_handler(MessageHandler(Filters.photo & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.document & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.audio & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.video & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    pass
