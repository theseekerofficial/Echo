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
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaDocument, InputMediaAudio, InputMediaVideo, InputFile, ParseMode


# Access the environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config.env')  # Assuming 'config.env' is in the parent directory
load_dotenv(dotenv_path)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
        update.message.reply_text("You are not authorized to use this command.")
        return

    photo_path = 'assets/broadcast.jpg'
    
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='setup_url_buttons_yes')],
        [InlineKeyboardButton("No", callback_data='setup_url_buttons_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(photo_path, 'rb') as photo:
        message = update.message.reply_photo(
            photo=photo,
            caption="Do you want to set URL Buttons for this Broadcast message?",
            reply_markup=reply_markup
        )

    context.user_data['original_message_id'] = message.message_id

def handle_url_buttons_setup_response(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_authorized_user(user_id):
        query.answer("You are not authorized to use this command.✖️")
        return

    photo_path = 'assets/broadcast.jpg'
    
    if query.data == 'setup_url_buttons_yes':
        # User wants to setup URL buttons
        context.user_data['setting_up_url_buttons'] = True
        new_caption = "_Now Send Your Buttons List_\n\n📝 *How to Setup Buttons* 📝\n\nPlease send your button list in this format. Each button and its corresponding URL should be enclosed in square brackets `[]`, with the button text and URL separated by ` - `.\n\nFor buttons on the same row, place them side by side within the brackets. For buttons on new lines, separate them with a newline.\n\nExample:\n`[Button1 - Link1][Button2 - Link2]`\n`[Button3 - Link3]`\n\nThis will create two buttons on the first row and one button on the second row. You can add as many as you like following this pattern. ✨"
        query.edit_message_caption(caption=new_caption, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
        logger.info("URL buttons setup initiated.")
    elif query.data == 'setup_url_buttons_no':
        proceed_to_broadcast_method_choice(update, context, photo_path)

    context.user_data['awaiting_broadcast_message'] = True
    logger.info("Awaiting broadcast message after URL button setup.")

def proceed_to_broadcast_method_choice(update: Update, context: CallbackContext, photo_path=None) -> None:
    keyboard = [
        [InlineKeyboardButton("PM(s) Only", callback_data='broadcast_pm')],
        [InlineKeyboardButton("Group(s) Only", callback_data='broadcast_group')],
        [InlineKeyboardButton("All Chat", callback_data='broadcast_all')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if photo_path:
        context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['original_message_id'],
            caption="🎯Choose a method to proceed broadcast module (To what target you need to send your scheducast)",
            reply_markup=reply_markup
        )
    else:
        pass

def handle_broadcast_button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_authorized_user(user_id):
        query.answer("You are not authorized to use this command.")
        return

    if query.data == 'broadcast_pm':
        context.user_data['broadcast_target'] = 'pm'
    elif query.data == 'broadcast_group':
        context.user_data['broadcast_target'] = 'group'
    elif query.data == 'broadcast_all':
        context.user_data['broadcast_target'] = 'all'

    query.edit_message_caption(
        caption="""🏹Now Send or Forward your message to broadcast (Text, Photo, Document, Audio, Gif)""",
        reply_markup=None  # Remove the inline keyboard
    )

# Function to handle broadcast message
def handle_broadcast_message(update: Update, context: CallbackContext) -> None:

    if not context.user_data.get('awaiting_broadcast_message', False):
        return 

    logger.info("Processing broadcast message.")
    
    if context.user_data.get('setting_up_url_buttons'):
        input_text = update.message.text.strip()
        rows = input_text.split('\n')
        buttons = []

        try:
            for row in rows:
                if row.startswith('[') and row.endswith(']'):
                    button_defs = row[1:-1].split('][')
                    button_row = []
                    for button_def in button_defs:
                        name, separator, url = button_def.partition(' - ')
                        if separator != ' - ' or not name or not url:
                            raise ValueError("Invalid button format detected.")
                        button_row.append(InlineKeyboardButton(text=name.strip(), url=url.strip()))
                    buttons.append(button_row)
                else:
                    raise ValueError("Each button definition must be enclosed in square brackets.")

            # Store the structured list of buttons in user_data
            context.user_data['url_buttons'] = buttons
            context.user_data.pop('setting_up_url_buttons')  # No longer setting up URL buttons

        except ValueError as e:
            error_message = "⚠️ <b>Invalid Button Format Detected!</b> ⚠️\n\n" \
                            "Please ensure each button and its URL are correctly formatted and enclosed in square brackets <code>[]</code>, " \
                            "with the button text and URL separated by <code> - </code>.\n\n" \
                            "For example:\n" \
                            "<code>[Button1 - Link1][Button2 - Link2]</code>\n" \
                            "<code>[Button3 - Link3]</code>\n\n" \
                            "For buttons on the same row, place them side by side within the brackets. " \
                            "Separate buttons on new lines with a newline (<code>\\n</code>).\n\n" \
                            "Please try again with the correct format. ✨"

            context.bot.send_message(chat_id=update.effective_chat.id, text=error_message, parse_mode='HTML')
            return


        keyboard = [
            [InlineKeyboardButton("PM(s) Only", callback_data='broadcast_pm')],
            [InlineKeyboardButton("Group(s) Only", callback_data='broadcast_group')],
            [InlineKeyboardButton("All Chat", callback_data='broadcast_all')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        photo_path = 'assets/broadcast.jpg'
        with open(photo_path, 'rb') as photo:
            update.message.reply_photo(
                photo=photo,
                caption="🎯Choose a method to proceed with the broadcast module (To what target do you need to send your broadcast?)",
                reply_markup=reply_markup
            )

        return
        
    if 'broadcast_target' not in context.user_data:
        return
    
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
                if 'url_buttons' in context.user_data:
                    reply_markup = InlineKeyboardMarkup(context.user_data['url_buttons'])
                else:
                    reply_markup = None
                for pm_user in pm_users:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=pm_user['chat_id'], video=video_file_id, caption=video_caption, reply_markup=reply_markup)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=pm_user['chat_id'], audio=audio_file_id, caption=audio_caption, reply_markup=reply_markup)
                        elif document_file_id:
                            context.bot.send_document(chat_id=pm_user['chat_id'], document=document_file_id, caption=document_caption, reply_markup=reply_markup)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=pm_user['chat_id'], photo=photo_file_id, caption=photo_caption, reply_markup=reply_markup)
                        else:
                            context.bot.send_message(chat_id=pm_user['chat_id'], text=message_text, reply_markup=reply_markup)
                        received_pm_users_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send broadcast to chat_id {pm_user['chat_id']}: {e}")
                        not_received_pm_users_count += 1

                context.user_data.clear()  # Clear user_data after broadcasting

            elif broadcast_target == 'group':
                # Broadcast to bot added group chats only
                group_chats = user_and_chat_data_collection.find({'chat_id': {'$lt': 0}})
                if 'url_buttons' in context.user_data:
                    reply_markup = InlineKeyboardMarkup(context.user_data['url_buttons'])
                else:
                    reply_markup = None
                for group_chat in group_chats:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=group_chat['chat_id'], video=video_file_id, caption=video_caption, reply_markup=reply_markup)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=group_chat['chat_id'], audio=audio_file_id, caption=audio_caption, reply_markup=reply_markup)
                        elif document_file_id:
                            context.bot.send_document(chat_id=group_chat['chat_id'], document=document_file_id, caption=document_caption, reply_markup=reply_markup)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=group_chat['chat_id'], photo=photo_file_id, caption=photo_caption, reply_markup=reply_markup)
                        else:
                            context.bot.send_message(chat_id=group_chat['chat_id'], text=message_text, reply_markup=reply_markup)
                        received_group_chat_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send broadcast to chat_id {group_chat['chat_id']}: {e}")
                        not_received_group_chat_count += 1

                context.user_data.clear()  # Clear user_data after broadcasting

            elif broadcast_target == 'all':
                # Broadcast to both bot started PM users and bot added group chats
                all_chats = user_and_chat_data_collection.find({})
                if 'url_buttons' in context.user_data:
                    reply_markup = InlineKeyboardMarkup(context.user_data['url_buttons'])
                else:
                    reply_markup = None
                for chat in all_chats:
                    try:
                        if video_file_id:
                            context.bot.send_video(chat_id=chat['chat_id'], video=video_file_id, caption=video_caption, reply_markup=reply_markup)
                        elif audio_file_id:
                            context.bot.send_audio(chat_id=chat['chat_id'], audio=audio_file_id, caption=audio_caption, reply_markup=reply_markup)
                        elif document_file_id:
                            context.bot.send_document(chat_id=chat['chat_id'], document=document_file_id, caption=document_caption, reply_markup=reply_markup)
                        elif photo_file_id:
                            context.bot.send_photo(chat_id=chat['chat_id'], photo=photo_file_id, caption=photo_caption, reply_markup=reply_markup)
                        else:
                            context.bot.send_message(chat_id=chat['chat_id'], text=message_text, reply_markup=reply_markup)

                        if chat['chat_id'] > 0:
                            received_pm_users_count += 1
                        else:
                            received_group_chat_count += 1
                    except Exception as e:
                        if chat['chat_id'] > 0:
                            logger.error(f"Failed to send broadcast to PM chat_id {chat['chat_id']}: {e}")
                            not_received_pm_users_count += 1
                        else:
                            logger.error(f"Failed to send broadcast to group chat_id {chat['chat_id']}: {e}")
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
    context.user_data.pop('awaiting_broadcast_message', None)  # Reset the state
    
# Register the handlers
def register_handlers(dp):
    dp.add_handler(MessageHandler(Filters.command & Filters.regex(r'^/broadcast'), start_broadcast))
    dp.add_handler(CallbackQueryHandler(handle_broadcast_button_click, pattern='^broadcast_(pm|group|all)$'))
    dp.add_handler(CallbackQueryHandler(handle_url_buttons_setup_response, pattern='^setup_url_buttons_(yes|no)$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, handle_broadcast_message), group=1)
    dp.add_handler(MessageHandler(Filters.photo & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.document & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.audio & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    dp.add_handler(MessageHandler(Filters.video & ~Filters.command & Filters.chat_type.private, handle_broadcast_message))
    pass
