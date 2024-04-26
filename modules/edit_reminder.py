# edit_reminder.py
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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
REMINDER_CHECK_TIMEZONE = get_env_var_from_db("REMINDER_CHECK_TIMEZONE")

def edit_reminders(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    user_reminders = list(reminders_collection.find({'user_id': user_id}))

    if not user_reminders:
        update.message.reply_text('You have no reminders to edit.')
        return

    reminder_list = "\n".join([f"{i + 1}. {reminder['message']} - /editreminder_{str(reminder['_id'])}" for i, reminder in enumerate(user_reminders)])
    if user_reminders:
        update.message.reply_text(f"""Your reminders List:\n\n{reminder_list}\n\nClick on the need to edit reminder's cmd string to start editing process.✨""")
    else:
        update.message.reply_text('You have no reminders to edit.')

def edit_specific_reminder(update: Update, context: CallbackContext) -> None:
    logger.info("Entering edit_specific_reminder function") 
    user_id = update.message.from_user.id

    command_text = update.message.text
    parts = command_text.split('_')

    if len(parts) != 2:
        logger.error("Invalid command format. No reminder ID found.")
        update.message.reply_text("Invalid command format. Please use /editreminders to view and choose a valid reminder.")
        return

    reminder_id = parts[1]

    logger.info(f"User ID: {user_id}")
    logger.info(f"Reminder ID: {reminder_id}")

    logger.info(f"Received /editreminder command with ID: {reminder_id}")
    
    reminder_id_object = ObjectId(reminder_id)

    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    specific_reminder = reminders_collection.find_one({'user_id': user_id, '_id': reminder_id_object})

    if specific_reminder:
        update.message.reply_text(f'Editing Reminder:\n{specific_reminder["datetime"].strftime("%Y-%m-%d %H:%M:%S")} - {specific_reminder["message"]}')
        update.message.reply_text('Send the new date, time, and reminder message in the format /er YYYY-MM-DD HH:MM:SS New reminder message.')
        context.user_data['editing_reminder_id'] = reminder_id
    else:
        update.message.reply_text('Invalid reminder ID. Please use /editreminders to view and choose a valid reminder.')
    print("Exiting edit_specific_reminder function")

def edit_reminder(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    if 'editing_reminder_id' in context.user_data:
        reminder_id = context.user_data['editing_reminder_id']

        try:
            command_text = update.message.text[len("/er"):].strip()

            date_str, time_str, *message_parts = command_text.split()
            datetime_str = f"{date_str} {time_str}"
            new_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

            user_timezone_record = db.user_timezones.find_one({'user_id': user_id}, {'timezone': 1})
            user_timezone = user_timezone_record['timezone'] if user_timezone_record else REMINDER_CHECK_TIMEZONE
            timezone = pytz.timezone(user_timezone)
            new_datetime = timezone.localize(new_datetime)

            new_message = ' '.join(message_parts)

            reminders_collection.update_one({'user_id': user_id, '_id': ObjectId(reminder_id)},
                                             {'$set': {'datetime': new_datetime, 'message': new_message}})

            update.message.reply_text(f'Reminder edited successfully:\n{new_datetime.strftime("%Y-%m-%d %H:%M:%S")} - {new_message}')

            del context.user_data['editing_reminder_id']

        except (ValueError, IndexError):
            
            update.message.reply_text('Invalid command format. Use /er followed by the date and time in the format '
                                      'YYYY-MM-DD HH:MM:SS and the new reminder message. '
                                      'For example, /er 2024-01-01 12:00:00 New reminder message.')
    else:
        update.message.reply_text('No reminder selected for editing. Use /editreminders to choose a reminder.')
