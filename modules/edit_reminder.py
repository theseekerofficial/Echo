# edit_reminder.py
import os
import pytz
from bson import ObjectId
from telegram import Update
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram.ext import CallbackContext
from modules.configurator import get_env_var_from_db


# Load environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
REMINDER_CHECK_TIMEZONE = get_env_var_from_db("REMINDER_CHECK_TIMEZONE")

def edit_reminders(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    # Retrieve the user's reminders
    user_reminders = list(reminders_collection.find({'user_id': user_id}))

    if not user_reminders:
        update.message.reply_text('You have no reminders to edit.')
        return

    # Display user's reminders with unique IDs
    reminder_list = "\n".join([f"{i + 1}. {reminder['message']} - /editreminder_{str(reminder['_id'])}" for i, reminder in enumerate(user_reminders)])
    if user_reminders:
        update.message.reply_text(f"""Your reminders List:\n\n{reminder_list}\n\nClick on the need to edit reminder's cmd string to start editing process.✨""")
    else:
        update.message.reply_text('You have no reminders to edit.')

def edit_specific_reminder(update: Update, context: CallbackContext) -> None:
    print("Entering edit_specific_reminder function") 
    user_id = update.message.from_user.id

    # Extract the reminder_id directly from the command text
    command_text = update.message.text
    parts = command_text.split('_')

    if len(parts) != 2:
        print("Invalid command format. No reminder ID found.")
        update.message.reply_text("Invalid command format. Please use /editreminders to view and choose a valid reminder.")
        return

    reminder_id = parts[1]

    # Debugging statements
    print(f"User ID: {user_id}")
    print(f"Reminder ID: {reminder_id}")

    # Debugging statement
    print(f"Received /editreminder command with ID: {reminder_id}")
    
    # Convert the reminder_id to ObjectId
    reminder_id_object = ObjectId(reminder_id)

    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    # Retrieve the specific reminder
    specific_reminder = reminders_collection.find_one({'user_id': user_id, '_id': reminder_id_object})

    if specific_reminder:
        update.message.reply_text(f'Editing Reminder:\n{specific_reminder["datetime"].strftime("%Y-%m-%d %H:%M:%S")} - {specific_reminder["message"]}')
        update.message.reply_text('Send the new date, time, and reminder message in the format /er YYYY-MM-DD HH:MM:SS New reminder message.')
        context.user_data['editing_reminder_id'] = reminder_id
    else:
        update.message.reply_text('Invalid reminder ID. Please use /editreminders to view and choose a valid reminder.')
    print("Exiting edit_specific_reminder function")

# Function to handle the /er command
def edit_reminder(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    reminders_collection = db['reminders']

    # Check if the user is in the process of editing a reminder
    if 'editing_reminder_id' in context.user_data:
        # User is editing a reminder, proceed with the edit
        reminder_id = context.user_data['editing_reminder_id']

        try:
            # Extract command text and remove the command itself (/er)
            command_text = update.message.text[len("/er"):].strip()

            # Split the command text into date, time, and message
            date_str, time_str, *message_parts = command_text.split()
            datetime_str = f"{date_str} {time_str}"
            new_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

            # Get the user's time zone from MongoDB (default to REMINDER_CHECK_TIMEZONE if not set)
            user_timezone_record = db.user_timezones.find_one({'user_id': user_id}, {'timezone': 1})
            user_timezone = user_timezone_record['timezone'] if user_timezone_record else REMINDER_CHECK_TIMEZONE
            timezone = pytz.timezone(user_timezone)
            new_datetime = timezone.localize(new_datetime)

            # Combine remaining parts as the new reminder message
            new_message = ' '.join(message_parts)

            # Update the specific reminder in MongoDB
            reminders_collection.update_one({'user_id': user_id, '_id': ObjectId(reminder_id)},
                                             {'$set': {'datetime': new_datetime, 'message': new_message}})

            update.message.reply_text(f'Reminder edited successfully:\n{new_datetime.strftime("%Y-%m-%d %H:%M:%S")} - {new_message}')

            # Clear the editing reminder ID from user_data
            del context.user_data['editing_reminder_id']

        except (ValueError, IndexError):
            
            update.message.reply_text('Invalid command format. Use /er followed by the date and time in the format '
                                      'YYYY-MM-DD HH:MM:SS and the new reminder message. '
                                      'For example, /er 2024-01-01 12:00:00 New reminder message.')
    else:
        update.message.reply_text('No reminder selected for editing. Use /editreminders to choose a reminder.')
