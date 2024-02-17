import os
import re
import base64
import logging
import pymongo
from telegram import Update
from dotenv import load_dotenv
from mimetypes import guess_type
import google.generativeai as genai
from telegram.error import Unauthorized
from modules.configurator import get_env_var_from_db
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters


# Load environment variables from config.env file
dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

# Read the GEMINI_PLUGIN environment variable
def is_gemini_plugin_enabled():
    gemini_plugin_str = get_env_var_from_db("GEMINI_PLUGIN")
    # Convert the string to a boolean: "true" (case insensitive) means enabled
    return gemini_plugin_str.lower() == "true" if gemini_plugin_str else False

# Use this function to check if Gemini plugin is enabled
gemini_plugin_enabled = is_gemini_plugin_enabled()

# MongoDB setup
mongo_uri = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(mongo_uri)
db = client["Echo"]
api_keys_collection = db["gemini_api"]
image_collection = db["image_data"]

# Set up basic logging
logging.basicConfig(filename='bot_log.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Function to clean up leftover images and records
def cleanup_leftover_images_and_records():
    temp_dir = 'temp_gemi4to'

    # Log that the cleanup process is starting
    logging.info("Starting cleanup process for leftover images and records")

    # Check if the directory exists
    if os.path.exists(temp_dir):
        files = os.listdir(temp_dir)
        
        for file in files:
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Log that image files have been removed
        logging.info("Removed leftover image files in the 'temp_gemi4to' directory")

    # Remove records from MongoDB "image_data" collection
    deleted_count = image_collection.delete_many({})

    # Log the number of records deleted
    logging.info(f"Deleted {deleted_count.deleted_count} records from the 'image_data' collection in MongoDB")

    # Log that the cleanup process is complete
    logging.info("Cleanup process completed")

# Add a call to the cleanup function before starting the bot
cleanup_leftover_images_and_records()

# Initialize the Gemini model
def initialize_gemini_model():
    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 8192,
    }
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        safety_settings=[]
    )
    return model

def format_html(text):
    text = text.replace('&', '&amp;')  # Escape HTML special characters
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')

    # Replace Markdown bold with HTML bold tags
    bold_parts = text.split('**')
    formatted_text = ''
    for i, part in enumerate(bold_parts):
        if i % 2 == 0:
            # Replace Markdown code block with HTML preformatted text
            part = part.replace('```python', '<pre>').replace('```', '</pre>')
            formatted_text += part
        else:
            # Bold text
            formatted_text += '<b>' + part + '</b>'
    
    return formatted_text

# Handle the /gemini command
def handle_gemini_command(update: Update, context: CallbackContext):
    
    if not gemini_plugin_enabled:
        update.message.reply_text("Gemini AI Plugin Disabled by the Person who deployed this Echo variant 💔")
        return
        
    user_id = update.effective_user.id
    logging.info(f"User {user_id} invoked /gemini command")
    user_id = update.effective_user.id

    # Check if the user has provided any text input
    if not update.message.text or len(update.message.text.split()) < 2:
        update.message.reply_text("Please send the command with a text message 💬")
        return

    # Check if the user has an API key set
    user_api_key = api_keys_collection.find_one({"user_id": user_id})
    if not user_api_key:
        update.message.reply_text("You need to set your API key first using /mygapi command.")
        return

    # Configure the API key for the Google Generative AI library
    genai.configure(api_key=user_api_key['api_key'])

    gemini_model = initialize_gemini_model()
    query = update.message.text.split('/gemini ', 1)[1]

    try:
        response = gemini_model.generate_content({"text": query})  
        formatted_response = format_html(response.text)
        update.message.reply_text(formatted_response, parse_mode='HTML')
    except Exception as e:
        logging.error(f"Error using Gemini model: {e}")
        update.message.reply_text("Sorry, there was an error processing your request. Please Try again")

# Handle the /mygapi command
def handle_mygapi_command(update: Update, context: CallbackContext):
    if not gemini_plugin_enabled:
        update.message.reply_text("Gemini Plugin Disabled by This bot deployed Person")
        return
    user_id = update.effective_user.id
    logging.info(f"User {user_id} saved new API key to database")
    user_id = update.effective_user.id
    api_key_message = update.message.text.split('/mygapi ', 1)

    if len(api_key_message) < 2 or not api_key_message[1]:
        # If the user didn't provide an API key, handle the error
        update.message.reply_text("Hey you doing someting wrong.❌ Please provide your API key as /mygapi your_api_key format. To get an API key go to - https://makersuite.google.com/app/apikey ")
        return

    api_key = api_key_message[1]

    # Store or update the user's API key
    api_keys_collection.update_one({"user_id": user_id}, {"$set": {"api_key": api_key}}, upsert=True)
    update.message.reply_text("Your API key has been set successfully.")

# Handle the /delmygapi command
def handle_delmygapi_command(update: Update, context: CallbackContext):
    if not gemini_plugin_enabled:
        update.message.reply_text("Gemini Plugin Disabled by This bot deployed Person")
        return
    user_id = update.effective_user.id
    logging.info(f"User {user_id} invoked /delmygapi command")
    user_id = update.effective_user.id

    # Delete the user's API key
    result = api_keys_collection.delete_one({"user_id": user_id})

    if result.deleted_count > 0:
        update.message.reply_text("Your API key has been deleted successfully.")
        logging.info(f"User {user_id} deleted his G-API")
    else:
        update.message.reply_text("No API key found for your account.")

# Handle the /showmygapi command
def handle_showmygapi_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if update.message.chat.type == 'private':
        # The command is called in PM, show the API key directly
        send_api_key_to_user(update.message.reply_text, user_id)
    else:
        # The command is called in a group chat
        stylish_message = "⚠️ <b>Please use this command in your bot PM.</b>\n<i>(To protect your privacy and API Key)</i>"
        update.message.reply_text(stylish_message, parse_mode='HTML')

def send_api_key_to_user(reply_function, user_id):
    user_api_key = api_keys_collection.find_one({"user_id": user_id})
    if user_api_key:
        api_key_message = f"Your API key is:\n<code>{user_api_key['api_key']}</code>"
        reply_function(api_key_message, parse_mode='HTML')
    else:
        reply_function("No G-API key found for your account.")

def initialize_gemini_model_for_images():
    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 8192,
    }

    # Initialize the Gemini model with the specific model name for image processing
    model = genai.GenerativeModel(
        model_name="gemini-pro-vision",  # Use this model for image processing
        generation_config=generation_config,
        safety_settings=[]
    )
    return model

# Then use this model in your image processing handlers
gemini_image_model = initialize_gemini_model_for_images()

def is_gemini_image_plugin_enabled():
    gemini_image_plugin_str = get_env_var_from_db("GEMINI_IMAGE_PLUGIN")
    # Convert the string to a boolean: "true" (case insensitive) means enabled
    return gemini_image_plugin_str.lower() == "true" if gemini_image_plugin_str else False
    
# Handler for /analyze4to command
def analyze4to_handler(update: Update, context: CallbackContext):
    gemini_image_plugin_enabled = is_gemini_image_plugin_enabled()

    if not gemini_image_plugin_enabled:
        update.message.reply_text("Gemini Image Analyze Plugin Disabled by the Person who deployed this Echo variant 💔")
        return

    user_id = update.effective_user.id

    # Fetch the user's API key from the database
    user_api_key_entry = api_keys_collection.find_one({"user_id": user_id})
    if not user_api_key_entry or "api_key" not in user_api_key_entry:
        update.message.reply_text("Please set your API key using /myapi first. Refer /help cmd for more 📖 (Like how to get an API Key and more)\n\nSo hurry up! We have a journey to complete!✨")
        return

    logging.info(f"Using {user_id}'s API key for image processing⚙️")
    
    # Configure the Gemini API with the user's API key
    user_api_key = user_api_key_entry["api_key"]
    genai.configure(api_key=user_api_key)

    if update.message.reply_to_message and update.message.reply_to_message.photo:
        photo_id = update.message.reply_to_message.photo[-1].file_id
        photo_file = update.message.reply_to_message.photo[-1].get_file()

        # Extract user-specific instructions if provided
        user_instructions = update.message.text.split(' ', 1)
        instructions = user_instructions[1] if len(user_instructions) > 1 else ""

        # Directory to store temporary images
        temp_dir = 'temp_gemi4to'

        # Check if the directory exists, if not, create it
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Save the photo in the temporary directory with a unique identifier
        file_path = os.path.join(temp_dir, f'{photo_id}.jpg')
        photo_file.download(file_path)

        try:
            with open(file_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            contents = {
                "parts": [
                    {"text": instructions},  # User-specific instructions
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }

            # Send the content to the Gemini model for analysis
            response = gemini_image_model.generate_content(contents=contents)
            formatted_response = format_html(response.text)
            update.message.reply_text(formatted_response, parse_mode='HTML')

            logging.info(f"Gemini's Respond sent to {user_id} successfully ✅")
            
            # After sending the response, delete the image file
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            logging.error(f"Error using Gemini model with image: {e}")
            update.message.reply_text("Sorry 💔, there was an error processing your request: {str(e)}.\n\n 💁Tips: Try using different API, Try after few hours, Try to analyze different image")

    else:
        update.message.reply_text("Wanna analyze some images?👀 \nStart by replying to an image with this command.")

# Add additional logging for error handling
def error_callback(update: Update, context: CallbackContext):
    logging.error(f"An error occurred: {context.error}")

