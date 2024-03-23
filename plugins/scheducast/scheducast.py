import os
import re
import pytz
import logging
from bson import ObjectId
from dateutil import parser
from pymongo import MongoClient
from datetime import datetime, timedelta
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

# Import the authorized users from config.env
def get_authorized_users():
    users_str = get_env_var_from_db("AUTHORIZED_USERS")
    if users_str:
        try:
            return [int(user_id.strip()) for user_id in users_str.split(",") if user_id.strip()]
        except ValueError:
            logger.warning(f"Invalid AUTHORIZED_USERS value in database: {users_str}.")
            return []
    else:
        return []  

AUTHORIZED_USERS = get_authorized_users()

SCHEDULE_BROADCASTS_COLLECTION = 'schedule_broadcasts'

def start_scheducast(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in AUTHORIZED_USERS:
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        update.message.reply_text("""You are not authorized to use this command. 🚫 Only pre-authorized user(s) added during deployment can utilize this command or module.

If you want to create your own Echo, please visit the official repository at [https://github.com/theseekerofficial/Echo] and deploy it on the Render platform or a VPS.""")
        return

    context.user_data['in_scheducast_setup'] = False

    photo_path = 'assets/scheducast.jpg'

    keyboard = [
        [InlineKeyboardButton("Setup a Scheducast!", callback_data='setup')],
        [InlineKeyboardButton("My Scheducasts", callback_data='my_scheducasts')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(photo_path, 'rb') as photo_file:
        update.message.reply_photo(photo=photo_file, caption="Select an option in Scheducast module:", reply_markup=reply_markup)

def setup_scheducast(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        logger.warning(f"Unauthorized button click attempt by user {user_id} in scheducast module.")
        query.answer("You are not authorized to use this command.")
        return

    query.answer()

    context.user_data['in_scheducast_setup'] = True

    keyboard = [
        [InlineKeyboardButton("Bot started PM users only", callback_data='pm')],
        [InlineKeyboardButton("Group Chats only", callback_data='group')],
        [InlineKeyboardButton("All Chats", callback_data='all')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['scheducast_setup'] = {}

    query.edit_message_caption("""Select the broadcast type (To what target you need to send your scheducast) :""", reply_markup=reply_markup)

def select_broadcast_type(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if 'scheducast_setup' not in context.user_data:
        query.answer("You are not authorized for this click.")
        return

    context.user_data['scheducast_setup']['broadcast_type'] = query.data

    # Show message for getting broadcast schedule date and time
    query.edit_message_caption("""⏱️Provide the broadcast schedule date and time (YYYY-MM-DD HH:MM:SS) with /scd cmd. 

Example: /scd 2024-01-01 12:00:00""")

def get_broadcast_schedule(update: Update, context: CallbackContext) -> None:
    # Check if the user is in the process of setting up a Scheducast
    if not context.user_data.get('in_scheducast_setup', False):
        # If not, ignore the command
        return

    # Extract the command text (/scd)
    command_text = update.message.text[len("/scd"):].strip()

    try:
        provided_datetime = parser.parse(command_text)

        provided_datetime_utc = provided_datetime.astimezone(pytz.UTC)

        context.user_data['scheducast_setup']['schedule_datetime'] = provided_datetime_utc

        update.message.reply_text("""✍️Provide the message you want to broadcast with /scm:

Example: /scm This is Echo's Sechducast Module""")
    except ValueError:
        logger.error(f"Error parsing datetime: {command_text}", exc_info=True)
        update.message.reply_text("Invalid date and time format. Please provide a valid format (e.g.,/scd YYYY-MM-DD HH:MM:SS).")

def complete_scheducast_setup(update: Update, context: CallbackContext) -> None:
    # Check if the user is in the process of setting up a Scheducast
    if not context.user_data.get('in_scheducast_setup', False):
        return

    command_text = update.message.text[len("/scm"):].strip()

    # Check if 'scheducast_setup' key is present in context.user_data
    if 'scheducast_setup' not in context.user_data:
        update.message.reply_text("Scheducast setup data not found. Please start the setup again.")
        return

    context.user_data['scheducast_setup']['broadcast_data'] = command_text

    context.user_data['scheducast_setup']['user_id'] = update.message.from_user.id

    db = context.bot_data.get('db')
    if db is not None:
        try:
            db['schedule_broadcasts'].insert_one(context.user_data['scheducast_setup'])
            logger.info(f"Successfully stored Scheducast setup data in the database. User: {update.message.from_user.id}")
        except Exception as e:
            logger.error(f"Error storing scheducast setup data in MongoDB: {e}", exc_info=True)
    else:
        logger.error("Database connection is not available.")
    
    context.user_data.pop('scheducast_setup', None)
    context.user_data['in_scheducast_setup'] = False

    # Show "Scheducast Setup Completed!" message
    update.message.reply_text("Scheducast Setup Completed!✅")

def my_scheducasts(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if user_id not in AUTHORIZED_USERS:
        query.answer("You are not authorized to use this command.")
        return

    db = context.bot_data.get('db')
    if db is not None:
        try:
            user_broadcasts = list(db['schedule_broadcasts'].find({'user_id': user_id}))

            if not user_broadcasts:
                query.answer("You don't have any scheduled broadcasts.")
                return

            buttons = [
                [InlineKeyboardButton(broadcast['broadcast_data'], callback_data=str(broadcast['_id']))]
                for broadcast in user_broadcasts
            ]

            reply_markup = InlineKeyboardMarkup(buttons)
            
            query.answer()

            query.edit_message_reply_markup(reply_markup)

        except Exception as e:
            logger.error(f"Error fetching user's scheduled broadcasts from MongoDB: {e}", exc_info=True)
            query.answer("An error occurred while fetching your scheduled broadcasts.")
    else:
        logger.error("Database connection is not available.")
        query.answer("An error occurred while fetching your scheduled broadcasts.")

def show_schedule_details(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    selected_broadcast_id = query.data

    db = context.bot_data.get('db')
    if db is not None:
        try:
            selected_broadcast_id = ObjectId(selected_broadcast_id)

            selected_schedule = db['schedule_broadcasts'].find_one({'_id': selected_broadcast_id})

            print("Selected Schedule:", selected_schedule)

            if selected_schedule:
                broadcast_type = selected_schedule.get('broadcast_type', 'N/A')
                schedule_datetime = selected_schedule.get('schedule_datetime', 'N/A')
                broadcast_data = selected_schedule.get('broadcast_data', 'N/A')
                user_id = selected_schedule.get('user_id', 'N/A')

                current_time_utc = datetime.utcnow()
                remaining_time = schedule_datetime - current_time_utc

                delete_button = InlineKeyboardButton("Delete this Scheducast 🚮", callback_data=f'delete_{selected_broadcast_id}')

                message = (f"**Broadcast Type:** {broadcast_type}\n"
                           f"**Schedule Datetime:** {schedule_datetime}\n"
                           f"**Broadcast Data:** {broadcast_data}\n"
                           f"**User ID:** {user_id}\n"
                           f"**Remaining Time until Scheducast Trigger:** {remaining_time}")

                inline_keyboard = [[delete_button]]
                reply_markup = InlineKeyboardMarkup(inline_keyboard)

                query.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

            else:
                query.message.reply_text("Selected broadcast not found.")

        except Exception as e:
            logger.error(f"Error fetching schedule details from MongoDB: {e}", exc_info=True)
            query.message.reply_text("An error occurred while fetching schedule details.")
    else:
        logger.error("Database connection is not available.")
        query.message.reply_text("An error occurred while fetching schedule details.")

def delete_scheducast(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    selected_broadcast_id = query.data.split('_')[1]

    db = context.bot_data.get('db')
    if db is not None:
        try:
            selected_broadcast_id = ObjectId(selected_broadcast_id)

            result = db['schedule_broadcasts'].delete_one({'_id': selected_broadcast_id})

            if result.deleted_count == 1:
                new_message = "RIP Your Scheducast :-🧨 ——> 💣 ——> 💥 ——> ☠️"
                query.message.edit_text(new_message, parse_mode=ParseMode.MARKDOWN)

                query.answer("Scheducast deleted successfully✅")
            else:
                query.answer("Scheducast not found or already deleted.")

        except Exception as e:
            logger.error(f"Error deleting scheducast from MongoDB: {e}", exc_info=True)
            query.message.reply_text("An error occurred while deleting the scheducast.")
    else:
        logger.error("Database connection is not available.")
        query.message.reply_text("An error occurred while deleting the scheducast.")

def setup_dispatcher(dp, db):    
    dp.add_handler(token_system.token_filter(CommandHandler("scheducast", start_scheducast)))
    dp.add_handler(CallbackQueryHandler(setup_scheducast, pattern='^setup$'))
    dp.add_handler(CallbackQueryHandler(select_broadcast_type, pattern='^(pm|group|all)$'))
    dp.add_handler(CommandHandler("scd", get_broadcast_schedule))
    dp.add_handler(CommandHandler("scm", complete_scheducast_setup))
    dp.add_handler(CallbackQueryHandler(my_scheducasts, pattern='^my_scheducasts$'))
    dp.add_handler(CallbackQueryHandler(show_schedule_details, pattern='^[0-9a-fA-F]{24}$'))
    dp.add_handler(CallbackQueryHandler(delete_scheducast, pattern='^delete_[0-9a-fA-F]{24}$'))

    dp.bot_data['db'] = db
