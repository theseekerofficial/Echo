import os
import pytz
import logging
import calendar
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, Filters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)
MONGODB_URI = os.getenv("MONGODB_URI")
REMINDER_CHECK_TIMEZONE = get_env_var_from_db("REMINDER_CHECK_TIMEZONE")

# Start reminder creation process
def start_reminder_creation(update: Update, context: CallbackContext) -> None:
    years = [str(year) for year in range(datetime.now().year, datetime.now().year + 20)]
    keyboard = [years[i:i+5] for i in range(0, len(years), 5)]
    keyboard_buttons = [[InlineKeyboardButton(year, callback_data=f"year_{year}") for year in row] for row in keyboard]
    keyboard_buttons.append([InlineKeyboardButton("Close", callback_data="sr_close")])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    update.message.reply_text(f'Choose a year for your reminder:\n\nAlso if you did not set your timezone set it using /settimezone command. If you did not set a timezone your reminder will be set for global timezone, *{REMINDER_CHECK_TIMEZONE}*. You can find your timezone use [This link](https://telegra.ph/Choose-your-timezone-02-16) to find your timezone easily🪄', reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# Handle callback queries
def handle_date_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    selection = query.data.split("_")
    data = query.data

    if data == "sr_close":
        query.delete_message()
        return
    
    if selection[0] == "year":
        context.user_data["year"] = int(selection[1])
        ask_for_month(query)
    elif selection[0] == "month":
        month_name = selection[1]
        month_number = datetime.strptime(month_name, '%b').month
        context.user_data["month"] = month_number
        ask_for_day(query, context.user_data["year"], month_number)
    elif selection[0] == "day":
        context.user_data["day"] = int(selection[1])
        ask_for_hour(query)
    elif selection[0] == "hour":
        context.user_data["hour"] = int(selection[1])
        ask_for_minute(query, context)  # Pass context here
    elif selection[0] == "minute":
        context.user_data["minute"] = int(selection[1])
        query.edit_message_text("Please send your reminder message.")

# Ask for month
def ask_for_month(query):
    months = [calendar.month_abbr[month] for month in range(1, 13)]
    keyboard = [months[i:i+3] for i in range(0, len(months), 3)]
    keyboard_buttons = [[InlineKeyboardButton(month, callback_data=f"month_{month}") for month in row] for row in keyboard]
    keyboard_buttons.append([InlineKeyboardButton("Close", callback_data="sr_close")])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    query.edit_message_text(text="Now choose a Month:", reply_markup=reply_markup)


# Ask for day
def ask_for_day(query, year, month):
    last_day = calendar.monthrange(year, month)[1]
    days = [str(day) for day in range(1, last_day + 1)]
    keyboard = [days[i:i+5] for i in range(0, len(days), 5)]
    keyboard_buttons = [[InlineKeyboardButton(day, callback_data=f"day_{day}") for day in row] for row in keyboard]
    keyboard_buttons.append([InlineKeyboardButton("Close", callback_data="sr_close")])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    query.edit_message_text(text="Now choose a Date:", reply_markup=reply_markup)


# Ask for hour
def ask_for_hour(query):
    hours = [f"{hour:02d}" for hour in range(24)]
    keyboard = [hours[i:i+6] for i in range(0, len(hours), 6)]
    keyboard_buttons = [[InlineKeyboardButton(hour, callback_data=f"hour_{hour}") for hour in row] for row in keyboard]
    keyboard_buttons.append([InlineKeyboardButton("Close", callback_data="sr_close")])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    query.edit_message_text(text="Choose an hour for your reminder:", reply_markup=reply_markup)


# Ask for minute
def ask_for_minute(query, context):
    minutes = [f"{minute:02d}" for minute in range(60)]
    keyboard = [minutes[i:i+10] for i in range(0, len(minutes), 10)] 
    flattened_keyboard = [button for row in keyboard for button in row]
    grid_keyboard = [flattened_keyboard[i:i+6] for i in range(0, len(flattened_keyboard), 6)]
    keyboard_buttons = [[InlineKeyboardButton(minute, callback_data=f"minute_{minute}") for minute in row] for row in grid_keyboard]
    keyboard_buttons.append([InlineKeyboardButton("Close", callback_data="sr_close")])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    query.edit_message_text(text="Choose a minute for your reminder:", reply_markup=reply_markup)
    context.user_data['awaiting_reminder_message'] = True

# Capture reminder message from user
def capture_reminder_message(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_reminder_message'):
        try:
            user_id = update.message.from_user.id
            message = update.message.text
            year = context.user_data["year"]
            month = context.user_data["month"]
            day = context.user_data["day"]
            hour = context.user_data["hour"]
            minute = context.user_data["minute"]

            # Construct a naive datetime object from the provided details
            reminder_datetime = datetime(year, month, day, hour, minute)

            # Retrieve user's timezone from the database or use default
            client = MongoClient(MONGODB_URI)
            db = client.Echo
            user_timezone_record = db.user_timezones.find_one({'user_id': user_id}, {'timezone': 1})
            user_timezone = user_timezone_record['timezone'] if user_timezone_record else REMINDER_CHECK_TIMEZONE
            timezone = pytz.timezone(user_timezone)
            
            # Localize the datetime to the user's timezone
            localized_reminder_datetime = timezone.localize(reminder_datetime)

            # Convert the datetime to UTC
            utc_reminder_datetime = localized_reminder_datetime.astimezone(pytz.utc)

            # Store the UTC datetime in reminder_info
            reminder_info = {
                'user_id': user_id,
                'datetime': utc_reminder_datetime,
                'message': message,
            }

            context.user_data['pending_reminder'] = reminder_info

            ask_if_recurring(update, context)
            context.user_data['awaiting_reminder_message'] = False

        except Exception as e:
            error_message = 'An error occurred while setting your reminder. Please try again. ❗'
            update.message.reply_text(error_message)
            logger.error(f"Error setting reminder: {e} ❗")
    else:
        pass

def ask_if_recurring(update: Update, context: CallbackContext) -> None:
    keyboard_buttons = [
        [InlineKeyboardButton("Yes", callback_data="rcr_yes")],
        [InlineKeyboardButton("No", callback_data="rcr_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    update.message.reply_text('Is this a recurring (Repeating) reminder?', reply_markup=reply_markup)

def handle_recurring_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    selection = query.data

    if selection == "rcr_yes":
        ask_for_recurring_period(query)
    elif selection == "rcr_no":
        # Proceed to save the reminder and respond to the user
        save_reminder(context.user_data['pending_reminder'])
        query.edit_message_text(text=f"Your reminder has been set successfully boss. 🫡")
        del context.user_data['pending_reminder']
        context.user_data.pop('awaiting_recurring_selection', None)

def ask_for_recurring_period(query):
    periods = ["Minutely", "Hourly", "Daily", "Weekly", "Monthly", "Yearly"]
    keyboard_buttons = [[InlineKeyboardButton(period, callback_data=f"rcr_period_{period.lower()}")] for period in periods]
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    query.edit_message_text(text="Choose a repeating period:", reply_markup=reply_markup)

def handle_recurring_period_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    period = query.data.split("_")[-1]

    # Add the recurring period to the reminder information
    context.user_data['pending_reminder']['recurring'] = period

    # Save the reminder with recurring information
    save_reminder(context.user_data['pending_reminder'])
    query.edit_message_text(text=f"Your recurring reminder has been set to repeat {period} boss. 🫡")
    del context.user_data['pending_reminder'] 
    context.user_data.pop('awaiting_recurring_selection', None)

def save_reminder(reminder_info):
    client = MongoClient(MONGODB_URI)
    db = client.Echo  
    
    try:
        db.reminders.insert_one(reminder_info)
        logger.info(f"👤 User ID {reminder_info['user_id']} - New reminder stored 📝: {reminder_info}")
        return True
    except Exception as e:
        logger.error(f"Failed to save reminder for User ID {reminder_info['user_id']}: {e}")
        return False

def reminder_creator_handlers(dp):
    dp.add_handler(CallbackQueryHandler(handle_date_selection, pattern='^(year_|month_|day_|hour_|minute_|sr_)'))
    dp.add_handler(CallbackQueryHandler(handle_recurring_selection, pattern='^rcr_(yes|no)$'))
    dp.add_handler(CallbackQueryHandler(handle_recurring_period_selection, pattern='^rcr_period_'))
    dp.add_handler(MessageHandler((Filters.text & ~Filters.command) & (Filters.chat_type.private | Filters.chat_type.groups), capture_reminder_message), group=4)
