# configurator.py
import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def create_configs_collection():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")

    # Check if the "configs" collection exists, and create it if not
    if "configs" not in db.list_collection_names():
        logger.info("Creating 'configs' collection...")
        db.create_collection("configs")

def load_and_store_env_vars():
    dotenv_path = os.path.join(os.path.dirname(__file__), '../config.env')
    if not os.path.exists(dotenv_path):
        logger.error("config.env file not found")
        return

    load_dotenv(dotenv_path)

    env_vars = {
        "TOKEN": os.getenv("TOKEN"),
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "OWNER": os.getenv("OWNER"),
        "UPSTREAM_REPO_URL": os.getenv("UPSTREAM_REPO_URL"),
        "REMINDER_CHECK_TIMEZONE": os.getenv("REMINDER_CHECK_TIMEZONE"),
        "AUTHORIZED_USERS": os.getenv("AUTHORIZED_USERS"),
        "SCEDUCAST_TIMEZONE": os.getenv("SCEDUCAST_TIMEZONE"),
        "SCEDUCAST_TIME_OFFSET": os.getenv("SCEDUCAST_TIME_OFFSET"),
        "GEMINI_PLUGIN": os.getenv("GEMINI_PLUGIN"),
        "CHAT_BOT_PLUGIN": os.getenv("CHAT_BOT_PLUGIN"),
        "GEMINI_IMAGE_PLUGIN": os.getenv("GEMINI_IMAGE_PLUGIN"),
        "CALCULATOR_PLUGIN": os.getenv("CALCULATOR_PLUGIN"),
        "SCI_CALCULATOR_PLUGIN": os.getenv("SCI_CALCULATOR_PLUGIN"),
        "UNIT_CONVERTER_PLUGIN": os.getenv("UNIT_CONVERTER_PLUGIN"),
        "TELEGRAPH_UP_PLUGIN": os.getenv("TELEGRAPH_UP_PLUGIN"),
        "LOGOGEN_PLUGIN": os.getenv("LOGOGEN_PLUGIN"),
        "DOC_SPOTTER_PLUGIN": os.getenv("DOC_SPOTTER_PLUGIN")
    }

    create_configs_collection()  # Create the "configs" collection if it doesn't exist

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]

    for key, value in env_vars.items():
        # Check if the key already exists in the database
        if configs_collection.count_documents({"key": key}) == 0:
            # If the key does not exist, insert it with its value
            configs_collection.insert_one({"key": key, "value": value})
        else:
            # If the key already exists, skip to the next one
            logger.info(f"Skipping {key} as it already exists in the database.")

    logger.info("Environment variables have been checked and updated in MongoDB.")
    
def get_owner_from_db():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    owner_record = configs_collection.find_one({"key": "OWNER"})
    return owner_record["value"] if owner_record else None

def bsettings_command(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = str(user.id)
    owner = get_owner_from_db()
    chat_type = update.message.chat.type
    chat_id = update.message.chat.id

    # Log for unauthorized access attempts
    if user_id != owner:
        username = user.username or "No Username"
        logger.warning(f"🚨 Unauthorized access attempt to config menu by User ID: {user_id}, Username: {username}, in Chat ID: {chat_id} (Type: {chat_type})")
        update.message.reply_text("🚫 You do not have permission to use this command.")
        return

    if chat_type != 'private':
        # Warning message if the command is used in a group chat
        update.message.reply_text("⚠️ This command can only be used in a private chat with the bot "
                                  "to prevent sensitive data from being exposed. Please open or "
                                  "start a private chat with the bot to access these settings. 🛡️")
        return

    # Log for successful access by the owner
    username = user.username or "No Username"
    logger.info(f"🫡 Owner accessed config menu: User ID: {user_id}, Username: {username}")

    # Rest of the command for displaying settings in a private chat
    keyboard = [
        [InlineKeyboardButton("Config ENVs", callback_data='config_envs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Bot Settings:", reply_markup=reply_markup)

def bsettings_button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'config_envs':
        show_config_envs(query) 
        
def show_env_value_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    parts = query.data.split("_")
    key = "_".join(parts[1:])  # Join all parts after the first underscore

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    env_record = configs_collection.find_one({"key": key})

    if env_record:
        text_message = f"{key}: {env_record['value']}"
        keyboard = []

        if key != "MONGODB_URI":
            keyboard.append([InlineKeyboardButton("Edit ENV", callback_data=f"edit_{key}")])
        else:
            # Special message for MONGODB_URI
            text_message += "\n\n⚠️Highly Sensitive ENV\n\n" \
                            "<u>MONGODB_URI</u> is an env that Echo can't edit from the telegram interface. " \
                            "If you want to change your current <u>MONGODB_URI</u>, you have to edit your " \
                            "<b>config.env</b> in your repo and redeploy.\n\n"

        # Add a 'Back' button to go back to the main config envs menu
        keyboard.append([InlineKeyboardButton("Back", callback_data='config_envs')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=text_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        query.edit_message_text(text=f"Value for {key} not found.")

def edit_env_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    full_key = query.data.split("_", 1)[1]
    context.user_data['edit_env_key'] = full_key
    context.user_data['awaiting_env_value'] = True  # Set a flag

    query.edit_message_text(text=f"Now send your new value for {full_key}!")

def handle_new_env_value(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    owner = get_owner_from_db()

    if str(user_id) != owner or 'edit_env_key' not in context.user_data:
        # If the user is not the owner or not in editing mode, do nothing
        return

    # Retrieve the environment variable key to be edited
    full_key = context.user_data['edit_env_key']
    new_value = update.message.text.strip()  # Get the new value sent by the owner

    # Update the value in the MongoDB database
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    configs_collection.update_one({"key": full_key}, {"$set": {"value": new_value}})

    # Prepare the message text and keyboard for the updated value
    text_message = f"{full_key}: {new_value}"
    keyboard = [
        [InlineKeyboardButton("Edit ENV", callback_data=f"edit_{full_key}")],
        [InlineKeyboardButton("Back", callback_data='config_envs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the updated value message with the keyboard
    update.message.reply_text(text=text_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    # Clear the editing mode flag and key from the user's context data
    del context.user_data['edit_env_key']

def show_config_envs(query):
    # Connect to MongoDB
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]

    # Fetch all environment variables
    envs = list(configs_collection.find({}))

    # Create a two-column grid of buttons
    keyboard = []
    row = []
    for env in envs:
        button = InlineKeyboardButton(env["key"], callback_data=f"env_{env['key']}")
        row.append(button)
        if len(row) == 2:  # Two buttons per row
            keyboard.append(row)
            row = []
    if row:  # Add the last row if it has less than 2 buttons
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Close", callback_data='close_config')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Select an ENV to view its value:", reply_markup=reply_markup)

def close_config_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    try:
        query.delete_message()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

def get_env_var_from_db(key_name):
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    env_var_record = configs_collection.find_one({"key": key_name})
    return env_var_record["value"] if env_var_record else None
