# configurator.py
import os
import logging
import telegram
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ENV_VARS_PER_PAGE = 10
MAX_PAGE_BTNS_PER_ROW = 6

class DatabaseConfig:
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            try:
                mongo_uri = os.getenv("MONGODB_URI")
                if mongo_uri is None:
                    raise Exception("MONGODB_URI is not set in environment variables")
                cls._client = MongoClient(mongo_uri)
                cls._db = cls._client.get_database("Echo")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                cls._db = None
        return cls._db

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
        "SETUP_BOT_PROFILE": os.getenv("SETUP_BOT_PROFILE"),
        "BOT_NAME": os.getenv("BOT_NAME"),
        "BOT_ABOUT": os.getenv("BOT_ABOUT"),
        "BOT_DESCRIPTION": os.getenv("BOT_DESCRIPTION"),
        "SCEDUCAST_TIMEZONE": os.getenv("SCEDUCAST_TIMEZONE"),
        "SCEDUCAST_TIME_OFFSET": os.getenv("SCEDUCAST_TIME_OFFSET"),
        "TOKEN_RESET_TIME": os.getenv("TOKEN_RESET_TIME"),
        "URL_SHORTNER": os.getenv("URL_SHORTNER"),
        "URL_SHORTNER_API": os.getenv("URL_SHORTNER_API"),
        "GEMINI_PLUGIN": os.getenv("GEMINI_PLUGIN"),
        "CHAT_BOT_PLUGIN": os.getenv("CHAT_BOT_PLUGIN"),
        "GEMINI_IMAGE_PLUGIN": os.getenv("GEMINI_IMAGE_PLUGIN"),
        "CALCULATOR_PLUGIN": os.getenv("CALCULATOR_PLUGIN"),
        "SCI_CALCULATOR_PLUGIN": os.getenv("SCI_CALCULATOR_PLUGIN"),
        "UNIT_CONVERTER_PLUGIN": os.getenv("UNIT_CONVERTER_PLUGIN"),
        "TELEGRAPH_UP_PLUGIN": os.getenv("TELEGRAPH_UP_PLUGIN"),
        "LOGOGEN_PLUGIN": os.getenv("LOGOGEN_PLUGIN"),
        "DOC_SPOTTER_PLUGIN": os.getenv("DOC_SPOTTER_PLUGIN"),
        "SHIFTX_PLUGIN": os.getenv("SHIFTX_PLUGIN"),
        "REMOVEBG_PLUGIN": os.getenv("REMOVEBG_PLUGIN"),
        "IMDb_PLUGIN": os.getenv("IMDb_PLUGIN"),
        "CLONEGRAM_PLUGIN": os.getenv("CLONEGRAM_PLUGIN"),
        "DS_IMDB_ACTIVATE": os.getenv("DS_IMDB_ACTIVATE"),
        "DS_URL_BUTTONS": os.getenv("DS_URL_BUTTONS"),
        "GH_CD_URLS": os.getenv("GH_CD_URLS"),
        "GH_CD_CHANNEL_IDS": os.getenv("GH_CD_CHANNEL_IDS"),
        "GH_CD_PAT": os.getenv("GH_CD_PAT"),
        "ENABLE_GLOBAL_G_API": os.getenv("ENABLE_GLOBAL_G_API"),
        "GLOBAL_G_API": os.getenv("GLOBAL_G_API"),
        "SHIFTX_MP3_TO_AAC_BITRATE": os.getenv("SHIFTX_MP3_TO_AAC_BITRATE"),
        "SHIFTX_AAC_TO_MP3_BITRATE": os.getenv("SHIFTX_AAC_TO_MP3_BITRATE"),
        "SHIFTX_OGG_TO_MP3_QUALITY": os.getenv("SHIFTX_OGG_TO_MP3_QUALITY"),
        "SHIFTX_MP3_TO_OGG_QUALITY": os.getenv("SHIFTX_MP3_TO_OGG_QUALITY"),
        "REMOVEBG_API": os.getenv("REMOVEBG_API")
    }

    create_configs_collection() 

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]

    for key, value in env_vars.items():
        if configs_collection.count_documents({"key": key}) == 0:
            configs_collection.insert_one({"key": key, "value": value})
        else:
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

def get_unique_message_for_env(key):
    unique_messages = {
        "TOKEN": "🔑 This is your bot's Telegram API token. Obtain it from @BotFather and Keep it secret!\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "MONGODB_URI": "🗄️ This is your MongoDB connection URI. It's crucial for your bot's database operations.\n\n<b>Required [🔴]</b>",
        "OWNER": "👤 This is the Telegram ID of the bot owner. Only this user can access bot settings.\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "UPSTREAM_REPO_URL": "🔗 URL to the GitHub source code repository, Recommended to use the official Echo Repo.\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SETUP_BOT_PROFILE": "Automatically setup Bot Name, About and Description at the deploy of Echo instead of manually setup in @BotFather\n\n⚠️ You have been advised to set SETUP_BOT_PROFILE environment variable to <code>False</code> after you set up your Echo profile correctly during the first deployment using /bsettings to prevent unnecessary rate limit errors.\n\n<b>Optional But Recommended to Fill [🔶]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "BOT_NAME": "Set New name for Echo!\n\n<b>Optional But Recommended to Fill [🔶]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "BOT_ABOUT": "Set New about text for Echo!\n\n<b>Optional But Recommended to Fill [🔶]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "BOT_DESCRIPTION": "Set New description for Echo!\n\n<b>Optional But Recommended to Fill [🔶]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "REMINDER_CHECK_TIMEZONE": "🕒 Global timezone used for scheduling reminders and time-based commands. Find your timezone from internet or <a href=\"https://telegra.ph/Choose-your-timezone-02-16\">this link</a>\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "AUTHORIZED_USERS": "🛡️ List of user IDs to give access to Echo's some features.\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SCEDUCAST_TIMEZONE": "🌐 Timezone setting for Sceducast, Your Scheducast will set based on this\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SCEDUCAST_TIME_OFFSET": "⏳ Offset in hours for Sceducast scheduling. Refer Readme for more info adjusting for time zones.\n\n<b>Required [🔴]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "TOKEN_RESET_TIME": "Token reset time for all users.\n\nSet to <code>0</code> to deactivate token system\n\n⚠️ Must be an integer (Number)\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "URL_SHORTNER": "Your Ad Shortner Domain with <code>https://</code>\n\nE.g. <code>https://atglinks.com</code>\n\n<i>Suppoerted Shortners: <code>atglinks.com, exe.io, gplinks.in, shrinkme.io, urlshortx.com, shortzon.com, shorte.st, ouo.io</code></i>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "URL_SHORTNER_API": "Your Ad Shortner API\n\n<i>Suppoerted Shortners: <code>atglinks.com, exe.io, gplinks.in, shrinkme.io, urlshortx.com, shortzon.com, shorte.st, ouo.io</code></i>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GEMINI_PLUGIN": "🔌 Enable or Disable Gemini Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "CHAT_BOT_PLUGIN": "🔌 Enable or Disable Chatbot Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GEMINI_IMAGE_PLUGIN": "🔌 Enable or Disable Gemini Image Analyze Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "CALCULATOR_PLUGIN": "🔌 Enable or Disable Basic Calculator Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "SCI_CALCULATOR_PLUGIN": "🔌 Enable or Disable Scientific Calculator Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "UNIT_CONVERTER_PLUGIN": "🔌 Enable or Disable Unit Converter Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "TELEGRAPH_UP_PLUGIN": "🔌 Enable or Disable Telegraph Image Uploading Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "LOGOGEN_PLUGIN": "🔌 Enable or Disable Logo Generator Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "DOC_SPOTTER_PLUGIN": "🔌 Enable or Disable Doc Spotter (Advanced Auto Filter) Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "SHIFTX_PLUGIN": "🔌 Enable or Disable ShiftX Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "REMOVEBG_PLUGIN": "🔌 Enable or Disable RemoveBG Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "IMDb_PLUGIN": "🔌 Enable or Disable IMDb Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "CLONEGRAM_PLUGIN": "🔌 Enable or Disable Clonegram Plugin\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Not Required</i></u>",
        "DS_IMDB_ACTIVATE": "🎥 Enable or Disable Doc Spotter's IIPS (IMDb Info and Poster Sending) in Button List\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GH_CD_URLS": "🔗 GitHub Repo URLs for Commit Detector Plugin\n\n<b>Optional [🟩], But necessary if GH_CD_CHANNEL_IDS was filled</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GH_CD_CHANNEL_IDS": "📢 Lists Telegram chat IDs Where Commit Detector Notifications are Sent.\n\n<b>Optional [🟩], But necessary if GH_CD_URLS was filled</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GH_CD_PAT": "🔐 Personal Access Token for GitHub to authenticate deployment requests.\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "ENABLE_GLOBAL_G_API": "🌍 Enables or disables global Google Gemini API for AI related features across the Echo.\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "GLOBAL_G_API": "🔑 Your Global Google Gemini API key.\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SHIFTX_MP3_TO_AAC_BITRATE": "🔊 Set a quality for MP3 to AAC Outputs.\n\n<code>Set a value among 128k, 192k, 256k, 320k</code>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SHIFTX_AAC_TO_MP3_BITRATE": "🔊 Set a quality for AAC to MP3 Outputs.\n\n<code>Set a value among 128k, 192k, 256k, 320k</code>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SHIFTX_OGG_TO_MP3_QUALITY": "🔊 Set quality for OGG to MP3 Outputs.\n\n<code>Set a value from 0 to 9</code>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "SHIFTX_MP3_TO_OGG_QUALITY": "🔊 Set quality for MP3 to OGG Outputs.\n\n<code>Set a value from -1 to 10</code>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "REMOVEBG_API": "🔊 Set Global API Key for RemoveBG Plugin.\n\n<i>Gen an API Key from https://www.remove.bg/dashboard#api-key</i>\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>",
        "DS_URL_BUTTONS": "Enable or Desable URL buttons for Doc Spotter\n\n<b>Optional [🟩]</b>\n<b>For new changes, Restart:</b> <u><i>Required</i></u>"
    }

    return unique_messages.get(key, "<b>Please fill in the environment variables accordingly. Refer to the README for more information about these variables.</b>")

def show_env_value_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    parts = query.data.split("_")
    key = "_".join(parts[1:]) 

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    env_record = configs_collection.find_one({"key": key})

    if env_record:
        unique_message = get_unique_message_for_env(key)
        base_message = f"{key}: <code>{env_record['value']}</code>"
        text_message = f"{unique_message}\n\n{base_message}"
        
        keyboard = []
        if key not in ["MONGODB_URI"]: 
            keyboard.append([InlineKeyboardButton("Edit ENV", callback_data=f"edit_{key}")])
        else:
            # Special message for MONGODB_URI
            text_message += "\n\n⚠️Highly Sensitive ENV\n\n" \
                            "<u>MONGODB_URI</u> is an env that Echo can't edit from the telegram interface. " \
                            "If you want to change your current <u>MONGODB_URI</u>, you have to edit your " \
                            "<b>config.env</b> in your repo and redeploy.\n\n"
        
        keyboard.append([InlineKeyboardButton("Back", callback_data='config_envs')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=text_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    else:
        query.edit_message_text(text=f"Value for {key} not found.")

def edit_env_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    full_key = query.data.split("_", 1)[1]
    context.user_data['edit_env_key'] = full_key
    context.user_data['awaiting_env_value'] = True

    query.edit_message_text(text=f"Now send your new value for {full_key}!")

def handle_new_env_value(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    owner = get_owner_from_db()

    if str(user_id) != owner or 'edit_env_key' not in context.user_data:
        return

    full_key = context.user_data['edit_env_key']
    new_value = update.message.text.strip()  

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]
    configs_collection.update_one({"key": full_key}, {"$set": {"value": new_value}})

    unique_message = get_unique_message_for_env(full_key)
    base_message = f"{full_key}: <code>{new_value}</code>"
    text_message = f"{unique_message}\n\n{base_message}"

    keyboard = [[InlineKeyboardButton("Edit ENV", callback_data=f"edit_{full_key}")],
                [InlineKeyboardButton("Back", callback_data='config_envs')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text=text_message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    del context.user_data['edit_env_key']

def show_config_envs(query, page=0):
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.get_database("Echo")
    configs_collection = db["configs"]

    # Fetch all environment variables and calculate the number of pages
    all_envs = list(configs_collection.find({}))
    total_envs = len(all_envs)
    total_pages = (total_envs + ENV_VARS_PER_PAGE - 1) // ENV_VARS_PER_PAGE

    # Calculate the range of envs to display on the current page
    start = page * ENV_VARS_PER_PAGE
    end = start + ENV_VARS_PER_PAGE
    page_envs = all_envs[start:end]

    # Create a two-column grid of buttons for the current page of envs
    keyboard = []
    for i in range(0, len(page_envs), 2):
        row = [
            InlineKeyboardButton(page_envs[i]["key"], callback_data=f"env_{page_envs[i]['key']}"),
            InlineKeyboardButton(page_envs[i+1]["key"], callback_data=f"env_{page_envs[i+1]['key']}")
        ] if (i + 1) < len(page_envs) else [
            InlineKeyboardButton(page_envs[i]["key"], callback_data=f"env_{page_envs[i]['key']}")
        ]
        keyboard.append(row)

    # Pagination buttons logic
    page_buttons = [InlineKeyboardButton(str(p + 1), callback_data=f"page_{p}") for p in range(total_pages)]
    
    # Split page buttons into groups for each row
    page_btn_groups = [page_buttons[i:i + MAX_PAGE_BTNS_PER_ROW] for i in range(0, len(page_buttons), MAX_PAGE_BTNS_PER_ROW)]

    # Add each group of page buttons as a new row in the keyboard
    for btn_group in page_btn_groups:
        keyboard.append(btn_group)

    keyboard.append([InlineKeyboardButton("Back to Bot Settings", callback_data='back_to_bot_settings'),
                     InlineKeyboardButton("Close", callback_data='close_config')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Select an ENV to edit or view its value:", reply_markup=reply_markup)

def page_navigation_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    page = int(query.data.split('_')[1])

    try:
        show_config_envs(query, page=page)
    except telegram.error.BadRequest as e:

        if "Message is not modified" in str(e):
            pass 
        else:
            raise 

def back_to_bot_settings_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Display the bot settings message with "Config ENVs" button
    keyboard = [
        [InlineKeyboardButton("Config ENVs", callback_data='config_envs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Bot Settings:", reply_markup=reply_markup)

def close_config_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    try:
        query.delete_message()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

def get_env_var_from_db(key_name):
    db = DatabaseConfig.get_db()
    if db is None:
        logger.error("Database connection is not available.")
        return None

    try:
        configs_collection = db["configs"]
        env_var_record = configs_collection.find_one({"key": key_name})
        if env_var_record and "value" in env_var_record:
            return env_var_record["value"]
        else:
            logger.warning(f"Environment variable {key_name} not found in database.")
            return None
    except Exception as e:
        logger.error(f"Error fetching environment variable {key_name} from database: {e}")
        return None
