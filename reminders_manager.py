# reminders_manager.py
import os
import pytz
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone

dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client.get_database("Echo")

# Function to show reminders for a specific user
def show_user_reminders(user_id):
    current_time = datetime.now(timezone.utc)

    reminders = db.reminders.find({'user_id': user_id, 'datetime': {'$gt': current_time}})
    
    return list(reminders)
