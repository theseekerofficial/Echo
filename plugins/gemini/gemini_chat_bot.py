import os
import sys
import time
import logging
import pymongo
import threading
from telegram import Update
import google.generativeai as genai
from telegram.ext import CallbackContext
from modules.configurator import get_env_var_from_db
from plugins.gemini.gemini import initialize_gemini_model, format_html

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

global_g_api = os.getenv("GLOBAL_G_API")
enable_global_g_api = os.getenv("ENABLE_GLOBAL_G_API", "false").lower() == "true"

if (enable_global_g_api and not global_g_api) or (not enable_global_g_api and global_g_api):
    logging.warning("⚠️Go and fill both values for ENABLE_GLOBAL_G_API and GLOBAL_G_API if needed  or Keep them both empty if didn't need!")
    sys.exit("Missing one of the required environment variables: GLOBAL_G_API or ENABLE_GLOBAL_G_API")

mongo_uri = os.getenv("MONGODB_URI")
chat_bot_plugin_enabled = get_env_var_from_db("CHAT_BOT_PLUGIN") == "True"
client = pymongo.MongoClient(mongo_uri)
db = client["Echo"]
api_keys_collection = db["gemini_api"]

# Function to toggle chatbot feature for a user
def toggle_chatbot(update: Update, context: CallbackContext):
    if not chat_bot_plugin_enabled:
        update.message.reply_text("Echo Chatbot Plugin Disabled by the Person who deployed this Echo variant 💔")
        return

    user_id = update.effective_user.id
    # Using a unique key for each user in the chat_data to store chatbot enabled state
    chatbot_enabled_key = f'chatbot_enabled_{user_id}'
    chatbot_enabled = context.chat_data.get(chatbot_enabled_key, False)
    
    context.chat_data[chatbot_enabled_key] = not chatbot_enabled

    if context.chat_data[chatbot_enabled_key]:
        update.message.reply_text("Echo Chatbot activated. I'm here to chat with you! 🗨️")
    else:
        update.message.reply_text("Echo Chatbot deactivated. I'll miss our conversations! 💔")

def update_thinking_message(context, chat_id, message_id):
    count = 0
    while not getattr(update_thinking_message, "stop", False):
        # Cycle through adding dots to simulate thinking
        new_text = "`Echo is thinking" + "." * (count % 4) + "`" 
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode='MarkdownV2')
        count += 1
        time.sleep(0.75) 

# Function to handle messages when chatbot is active
def handle_chat_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chatbot_enabled_key = f'chatbot_enabled_{user_id}'

    if not chat_bot_plugin_enabled:
        return

    if update.effective_user is None:
        logging.warning("Received an update without an effective user.")
        return

    if not context.chat_data.get(chatbot_enabled_key, False):
        return  

    # Fetch the user's API key from the database
    user_api_key_entry = api_keys_collection.find_one({"user_id": user_id})
    api_key = user_api_key_entry['api_key'] if user_api_key_entry else None

    # Use the global API key if a user-specific API key is not found and global API is enabled
    if not api_key and enable_global_g_api and global_g_api:
        api_key = global_g_api
        logging.info("Using global API key for Gemini model.")
    elif not api_key:
        update.message.reply_text("Please set your API key using /myapi first. Refer /help cmd for more 📖 (Like how to get an API Key and more)\n\nSo hurry up! We have a journey to complete!✨")
        return

    # Configure the Gemini API with the chosen API key
    genai.configure(api_key=api_key)

    # Send initial "Echo is thinking..." message in monospace font
    thinking_message = update.message.reply_text("`Echo X Gemini`", parse_mode='MarkdownV2')

    # Reset the stop flag and start the "thinking" thread
    update_thinking_message.stop = False
    thinking_thread = threading.Thread(target=update_thinking_message, args=(context, update.effective_chat.id, thinking_message.message_id,))
    thinking_thread.start()
    
    try:
        gemini_model = initialize_gemini_model()
        query = update.message.text
        response = gemini_model.generate_content({"text": query})
        formatted_response = format_html(response.text)

        # Stop the "thinking" thread
        update_thinking_message.stop = True
        thinking_thread.join()

        # Edit the final message to display the response
        context.bot.edit_message_text(chat_id=user_id, message_id=thinking_message.message_id, text=formatted_response, parse_mode='HTML')
        
        # Logging the response sent to the user
        logging.info(f"Chat bot 🗨️🤖💬 response sent to user {user_id}")
        
    except Exception as e:
        logging.error(f"Error using Gemini model: {e}")
        update_thinking_message.stop = True
        thinking_thread.join()
        update.message.reply_text("Sorry, there was an error processing your request. Please try again.")
