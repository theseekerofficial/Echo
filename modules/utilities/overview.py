# modules/utilities/overview.py
import os
import re
import distro
import psutil
import requests
import platform
import threading
from datetime import datetime
from pymongo import MongoClient
from datetime import datetime, timedelta
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

client = MongoClient(os.getenv("MONGODB_URI"))
db = client.Echo

def get_bot_uptime(start_time):
    now = datetime.now()
    uptime = now - start_time
    return str(uptime).split('.')[0]

def overview_command(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Bot Status", callback_data='overview_bot_status'), InlineKeyboardButton("System Status", callback_data='overview_system_status')],
        [InlineKeyboardButton("Plugin Status", callback_data='overview_plugin_status')],
        [InlineKeyboardButton("Check For Updates!", callback_data='overview_check_updates')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Echo\'s Overview', reply_markup=reply_markup)

def bot_status_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    bot_start_time = context.bot_data.get('start_time', datetime.now())
    uptime = get_bot_uptime(bot_start_time)

    try:
        with open('README.md', 'r') as file:
            first_line = file.readline().strip()
            match = re.search(r"ECHO v(.*?\))", first_line)
            if match:
                bot_version = match.group(0)
            else:
                bot_version = 'Unknown'
    except Exception as e:
        bot_version = 'Unknown'

    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    swap_usage = psutil.swap_memory().percent

    repo_path = os.getcwd()
    disk_usage = psutil.disk_usage(repo_path).percent

    try:
        restart_at_every = int(get_env_var_from_db("RESTART_AT_EVERY"))
    except (ValueError, TypeError):
        restart_at_every = None

    uptime_parts = uptime.split(':')
    hours = int(uptime_parts[0])
    minutes = int(uptime_parts[1])
    seconds = int(uptime_parts[2])

    total_uptime_seconds = hours * 3600 + minutes * 60 + seconds

    if restart_at_every is not None:
        auto_restart_in_seconds = restart_at_every - total_uptime_seconds
        if auto_restart_in_seconds < 0:
            auto_restart_in = "Auto Restart Disabled"
        else:
            auto_restart_hours = auto_restart_in_seconds // 3600
            auto_restart_minutes = (auto_restart_in_seconds % 3600) // 60
            auto_restart_seconds = auto_restart_in_seconds % 60
            auto_restart_in = f"{auto_restart_hours:02d}:{auto_restart_minutes:02d}:{auto_restart_seconds:02d}"
    else:
        auto_restart_in = "Auto Restart Disabled"

    status_message = f"╰──╮ <u><b><i>BOT STATISTICS</i></b></u> ╭──╯\n\n༶•┈┈┈┈┈┈┈┈┈୨💤୧┈┈┈┈┈┈┈┈┈•༶\n🤖 <b>Echo Uptime:</b> <code>{uptime}</code>\n🌀 <b>Auto Restart in:</b> <code>{auto_restart_in}\n</code>༶•┈┈┈┈┈┈┈┈┈୨💤୧┈┈┈┈┈┈┈┈┈•༶\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨🔑୧┈┈┈┈┈┈┈┈┈•༶\n💾 <b>Echo Version:</b> <code>{bot_version}</code>\n༶•┈┈┈┈┈┈┈┈┈୨🔑୧┈┈┈┈┈┈┈┈┈•༶\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨⚡️୧┈┈┈┈┈┈┈┈┈•༶\n🖥 <b>CPU Usage:</b> <code>{cpu_usage}%</code>\n" \
                     f"🧠 <b>RAM Usage:</b> <code>{ram_usage}%</code>\n" \
                     f"💽 <b>Swap Memory Usage:</b> <code>{swap_usage}%</code>\n" \
                     f"🗄 <b>Disk Usage:</b> <code>{disk_usage}%</code>\n༶•┈┈┈┈┈┈┈┈┈୨⚡️୧┈┈┈┈┈┈┈┈┈•༶"

    keyboard = [
        [InlineKeyboardButton("Close", callback_data='overview_close'),
         InlineKeyboardButton("Back", callback_data='overview_back')],
        [InlineKeyboardButton("Refresh ♻️", callback_data='overview_bot_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=status_message, reply_markup=reply_markup, parse_mode='HTML')

def system_status_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    # System uptime
    system_uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    system_uptime_str = str(system_uptime).split('.')[0]  

    net_io = psutil.net_io_counters()
    data_sent = net_io.bytes_sent / (1024**3)  
    data_received = net_io.bytes_recv / (1024**3)  
    packets_sent = net_io.packets_sent
    packets_received = net_io.packets_recv
    total_data_gb = (net_io.bytes_sent + net_io.bytes_recv) / (1024**3) 

    cpu_freq = psutil.cpu_freq().current 
    physical_cores = psutil.cpu_count(logical=False)  
    logical_cores = psutil.cpu_count(logical=True)

    active_threads = threading.active_count()
    python_version = platform.python_version()
    distribution_info = f"{distro.name()} {distro.version()}"
    platform_info = platform.system() + " " + platform.release()
    load_average = os.getloadavg()
    python_implementation = platform.python_implementation()
    total_disk_space, used_disk_space, free_disk_space = psutil.disk_usage('/').total / (1024**3), psutil.disk_usage('/').used / (1024**3), psutil.disk_usage('/').free / (1024**3)
    total_memory, available_memory = psutil.virtual_memory().total / (1024**3), psutil.virtual_memory().available / (1024**3)
    num_processes = len(psutil.pids())
    os_arch = platform.machine()
    last_restart = context.bot_data.get('start_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')

    status_message = f"╰──╮ <u><b><i>SYSTEM STATISTICS</i></b></u> ╭──╯\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨🟢୧┈┈┈┈┈┈┈┈┈•༶\n🕒 <b>System Uptime:</b> <code>{system_uptime_str}</code>\n" \
                     f"🖥️ <b>OS Version:</b> <code>{distribution_info}</code>\n" \
                     f"💻 <b>Platform:</b> <code>{platform_info}</code>\n" \
                     f"🌉 <b>OS Arch :</b> <code>{os_arch}</code>\n༶•┈┈┈┈┈┈┈┈┈୨🟢୧┈┈┈┈┈┈┈┈┈•༶\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨⚙️୧┈┈┈┈┈┈┈┈┈•༶\n🚀 <b>CPU Frequency:</b> <code>{cpu_freq:.2f} MHz</code>\n" \
                     f"🔢 <b>Total Core(s):</b> <code>{logical_cores}</code>\n" \
                     f"🖥️ <b>P-Core(s):</b> <code>{physical_cores}</code>\n" \
                     f"💻 <b>V-Core(s):</b> <code>{logical_cores}</code>\n" \
                     f"🧵 <b>CPU Threads Count:</b> <code>{logical_cores}</code>\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨⚙️୧┈┈┈┈┈┈┈┈┈•༶\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨🌐୧┈┈┈┈┈┈┈┈┈•༶\n📡 <b>Network I/O:</b> Sent <code>{data_sent:.2f} GB</code>, Received <code>{data_received:.2f} GB</code>\n" \
                     f"📤 <b>Pkts Sent:</b> <code>{packets_sent}</code>, 📥 <b>Pkts Received:</b> <code>{packets_received}</code>\n" \
                     f"🌐 <b>Total Network I/O Data:</b> <code>{total_data_gb:.2f} GB</code>\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨🌐୧┈┈┈┈┈┈┈┈┈•༶\n\n" \
                     f"༶•┈┈┈┈┈┈┈┈┈୨🖥️୧┈┈┈┈┈┈┈┈┈•༶\n🧵<b>Active Threads:</b> <code>{active_threads}</code>\n" \
                     f"🐍 <b>Python Version:</b> <code>{python_version}</code>\n" \
                     f"💻 <b>System Load:</b> <code>1 min: {load_average[0]:.2f}, 5 min: {load_average[1]:.2f}, 15 min: {load_average[2]:.2f}</code>\n" \
                     f"🛣️ <b>Python implementation:</b> <code>{python_implementation}</code>\n" \
                     f"💽 <b>Total Disk Size:</b> <code>{total_disk_space:.2f} GB</code>\n" \
                     f"💿 <b>Used Disk Size:</b> <code>{used_disk_space:.2f} GB</code>\n" \
                     f"📀 <b>Free Disk Size:</b> <code>{free_disk_space:.2f} GB</code>\n" \
                     f"💫 <b>Total RAM:</b> <code>{total_memory:.2f} GB</code>\n" \
                     f"💫 <b>Free RAM:</b> <code>{available_memory:.2f} GB</code>\n" \
                     f"⚙️ <b>Processes Count:</b> <code>{num_processes}</code>\n" \
                     f"🔄 <b>Last Restart:</b> <code>{last_restart}</code>\n༶•┈┈┈┈┈┈┈┈┈୨🖥️୧┈┈┈┈┈┈┈┈┈•༶"

    keyboard = [
        [InlineKeyboardButton("Close", callback_data='overview_close'),
         InlineKeyboardButton("Back", callback_data='overview_back')],
        [InlineKeyboardButton("Refresh ♻️", callback_data='overview_system_status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=status_message, reply_markup=reply_markup, parse_mode='HTML')

def fetch_plugin_statuses():
    plugin_statuses = {}
    configs = db.configs.find({})

    for config in configs:
        if config['key'] != "GH_CD_URLS" and config['key'] != "REMOVEBG_API":
            plugin_statuses[config['key']] = config['value'] == "True"
        elif config['key'] == "GH_CD_URLS" or config['key'] == "REMOVEBG_API":
            plugin_statuses[config['key']] = bool(config['value'])
        else:
            plugin_statuses[config['key']] = config['value']

    return plugin_statuses

def plugin_status_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    plugin_statuses = fetch_plugin_statuses()

    # Plugin descriptions
    plugin_descriptions = {
        "GEMINI_PLUGIN": "Gemini Plugin",
        "ENABLE_GLOBAL_G_API": "Global Gemini API for All Users",
        "GEMINI_IMAGE_PLUGIN": "Gemini Image Analyzer",
        "CHAT_BOT_PLUGIN": "Echo Chatbot",
        "CALCULATOR_PLUGIN": "Basic Calculator",
        "SCI_CALCULATOR_PLUGIN": "Scientific Calculator",
        "UNIT_CONVERTER_PLUGIN": "Unit Converter",
        "TELEGRAPH_UP_PLUGIN": "Telegraph Uploader",
        "LOGOGEN_PLUGIN": "Logo Generator",
        "DOC_SPOTTER_PLUGIN": "Doc Spotter [DS]",
        "SHIFTX_PLUGIN": "ShiftX Converter",
        "REMOVEBG_PLUGIN": "Background Remover",
        "REMOVEBG_API": "Global API for Background Remover",
        "IMDb_PLUGIN": "IMDb Movie/TV Show Finder",
        "CLONEGRAM_PLUGIN": "Chat Cloner [Clonegram]",
        "F_SUB_PLUGIN": "Force Subscriber [F-Sub]",
        "FSUB_INFO_IN_PM": "F-Sub info in PM",
        "DS_IMDB_ACTIVATE": "IMDb in DS",
        "DS_URL_BUTTONS": "URL Buttons for Doc Spotter",
        "GH_CD_URLS": "Commit Detector"
    }

    status_message = "╰──╮ <u><b><i>PLUGIN/FEATURE STATUS</i></b></u> ╭──╯\n\n༶•┈┈┈┈┈┈┈┈┈୨🧩୧┈┈┈┈┈┈┈┈┈•༶\n"

    for key, description in plugin_descriptions.items():
        status = "Enabled" if plugin_statuses.get(key, False) else "Disabled"
        status_message += f"🔌 <b>{description}:</b> <code>{status}</code>\n"
    status_message += f"༶•┈┈┈┈┈┈┈┈┈୨🧩୧┈┈┈┈┈┈┈┈┈•༶"

    keyboard = [
        [InlineKeyboardButton("Close", callback_data='overview_close'),
         InlineKeyboardButton("Back", callback_data='overview_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=status_message, reply_markup=reply_markup, parse_mode='HTML')

def check_for_updates_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    owner_id = int(os.getenv('OWNER', 'default_owner_id'))

    if user_id != owner_id:
        query.answer("Sorry, mate, this button can only be used by the owner.", show_alert=True)
        return

    try:
        with open('README.md', 'r') as file:
            local_version = file.readline().strip()
    except Exception as e:
        local_version = "Local version could not be determined."

    repo_url = 'https://raw.githubusercontent.com/theseekerofficial/Echo/master/README.md'
    try:
        response = requests.get(repo_url)
        remote_version = response.text.split('\n', 1)[0].strip()
    except Exception as e:
        query.edit_message_text("Failed to fetch remote version.")
        return

    if local_version == remote_version:
        message = f"🆗 <b><i><u>Bot is Up to Date!</u></i></b>\n\nVersion: <code>{local_version}</code>"
    else:
        message = f"🆕 <b><i><u>New Update Available!</u></i></b>\n\nCurrent Version: <code>{local_version}</code>\nNew Version: <code>{remote_version}</code>\n\n" \
                  f"To update, simply send /restart, and you are fully up to date. 🔄"

    # Add Back and Close buttons
    keyboard = [
        [InlineKeyboardButton("Close", callback_data='overview_close'),
         InlineKeyboardButton("Back", callback_data='overview_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode='HTML')

def overview_close_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.delete()

def overview_back_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("Bot Status", callback_data='overview_bot_status'), InlineKeyboardButton("System Status", callback_data='overview_system_status')],
        [InlineKeyboardButton("Plugin Status", callback_data='overview_plugin_status')],
        [InlineKeyboardButton("Check For Updates!", callback_data='overview_check_updates')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text='Echo\'s Overview', reply_markup=reply_markup)

def register_overview_handlers(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(bot_status_callback, pattern='^overview_bot_status$'))
    dispatcher.add_handler(CallbackQueryHandler(system_status_callback, pattern='^overview_system_status$'))
    dispatcher.add_handler(CallbackQueryHandler(plugin_status_callback, pattern='^overview_plugin_status$'))
    dispatcher.add_handler(CallbackQueryHandler(check_for_updates_callback, pattern='^overview_check_updates$'))
    dispatcher.add_handler(CallbackQueryHandler(overview_close_callback, pattern='^overview_close$'))
    dispatcher.add_handler(CallbackQueryHandler(overview_back_callback, pattern='^overview_back$'))
