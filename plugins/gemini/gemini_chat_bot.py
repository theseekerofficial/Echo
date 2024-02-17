import os
import logging
import pymongo
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

# Function to handle messages when chatbot is active
def handle_chat_message(update: Update, context: CallbackContext):
    if not chat_bot_plugin_enabled:
        # If the chat bot plugin is disabled, no need to proceed further
        return

    if update.effective_user is None:
        logging.warning("Received an update without an effective user.")
        return
        
    user_id = update.effective_user.id
    chatbot_enabled_key = f'chatbot_enabled_{user_id}'

    if not context.chat_data.get(chatbot_enabled_key, False):
        return  

    # Fetch the user's API key from the database
    user_api_key_entry = api_keys_collection.find_one({"user_id": user_id})
    if not user_api_key_entry:
        update.message.reply_text("You need to set your API key first using /mygapi command.")
        return

    # Configure the Gemini API with the user's API key
    genai.configure(api_key=user_api_key_entry['api_key'])

    try:
        gemini_model = initialize_gemini_model()  
        query = update.message.text
        response = gemini_model.generate_content({"text": query})
        formatted_response = format_html(response.text) 
        update.message.reply_text(formatted_response, parse_mode='HTML')

        # Logging the response sent to the user
        logging.info(f"Chat bot 🗨️🤖💬 response sent to user {user_id}")
    except Exception as e:
        logging.error(f"Error using Gemini model: {e}")
        update.message.reply_text("Sorry, there was an error processing your request. Please try again.")
