import os
import logging
import hashlib
from telegram import Update
from pymongo import MongoClient
from datetime import datetime, timedelta
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, CommandHandler
from modules.utilities.url_shortener import get_short_url
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenSystem:
    def __init__(self, mongo_uri, db_name, collection_name):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        token_reset_time = get_env_var_from_db("TOKEN_RESET_TIME")
        try:
            self.token_reset_time = int(token_reset_time) if token_reset_time is not None else 0
            logger.info(f"Token System reset time set to {self.token_reset_time} 🎫")
        except ValueError:  
            self.token_reset_time = 0
            logger.warning(f"There is a problem in you mongodb config for TOKEN_RESET_TIME. For safety we fallback to default value, {self.token_reset_time}. Witch mean token system was disabled!⚠️")
        self.owner_id = get_env_var_from_db("OWNER")
        authorized_user_ids_str = get_env_var_from_db("AUTHORIZED_USERS")
        self.authorized_user_ids = [int(uid.strip()) for uid in authorized_user_ids_str.split(',')] if authorized_user_ids_str else []
        self.go_public = get_env_var_from_db("GO_PUBLIC").strip().lower() == "true"
        allowed_chats_str = get_env_var_from_db("ALLOWED_CHATS")
        self.allowed_chats = set(int(cid.strip()) for cid in allowed_chats_str.split(',')) if allowed_chats_str else set()
    
    def generate_token(self, user_id):
        self.collection.delete_many({
            'user_id': user_id
        })
        token = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()
        self.collection.insert_one({
            'user_id': user_id, 
            'token': token, 
            'created_at': datetime.now(), 
            'used': False
        })
        return token

    def verify_token(self, update: Update, context: CallbackContext, next):
        user_id = update.effective_user.id

        if user_id == self.owner_id or user_id in self.authorized_user_ids:
            return next(update, context)

        chat_id = update.effective_chat.id
        
        if not self.go_public and chat_id not in self.allowed_chats:
            return
        
        if self.token_reset_time == 0:
            return next(update, context)

        paid_user_record = self.db["Paid_Users"].find_one({'user_id': user_id})
        if paid_user_record:
            expire_date_str = paid_user_record.get('expire_date')
            if expire_date_str:
                expire_date = datetime.strptime(expire_date_str, "%d-%m-%Y").date()
                if expire_date >= datetime.now().date():
                    return next(update, context)

        token_record = self.collection.find_one({
            'user_id': user_id, 
            'used': True
        })
        
        if token_record:
            token_age = datetime.now() - token_record['created_at']
            if token_age <= timedelta(seconds=self.token_reset_time):
                return next(update, context)
            else:
                self.collection.delete_one({'user_id': user_id})
                token_record = None

        if not token_record:
            token = self.generate_token(user_id)
            bot_username = context.bot.username
            long_url = f"https://t.me/{bot_username}?start={token}"
            short_url = get_short_url(long_url)
            activation_button = InlineKeyboardButton(text="Activate Session", url=short_url)
            reply_markup = InlineKeyboardMarkup([[activation_button]])
            update.message.reply_text("Please activate your session by clicking the button below:", reply_markup=reply_markup)
            return

    def token_filter(self, command_handler):
        def wrapped(update: Update, context: CallbackContext):
            return self.verify_token(update, context, command_handler.callback)
        return CommandHandler(command_handler.command, wrapped, filters=command_handler.filters, pass_args=command_handler.pass_args)
