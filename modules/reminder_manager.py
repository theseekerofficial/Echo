# modules/reminder_manager.py
import os
import pytz
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone
from telegram.constants import PARSEMODE_MARKDOWN
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton


# Load environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

# Access the environment variables
MONGODB_URI = os.getenv("MONGODB_URI")

# Set up MongoDB connection
client = MongoClient(MONGODB_URI)
db = client.get_database("Echo")

def handle_delreminder_command(update, context):
    user_id = (
        update.callback_query.from_user.id
        if hasattr(update.callback_query, "from_user")
        else update.message.from_user.id
    )
    reminders = get_user_reminders(user_id)

    if not reminders:
        if hasattr(update.callback_query, "edit_message_text"):
            update.callback_query.edit_message_text("You have no reminders to delete.")
        else:
            update.message.reply_text("You have no reminders to delete.")
        return

    # Prepare reminder buttons
    keyboard = [
        [
            InlineKeyboardButton(
                reminder["message"],
                callback_data=f"delreminder:{reminder['_id']}",
            )
        ]
        for reminder in reminders
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Determine whether to edit a message or send a new one
    if hasattr(update.callback_query, "edit_message_text"):
        # Edit the original message with updated reminders
        update.callback_query.edit_message_text(
            "Choose a Reminder to Delete:", reply_markup=reply_markup
        )
    else:
        # Send a new message with reminders
        update.message.reply_text(
            "Choose a Reminder to Delete:", reply_markup=reply_markup
        )

def get_user_reminders(user_id):
    current_time = datetime.now(timezone.utc)
    return list(db.reminders.find({'user_id': user_id, 'datetime': {'$gt': current_time}}))

def confirm_delete(update, context):
    query = update.callback_query
    reminder_id = ObjectId(query.data.split(":")[1])

    # Retrieve the reminder details
    reminder = db.reminders.find_one({'_id': reminder_id})

    # Prepare confirmation message with "Yes" and "No" buttons
    confirmation_message = f"{reminder['message']}\n\nAre you sure you want to delete this reminder?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"yes:{reminder_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit the original message to show the confirmation message
    query.edit_message_text(confirmation_message, reply_markup=reply_markup, parse_mode=PARSEMODE_MARKDOWN)

def handle_confirmation(update, context):
    query = update.callback_query
    data = query.data

    if data.startswith("yes"):
        reminder_id = ObjectId(data.split(":")[1])

        # Delete the reminder from the database
        db.reminders.delete_one({'_id': reminder_id})

        # Send a confirmation message
        query.answer("Reminder deleted successfully.")

    elif data == "no":
        # Send a positive response
        query.answer("OK :)")

        # Delete the "Are you sure you want to delete this reminder?" message
        query.edit_message_text("Reminder deletion canceled.")
        return

    # Send the "Choose a Reminder to Delete:" message with buttons
    handle_delreminder_command(update, context)

# Add a CallbackQueryHandler to handle button presses
callback_query_handler = CallbackQueryHandler(confirm_delete, pattern='^delreminder:')
