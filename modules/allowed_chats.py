# modules/allowed_chats.py
import os
import logging
from functools import wraps
from telegram.ext import BaseFilter, MessageHandler
from modules.configurator import get_env_var_from_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AllowedChatsFilter(BaseFilter):
    def __call__(self, message):

        owner_id = get_env_var_from_db("OWNER")
        authorized_users = get_env_var_from_db("AUTHORIZED_USERS")

        owner_id = int(owner_id) if owner_id and owner_id.isdigit() else None
        authorized_user_list = []
        if authorized_users:
            try:
                authorized_user_list = [int(user_id.strip()) for user_id in authorized_users.split(",") if user_id.strip().isdigit()]
            except ValueError as e:
                logger.error(f"Error parsing AUTHORIZED_USERS: {e}")
                return False

        if message.from_user.id == owner_id or message.from_user.id in authorized_user_list:
            return True
        
        go_public = get_env_var_from_db("GO_PUBLIC")
        go_public = (go_public or "False").lower() == "true"
        if go_public:
            return True

        allowed_chats = get_env_var_from_db("ALLOWED_CHATS")
        if not allowed_chats:
            return False

        try:
            allowed_chat_list = [int(chat_id.strip()) for chat_id in allowed_chats.split(",") if chat_id.strip().isdigit() or chat_id.strip().lstrip("-").isdigit()]
        except ValueError as e:
            logger.error(f"Error parsing ALLOWED_CHATS: {e}")
            return False

        return message.chat_id in allowed_chat_list

def allowed_chats_only(handler):
    @wraps(handler)
    def wrapped(update, context, *args, **kwargs):
        filter_instance = AllowedChatsFilter()
        if filter_instance(update.message):
            return handler(update, context, *args, **kwargs)
        else:
            logger.warning(f"Access denied for chat/user ID: {update.message.chat_id}")
    return wrapped

