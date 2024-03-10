import logging
import requests
from modules.configurator import get_env_var_from_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = get_env_var_from_db("TOKEN")
new_name = get_env_var_from_db("BOT_NAME") or 'Ｅｃｈｏ'
new_short_description = get_env_var_from_db("BOT_ABOUT") or 'Echo is your All-in-One AI Personal Assistant 🤖'
new_description = get_env_var_from_db("BOT_DESCRIPTION") or """Echo is a personal AI assistant on Telegram aimed at enhancing productivity through seamless integration of reminders, schedules, broadcasts, and many many more features. 🪄🍃"""
setup_bot_profile = get_env_var_from_db('SETUP_BOT_PROFILE') or 'True'

def set_bot_name():
    url = f'https://api.telegram.org/bot{TOKEN}/setMyName'
    params = {
        'name': new_name
    }
    response = requests.post(url, json=params)
    if response.status_code == 200:
        logger.info(f"Bot name changed successfully as '{new_name}'🤖.")
    else:
        logger.info("Failed to change bot name.")
        logger.info(response.text)

def set_bot_description():
    url = f'https://api.telegram.org/bot{TOKEN}/setMyDescription'
    params = {
        'description': new_description
    }
    response = requests.post(url, json=params)
    if response.status_code == 200:
        logger.info(f"Bot description changed successfully as '{new_short_description}'✔️.")
    else:
        logger.error("Failed to change bot description.")
        logger.error(response.text)

def set_bot_short_description():
    url = f'https://api.telegram.org/bot{TOKEN}/setMyShortDescription'
    params = {
        'short_description': new_short_description
    }
    response = requests.post(url, json=params)
    if response.status_code == 200:
        logger.info(f"Bot short description changed successfully as '{new_description}'📝.")
    else:
        logger.error("Failed to change bot short description.")
        logger.error(response.text)

def setup_bot_info():
    if setup_bot_profile.lower() == 'true':
        set_bot_name()
        set_bot_description()
        set_bot_short_description()
    else:
        logger.info("Auto Bot Profile setup config is disabled. Skipping bot information setup. 🍃")
