import os
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)

def is_user_member_of_fsub_chats(sender_user_id: int, chat_id: int, client, context: CallbackContext) -> bool:
    
    group_config = client["Echo_Doc_Spotter"]["Listening_Groups"].find_one({"group_id": str(chat_id)})
    if not group_config:
        return True

    logging.info(f"🔍 Checking FSub for sender_user_id: {sender_user_id} in chat_id: {chat_id}")
    setup_user_id = group_config["user_id"]
    fsub_chats = client["Echo_Doc_Spotter"]["Fsub_Chats"].find({"user_id": setup_user_id})
    
    for fsub_chat in fsub_chats:
        fsub_chat_id = fsub_chat["chat_id"]
        try:
            status = context.bot.get_chat_member(fsub_chat_id, sender_user_id).status
            if status not in ['member', 'administrator', 'creator']:
                logging.info(f"❌ Sender {sender_user_id} is not a member of FSub chat: {fsub_chat_id}")
                return False
        except Exception as e:
            logging.error(f"⚠️ Error checking membership for chat {fsub_chat_id}: {e}")
    
    logging.info(f"✅ Sender {sender_user_id} is a member of all required FSub chats or No FSub chat(s) configured by group owner.")
    return True

def prompt_to_join_fsub_chats(update: Update, context: CallbackContext, client):
    chat_id = update.message.chat.id
    
    group_config = client["Echo_Doc_Spotter"]["Listening_Groups"].find_one({"group_id": str(chat_id)})
    if not group_config:
        logging.info("🚫 This group is not configured for FSub. No action required.")
        update.message.reply_text("This group does not have any FSub requirements set.")
        return

    setup_user_id = group_config["user_id"]
    fsub_chats = client["Echo_Doc_Spotter"]["Fsub_Chats"].find({"user_id": setup_user_id})
    
    buttons = []
    for fsub_chat in fsub_chats:
        fsub_chat_id = fsub_chat["chat_id"]
        chat_info = context.bot.get_chat(fsub_chat_id)
        invite_link = chat_info.invite_link if chat_info.invite_link else f"https://t.me/{chat_info.username}"
        buttons.append([InlineKeyboardButton(chat_info.title, url=invite_link)])
    
    if buttons:
        logging.info("📬 Prompting user to join FSub chats.")
        reply_markup = InlineKeyboardMarkup(buttons)
        update.message.reply_text("Hmm... Looks like you haven't joined our chats to use Doc Spotter 😓. Please join the following chats and try again:", reply_markup=reply_markup)
    else:
        logging.error("⚠️ No invite links found or unable to create buttons for FSub chats.")
        update.message.reply_text("We encountered an issue fetching the FSub chats. Please contact the admin.")

def find_user_by_group(chat_id, client):
    """Find the setup user_id associated with a group_id."""
    record = client["Echo_Doc_Spotter"]["Listening_Groups"].find_one({"group_id": str(chat_id)})
    return record["user_id"] if record else None
