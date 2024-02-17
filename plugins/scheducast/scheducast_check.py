import os
import logging
from dateutil import tz
from telegram import Bot, User
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
from modules.configurator import get_env_var_from_db

dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

# Access the environment variables
SCEDUCAST_TIMEZONE = get_env_var_from_db("SCEDUCAST_TIMEZONE")
MONGODB_URI = os.getenv("MONGODB_URI")
TOKEN = get_env_var_from_db("TOKEN")

def get_sceducast_time_offset():
    offset_str = get_env_var_from_db("SCEDUCAST_TIME_OFFSET")
    try:
        return float(offset_str) if offset_str is not None else 0.0
    except ValueError:
        logger.warning(f"Invalid SCEDUCAST_TIME_OFFSET value in database: {offset_str}. Defaulting to 0.0.")
        return 0.0

SCEDUCAST_TIME_OFFSET = get_sceducast_time_offset()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient(MONGODB_URI)
db = client.get_database("Echo")
schedule_broadcasts_collection = db["schedule_broadcasts"]
user_and_chat_data_collection = db["user_and_chat_data"]

bot = Bot(token=TOKEN)

def check_scheduled_broadcasts(bot):
    current_time = datetime.now(tz.tzlocal()) + timedelta(hours=SCEDUCAST_TIME_OFFSET)

    sceducast_timezone = tz.gettz(SCEDUCAST_TIMEZONE)
    current_sceducast_time = current_time.astimezone(sceducast_timezone)
    logger.info(f'Current time in SCEDUCAST_TIMEZONE: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')

    broadcasts = schedule_broadcasts_collection.find({'schedule_datetime': {'$lte': current_time}})

    for broadcast in broadcasts:
        broadcast_type = broadcast['broadcast_type']
        broadcast_data = broadcast['broadcast_data']
        scheduled_user_id = broadcast['user_id']

        user = user_and_chat_data_collection.find_one({'user_id': scheduled_user_id})

        if broadcast_type == 'pm':
            received_pm_users_count, not_received_pm_users_count = send_to_pm_users(bot, broadcast_data, user)
            received_group_chat_count, not_received_group_chat_count = 0, 0
        elif broadcast_type == 'group':
            received_group_chat_count, not_received_group_chat_count = send_to_bot_added_groups(bot, broadcast_data, user)
            received_pm_users_count, not_received_pm_users_count = 0, 0
        elif broadcast_type == 'all':
            received_pm_users_count, not_received_pm_users_count = send_to_pm_users(bot, broadcast_data, user)
            received_group_chat_count, not_received_group_chat_count = send_to_bot_added_groups(bot, broadcast_data, user)

        logger.info(f'Processed broadcast: {broadcast}')

        schedule_broadcasts_collection.delete_one({'_id': broadcast['_id']})

        # Send the summary message to the user who scheduled the broadcast
        send_summary_message(bot, user, broadcast_type, received_pm_users_count, received_group_chat_count,
                             not_received_pm_users_count, not_received_group_chat_count)


def send_summary_message(bot, user, broadcast_type, received_pm_users_count, received_group_chat_count,
                         not_received_pm_users_count, not_received_group_chat_count):
    # Extract user information from the dictionary
    user_full_name = user.get('full_name', 'N/A')
    user_username = user.get('username', 'N/A')
    user_id = user.get('user_id', 'N/A')

    summary_message = f"Scheducast successfully sent.\n\n" \
                      f"🎯 Scheducast Initiated User Info\n" \
                      f"⚡Scheducast Type: {broadcast_type.capitalize()}\n\n" \
                      f"📃 Scheducast Summary\n" \
                      f"❄️Received PM Users Count: {received_pm_users_count}\n" \
                      f"❄️Received Group Chat Count: {received_group_chat_count}\n" \
                      f"❄️Received Total Chat Count: {received_pm_users_count + received_group_chat_count}\n\n" \
                      f"❄️Not Received PM Users Count: {not_received_pm_users_count}\n" \
                      f"❄️Not Received Group Chat Count: {not_received_group_chat_count}\n" \
                      f"❄️Not Received Total Chat Count: {not_received_pm_users_count + not_received_group_chat_count}"

    try:
        chat_id = user.get('chat_id', None)

        if chat_id is not None:
            user_details = f"⚡User: You🫵\n" \
                           f"⚡Telegram ID: {user_id}\n"

            summary_message = summary_message.replace("🎯 Broadcast Initiated User Info", f"🎯 Broadcast Initiated User Info\n{user_details}")

            bot.send_message(chat_id=chat_id, text=summary_message)
    except Exception as e:
        # Handle exception if needed
        logger.error(f"Error sending summary message: {e}", exc_info=True)

def send_to_pm_users(bot, message, user):
    pm_users = user_and_chat_data_collection.find({'chat_id': {'$gt': 0}})

    received_count = 0
    not_received_count = 0

    for pm_user in pm_users:
        try:
            bot.send_message(chat_id=pm_user['chat_id'], text=message)
            received_count += 1
        except Exception as e:
            not_received_count += 1

    return received_count, not_received_count


def send_to_bot_added_groups(bot, message, user):
    group_chats = user_and_chat_data_collection.find({'chat_id': {'$lt': 0}})

    received_count = 0
    not_received_count = 0

    for group_chat in group_chats:
        try:
            bot.send_message(chat_id=group_chat['chat_id'], text=message)
            received_count += 1
        except Exception as e:
            not_received_count += 1

    return received_count, not_received_count

def send_to_all_chats(bot, message):
    all_chats = user_and_chat_data_collection.find({})

    for chat in all_chats:
        try:
            bot.send_message(chat_id=chat['chat_id'], text=message)
        except Exception as e:
            pass

if __name__ == "__main__":
    check_scheduled_broadcasts(bot)
