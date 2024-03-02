# bot.py
## Don't edit this file unless you know what you are doing!
from modules.configurator import load_and_store_env_vars, bsettings_command, bsettings_button_callback, show_env_value_callback, handle_new_env_value, edit_env_callback, get_env_var_from_db, close_config_callback
load_and_store_env_vars()

import os
import io
import sys
import pytz
import logging
import subprocess
import http.server
import socketserver

from bson import ObjectId 
from dotenv import load_dotenv
from pymongo import MongoClient
from threading import Thread, Event
from dateutil.relativedelta import relativedelta
from datetime import datetime, timezone, timedelta

from ringtone_manager import send_ringtones 
from reminders_manager import show_user_reminders

from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, CallbackQueryHandler
from telegram import Update, ParseMode, Message, User, Chat, BotCommand, BotCommandScopeDefault, Bot, InlineKeyboardButton, InlineKeyboardMarkup

from modules.utilities.database_info import database_command
from modules.utilities.info_fetcher import register_id_command
from modules.encrypted_data import encrypted_creator_info, decrypt
from modules.utilities.overview import overview_command, register_overview_handlers
from modules.edit_reminder import edit_reminders, edit_specific_reminder, edit_reminder
from modules.reminder_creator import reminder_creator_handlers, start_reminder_creation
from modules.help import help_command, handle_help_button_click, handle_back_button_click
from modules.restarter import check_for_updates, restart_bot, write_update_status_to_mongo
from modules.reminder_manager import handle_delreminder_command, callback_query_handler, handle_confirmation
from modules.broadcast import register_handlers as broadcast_register_handlers, set_bot_variables as broadcast_set_bot_variables, handle_broadcast_message


from plugins.scheducast import scheducast
from plugins.shiftx.shiftx import register_shiftx_handlers
from plugins.calculators.calculator import setup_calculator
from plugins.logo_gen.logo_generator import handle_logogen, button
from plugins.calculators.sci_calculator import setup_sci_calculator
from plugins.doc_spotter.doc_spotter_indexer import setup_ds_dispatcher
from plugins.commit_detector.commit_detector import setup_commit_detector
from plugins.scheducast.scheducast_check import check_scheduled_broadcasts
from plugins.gemini.gemini_chat_bot import toggle_chatbot, handle_chat_message
from plugins.doc_spotter.doc_spotter_executor import setup_ds_executor_dispatcher
from plugins.telegraph.telegraph_up import setup_dispatcher as setup_telegraph_up
from plugins.gemini.gemini import handle_gemini_command, handle_mygapi_command, handle_delmygapi_command, handle_showmygapi_command, analyze4to_handler

creator_credits = """🎨 Creator and Developer of Echo 🎨

🔰 Creator Information:
🧑‍💻 Creator: The Seeker
📧 Contact: [@MrUnknown114]
📝 Proofreader: [@The_Seeker_116]

For inquiries and collaborations, please contact:
📧 Email: caveoftheseekers@gmail.com
🌐 Update Channel: https://t.me/Echo_AIO

For support and community engagement, join our support group:
👥 Support Group: https://t.me/ECHO_Support_Unit"""

# Load environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

# Validate environment variables
if not all([os.getenv("TOKEN"), os.getenv("MONGODB_URI"), os.getenv("REMINDER_CHECK_TIMEZONE"), os.getenv("AUTHORIZED_USERS"), os.getenv("SCEDUCAST_TIMEZONE"), os.getenv("SCEDUCAST_TIME_OFFSET"), os.getenv("OWNER"), os.getenv("UPSTREAM_REPO_URL")]):
    print("Please provide all required environment variables.")
    exit(1)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Assign the environment variables to variables
TOKEN = get_env_var_from_db("TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
REMINDER_CHECK_TIMEZONE = get_env_var_from_db("REMINDER_CHECK_TIMEZONE")

# log the environment variables
logger.info("TOKEN: %s", TOKEN)
logger.info("MONGODB_URI: %s", MONGODB_URI)

try:
    decrypted_creator_info = decrypt(encrypted_creator_info)

    if creator_credits != decrypted_creator_info:
        print("""⚠️ Attention!

Echo's Copyright Cops are here! Dare to crack the code, trespasser? 

The chosen ones laugh in the face of your puny edits.A labyrinth for the unworthy. Seek wisdom, not plunder. Respect the Creator's artistry, or face the eternal maze.⚔️

(You have tempered to the creator's credits. Don't edit them. The creator needs some appreciation too. Right? Good Luck with your deployment
~Echo!)""")
        exit(1)

except Exception as e:
    print("Respect to the Creator. Deployment stopped due to integrity check failure.")
    print(e)
    exit(1)

USER_AND_CHAT_DATA_COLLECTION = 'user_and_chat_data'

client = MongoClient(MONGODB_URI)
db = client.get_database("Echo")
user_and_chat_data_collection = db[USER_AND_CHAT_DATA_COLLECTION]
USER_TIMEZONES_COLLECTION = 'user_timezones' 

# Call the function to set necessary variables from broadcast module
broadcast_set_bot_variables(user_and_chat_data_collection, REMINDER_CHECK_TIMEZONE)

def send_post_restart_message(bot: Bot):
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    status_record = db.update_status.find_one({'_id': 'restart_status'})

    if status_record and 'status' in status_record:
        # Fetch OWNER from the MongoDB database
        owner_str = get_env_var_from_db("OWNER")
        owners = owner_str.split(",") if owner_str else []

        status_message = status_record['status']
        for owner in owners:
            bot.send_message(chat_id=owner, text=status_message, parse_mode=ParseMode.MARKDOWN)

def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user = update.message.from_user
    chat = update.message.chat

    if chat.type == 'private':
        username = f"@{user.username}" if user.username else None

        # Save user details to MongoDB
        user_and_chat_data_collection.update_one(
            {'user_id': user.id, 'chat_id': chat_id},
            {'$set': {
                'user_id': user.id,
                'chat_id': chat_id,
                'telegram_name': user.full_name,  # Use full_name to store the complete name
                'telegram_username': username,
                'bot_start_time': datetime.now(),
            }},
            upsert=True
        )

        start_photo_path = "assets/start.jpeg"  
        start_caption = '🕊*Step into the world of Echo, where modern Telegram experiences are crafted. Let Echo be your guide to a new dimension of communication and convenience. Welcome to the Echo experience!*\n\n*Echo is your trusty sidekick. Need a nudge? /setreminder is your jam.*'

        # Add the "Update Channel 📢" and "Support Group 🫂" buttons
        keyboard = [
            [InlineKeyboardButton("Update Channel 📢", url="https://t.me/Echo_AIO")],
            [InlineKeyboardButton("Support Group 🫂", url="https://t.me/ECHO_Support_Unit")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_photo(
            chat_id=chat_id,
            photo=open(start_photo_path, "rb"),
            caption=start_caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup  # Add the inline keyboard
        )

    elif chat.type == 'group' or chat.type == 'supergroup':
        group_username = chat.username if chat.username else None

        # Save group details to MongoDB
        user_and_chat_data_collection.update_one(
            {'chat_id': chat_id},
            {'$set': {
                'chat_id': chat_id,
                'group_name': chat.title,
                'group_username': group_username,
                'bot_added_time': datetime.now(),
            }},
            upsert=True
        )

        start_photo_path = "assets/start.jpeg"  
        start_caption = '🕊*Step into the world of Echo, where modern Telegram experiences are crafted. Let Echo assist you in your group chats with a new dimension of communication and convenience. Welcome to the Echo experience!*\n\n*Echo is your trusty sidekick. Need a nudge? /setreminder is your jam.*'

        # Add the "Update Channel 📢" and "Support Group 🫂" buttons
        keyboard = [
            [InlineKeyboardButton("Update Channel 📢", url="https://t.me/Echo_AIO")],
            [InlineKeyboardButton("Support Group 🫂", url="https://t.me/ECHO_Support_Unit")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_photo(
            chat_id=chat_id,
            photo=open(start_photo_path, "rb"),
            caption=start_caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup  # Add the inline keyboard
        )
     
    else:
        # Unknown chat type, handle accordingly
        return

# HTTP server code
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        with open('index.html', 'rb') as file:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(file.read())

httpd = None

def run_http_server():
    global httpd
    httpd = socketserver.TCPServer(("", 8000), SimpleHTTPRequestHandler)
    logger.info("Serving HTTP on port 8000")
    httpd.serve_forever()

def stop_http_server():
    global httpd
    if httpd:
        httpd.shutdown()
        httpd.server_close()
        logger.info("HTTP server stopped")


def restart_command(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    owners_str = get_env_var_from_db("OWNER")
    owners = owners_str.split(",") if owners_str else []
    repo_url = get_env_var_from_db("UPSTREAM_REPO_URL")

    if str(user_id) in owners:
        try:
            snowflake_message = context.bot.send_message(chat_id=update.message.chat_id, text="❄️", parse_mode=ParseMode.MARKDOWN)

            updates_applied, commit_message, commit_author = check_for_updates(repo_url)
            if updates_applied:
                status_message = f"✅ Successfully Updated and Restarted!\n\n*Latest Commit Details;*\n\n_Message_: `{commit_message}`\n_Author_: `{commit_author}`"
            else:
                status_message = "🔄 No New Updates. Just Restarted!"
            
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=snowflake_message.message_id)

            write_update_status_to_mongo(status_message)
            stop_http_server()
            restart_bot()

            context.bot.delete_message(chat_id=update.message.chat_id, message_id=snowflake_message.message_id)

        except Exception as e:
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=snowflake_message.message_id)
            update.message.reply_text(f"Failed to restart: {str(e)}")
            logging.error(f"⚠️ Failed to restart: {str(e)}")
    else:
        update.message.reply_text("You do not have permission to perform this action.")

# Function to set a reminder
def set_reminder(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    try:
        # Extract command text and remove the command itself (/setreminder)
        command_text = update.message.text[len("/sr"):].strip()

                # Split the command text into date, time, and message
        date_str, time_str, *message_parts = command_text.split()
        datetime_str = f"{date_str} {time_str}"
        reminder_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

        # Get the user's time zone from MongoDB (default to REMINDER_CHECK_TIMEZONE if not set)
        user_timezone_record = db.user_timezones.find_one({'user_id': user_id}, {'timezone': 1})
        user_timezone = user_timezone_record['timezone'] if user_timezone_record else REMINDER_CHECK_TIMEZONE
        timezone = pytz.timezone(user_timezone)
        reminder_datetime = timezone.localize(reminder_datetime)

        # Combine remaining parts as the reminder message
        reminder_message = ' '.join(message_parts)

        # Save the reminder to MongoDB
        db.reminders.insert_one({
            'user_id': user_id,
            'datetime': reminder_datetime,
            'message': reminder_message
        })

        update.message.reply_text(f'Reminder set for {reminder_datetime.strftime("%Y-%m-%d %H:%M:%S")} ({user_timezone}).')

    except (ValueError, IndexError):
        update.message.reply_text('Invalid command. Use /sr followed by the date and time in the format '
                                  'YYYY-MM-DD HH:MM:SS. For example, /sr 2024-01-01 12:00:00 My reminder message.')

# Function to check and send reminders
def check_reminders(context: CallbackContext) -> None:
    current_time = datetime.now(pytz.utc)

    reminders = db.reminders.find()
    for reminder in reminders:
        reminder_datetime_utc = reminder['datetime'].replace(tzinfo=pytz.utc)

        if reminder_datetime_utc <= current_time:
            user_id = reminder['user_id']
            message_text = f'#Reminder: {reminder["message"]}'

            # Define the inline keyboard buttons with "re_b_re" prefix
            keyboard = [
                [InlineKeyboardButton("Mark as Completed 🔖", callback_data=f"re_b_re_complete_{reminder['_id']}"),
                 InlineKeyboardButton("Mark as Incompleted ⛔", callback_data=f"re_b_re_notcomplete_{reminder['_id']}")],
                [InlineKeyboardButton("Mark as Ignored 🤷", callback_data=f"re_b_re_ignore_{reminder['_id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send the message with inline buttons
            context.bot.send_message(chat_id=user_id, text=message_text, reply_markup=reply_markup)
            
            if 'recurring' in reminder:
                new_datetime = reminder_datetime_utc  # Use the UTC-aware datetime
                if reminder['recurring'] == 'minutely':
                    new_datetime += timedelta(minutes=1)
                elif reminder['recurring'] == 'hourly':
                    new_datetime += timedelta(hours=1)
                elif reminder['recurring'] == 'daily':
                    new_datetime += timedelta(days=1)
                elif reminder['recurring'] == 'weekly':
                    new_datetime += timedelta(weeks=1)
                elif reminder['recurring'] == 'monthly':
                    new_datetime += relativedelta(months=+1)
                elif reminder['recurring'] == 'yearly':
                    new_datetime += relativedelta(years=+1)
                
                # Update the reminder's datetime in MongoDB for the next occurrence
                db.reminders.update_one({'_id': reminder['_id']}, {'$set': {'datetime': new_datetime}})
            else:
                db.reminders.delete_one({'_id': reminder['_id']})

def reminder_reaction_button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    callback_data = query.data

    # Adjusted to handle additional segments in callback_data
    parts = callback_data.split('_')
    action = parts[3]  # Assuming 'action' is always at the third position
    reminder_id = '_'.join(parts[4:])  # Joining the rest as reminder_id may contain '_'

    # Define noop button for completed actions
    noop_button = None

    if action == 'complete':
        new_text = "Completed ✅"
        noop_button = InlineKeyboardButton(new_text, callback_data="noop")
    elif action == 'notcomplete':
        new_text = "Incompleted ❌"
        noop_button = InlineKeyboardButton(new_text, callback_data="noop")
    elif action == 'ignore':
        new_text = "Ignored 🤷‍♂️"
        noop_button = InlineKeyboardButton(new_text, callback_data="noop")

    # Update the message to reflect the action taken
    query.edit_message_text(text=f"#Reminder: {query.message.text.split(':', 1)[1]}",
                            reply_markup=InlineKeyboardMarkup([[noop_button]]))

# Function to handle the /myreminders command
def show_my_reminders(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Check if there is an existing document for the user in the user_timezones collection
    user_timezone_record = db.user_timezones.find_one({'user_id': user_id}, {'timezone': 1})
    user_timezone = user_timezone_record['timezone'] if user_timezone_record else None

    # Set the timezone to user's timezone if available; otherwise, use the global timezone
    target_timezone = pytz.timezone(user_timezone) if user_timezone else pytz.timezone(REMINDER_CHECK_TIMEZONE)

    # Display user's current timezone at the top of the message
    timezone_message = f'🌐 Your current timezone: *{user_timezone}* 🕒' if user_timezone else f'🌐 Your current timezone: *{REMINDER_CHECK_TIMEZONE}* (Default) 🕒'

    # Call the function to show user reminders
    reminders = show_user_reminders(user_id)

    if reminders:
        messages = [timezone_message, '']  # Adding a line space after timezone message

        for reminder in reminders:
            reminder_datetime = reminder["datetime"].astimezone(target_timezone)
            time_remaining = reminder_datetime - datetime.now(pytz.timezone(REMINDER_CHECK_TIMEZONE))

            # Format remaining time as days, hours, minutes, and seconds
            remaining_time_str = str(timedelta(seconds=time_remaining.total_seconds()))

            message = f'📅 *{reminder["message"]}*' \
                      f'\n\tDate & Time - {reminder_datetime.strftime("%Y-%m-%d %H:%M:%S")}' \
                      f'\n\tRemaining Time - {remaining_time_str}'

            messages.extend([message, ''])  # Add a line space after each reminder

        update.message.reply_text('\n'.join(messages), parse_mode=ParseMode.MARKDOWN)
    else:
        no_reminders_message = 'You have no reminders.'
        if not user_timezone:
            no_reminders_message += f'\n\n*Note:* You haven\'t set a custom timezone, so your reminders and other time-related activities are set to the global timezone (*{REMINDER_CHECK_TIMEZONE}*) 🌐.\n\n Use [This link](https://telegra.ph/Choose-your-timezone-02-16) to find you timezone easily🪄'
        update.message.reply_text(no_reminders_message, parse_mode=ParseMode.MARKDOWN)
        
# Function to set the user's time zone
def set_timezone(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_timezone = ' '.join(context.args)

    # Check if "user_timezones" collection exists, if not, create it
    if USER_TIMEZONES_COLLECTION not in db.list_collection_names():
        db.create_collection(USER_TIMEZONES_COLLECTION)

    # Check if there is an existing document for the user
    existing_document = db[USER_TIMEZONES_COLLECTION].find_one({'user_id': user_id})

    if existing_document:
        # Update the existing document
        db[USER_TIMEZONES_COLLECTION].update_one({'user_id': user_id}, {'$set': {'timezone': user_timezone}})
    else:
        # Create a new document for the user
        db[USER_TIMEZONES_COLLECTION].insert_one({'user_id': user_id, 'timezone': user_timezone})

    # Update the in-memory user_data
    context.user_data['timezone'] = user_timezone

    update.message.reply_text(f'Time zone set to {user_timezone}.')

def install_ffmpeg():
    logger.info("Checking for ffmpeg installation...")
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE)
        logger.info("ffmpeg is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("ffmpeg not found. Attempting installation...")
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
            logger.info("ffmpeg installation successful.")
        except subprocess.CalledProcessError as e:
            logger.info(f"Failed to install ffmpeg: {e}")
            sys.exit(1)

# List of bot commands
bot_commands = [
    BotCommand("start", "Start the Echo🤖"),
    BotCommand("help", "Get help & more info message💁"),
    BotCommand("broadcast", "[Authorized Users Only]Send important updates directly to all your followers.📢"),
    BotCommand("scheducast", "[Authorized Users Only]Schedule important broadcast and Echo got you covered🗓️"),
    BotCommand("setreminder", "Set a reminder in mordern way🧬"),
    BotCommand("sr", "Set a reminder in traditional way⏰"),
    BotCommand("myreminders", "Show your reminders📃"),
    BotCommand("editreminders", "Make a mistake? Edit your reminders now before it's too late ⚙️"),
    BotCommand("delreminder", "Delete your reminders♻️"),
    BotCommand("settimezone", "Set your time zone⌚"),
    BotCommand("gemini", "Meet you personal AI Assistant, Google Gemini🤖"),
    BotCommand("chatbot", "Chat with Echo's Chatbot🗨️"),
    BotCommand("mygapi", "Setup your Gemini API🧩"),
    BotCommand("analyze4to", "Begin Image Analysis Process🖼️"),
    BotCommand("showmygapi", "Look at you Google Gemini API👀"),
    BotCommand("delmygapi", "Delete Your Google API from Echo's Database🗑️"),
    BotCommand("calculator", "or /cal To get Echo's Calculator menu 🧮"),
    BotCommand("uptotgph", "Upload any telegram image to telegraph ⤴️"),
    BotCommand("logogen", "[Beta] Craft Your Logos with Echo!"),
    BotCommand("docspotter", "Enhanced Auto Filter Module ⛈️"),
    BotCommand("shiftx", "Convert Various range of files to another type 🔄️"),
    BotCommand("erasefiles", "Delete indexed files ♻️"),
    BotCommand("ringtones", "Explore sample ringtones♫"),
    BotCommand("info", "See User/Chat info 📜"),
    BotCommand("moreinfo", "Get more information about the bot🤓"),
    BotCommand("overview", "See a stats report about Echo and Host Server 📝"),
    BotCommand("database", "Get database stats📊"),
    BotCommand("bsettings", "Config Echo! ⚙️"),
    BotCommand("restart", "Restart Echo (And get latest update from REPO)!🔁"),
]

# Main function
if __name__ == '__main__':
    from telegram.ext import Updater

    # Start the HTTP server in a separate thread
    http_server_thread = Thread(target=run_http_server)
    http_server_thread.start()
     
    # Initialize the Updater with your bot token
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    from moreinfo_handler import more_info
    from modules.broadcast import register_handlers as broadcast_register_handlers, set_bot_variables as broadcast_set_bot_variables, handle_broadcast_message

    # Retrieve user timezone from MongoDB or set it to REMINDER_CHECK_TIMEZONE
    default_timezone = db.user_timezones.find_one({'user_id': 0}, {'timezone': 1})
    dp.user_data['timezone'] = default_timezone['timezone'] if default_timezone else REMINDER_CHECK_TIMEZONE
     
    dp.add_handler(CommandHandler("start", start)) 
    dp.add_handler(CommandHandler("sr", set_reminder))
    dp.add_handler(CommandHandler("setreminder", start_reminder_creation))
    dp.add_handler(CommandHandler("settimezone", set_timezone))
    dp.add_handler(CommandHandler("myreminders", show_my_reminders))
    dp.add_handler(CommandHandler("delreminder", handle_delreminder_command)) 
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("ringtones", send_ringtones))
    dp.add_handler(CommandHandler("moreinfo", more_info))
    dp.add_handler(CommandHandler("editreminders", edit_reminders))
    dp.add_handler(MessageHandler(Filters.regex(r'^/editreminder_\w+$'), edit_specific_reminder))
    dp.add_handler(CommandHandler("er", edit_reminder))
    dp.add_handler(CommandHandler("database", database_command))
    dp.add_handler(CommandHandler("bsettings", bsettings_command))
    dp.add_handler(CommandHandler("overview", overview_command))
    dp.add_handler(CommandHandler("restart", restart_command))
    dp.add_handler(CallbackQueryHandler(reminder_reaction_button_callback, pattern='^re_b_re_'))

    gemini_handler = CommandHandler('gemini', handle_gemini_command)
    dp.add_handler(gemini_handler)
    dp.add_handler(CommandHandler("mygapi", handle_mygapi_command)) 
    dp.add_handler(CommandHandler("delmygapi", handle_delmygapi_command))
    dp.add_handler(CommandHandler("showmygapi", handle_showmygapi_command))
    dp.add_handler(CommandHandler('analyze4to', analyze4to_handler))
    dp.add_handler(CommandHandler("chatbot", toggle_chatbot))
    dp.add_handler(MessageHandler((Filters.text & ~Filters.command) & (Filters.chat_type.private | Filters.chat_type.groups), handle_chat_message), group=5)
     
    dp.add_handler(CommandHandler("logogen", handle_logogen, pass_args=True))
    dp.add_handler(CallbackQueryHandler(button, pattern=r"^(frame_|logo_|font_size_\d+)"))

    dp.add_handler(CallbackQueryHandler(bsettings_button_callback, pattern='^config_envs$'))
    dp.add_handler(CallbackQueryHandler(show_env_value_callback, pattern='^env_'))
    dp.add_handler(CallbackQueryHandler(edit_env_callback, pattern='^edit_'))
    dp.add_handler(CallbackQueryHandler(close_config_callback, pattern='^close_config$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, handle_new_env_value), group=0)
     
    send_post_restart_message(updater.bot)

    dp.job_queue.run_repeating(check_reminders, interval=60, first=0)
    dp.job_queue.run_repeating(lambda context: check_scheduled_broadcasts(context.bot), interval=60, first=0)
    dp.bot.set_my_commands(bot_commands, scope=BotCommandScopeDefault())
    dp.add_handler(CallbackQueryHandler(handle_help_button_click, pattern='^(basic|reminder|misc|brsc|gemini|calculator_help|tgphup|logogen_help|doc_spotter_help|info_help|chatbot_help|commit_detector_help)$'))
    dp.add_handler(callback_query_handler)
    dp.add_handler(CallbackQueryHandler(handle_confirmation, pattern='^(yes|no):'))
    dp.add_handler(CallbackQueryHandler(handle_back_button_click, pattern='^back$'))

    setup_commit_detector(updater)

    register_overview_handlers(dp)
    
    register_id_command(dp)
    
    setup_telegraph_up(dp)
     
    setup_calculator(dp)
    setup_sci_calculator(dp)

    reminder_creator_handlers(dp)
     
    setup_ds_dispatcher(dp)
    setup_ds_executor_dispatcher(dp)
     
    from modules import broadcast 
    broadcast.register_handlers(dp)
    dp.add_handler(CommandHandler("broadcast", handle_broadcast_message))

    scheducast.setup_dispatcher(dp, db)     

    register_shiftx_handlers(dp)

    install_ffmpeg()
    
    dp.bot_data['start_time'] = datetime.now()
    
    # Start the Bot
    updater.start_polling()

    bot_info = updater.bot.get_me()
    bot_name = bot_info.first_name
    bot_username = bot_info.username
    logger.info(f"{bot_name} [@{bot_username}] Started Successfully ✅. Have Some fun with Echo ✨")

    updater.idle()
