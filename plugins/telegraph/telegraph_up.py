import os
import logging
import requests
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, CommandHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup


# Set up logging for this module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_temp_directory(directory_name="temp_tgph_img"):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

def clear_leftover_images(directory_name="temp_tgph_img"):
    create_temp_directory(directory_name)
    count = 0
    for filename in os.listdir(directory_name):
        file_path = os.path.join(directory_name, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            count += 1
    logger.info(f"🧹 Cleared {count} leftover image(s) from {directory_name}.")

def upload_to_telegraph(update: Update, context: CallbackContext):
    telegraph_up_plugin_enabled_str = get_env_var_from_db('TELEGRAPH_UP_PLUGIN')
    telegraph_up_plugin_enabled = telegraph_up_plugin_enabled_str.lower() == 'true' if telegraph_up_plugin_enabled_str else False

    if telegraph_up_plugin_enabled:
        user = update.message.from_user
        chat_id = update.message.chat_id

        message = update.message.reply_text("🚀 Uploading your image to telegraph... Just gimme 5sec ⏳")

        if update.message.reply_to_message and update.message.reply_to_message.photo:
            photo = update.message.reply_to_message.photo[-1].get_file()
        else:
            message.edit_text("❗ Please reply to an image with this command.")
            return

        temp_img_path = os.path.join("temp_tgph_img", f"temp_photo_{chat_id}.jpg")
        photo.download(temp_img_path)

        url = 'https://telegra.ph/upload'
        with open(temp_img_path, 'rb') as file:
            response = requests.post(url, files={'file': file})

        os.remove(temp_img_path)

        if response.status_code == 200:
            result = response.json()
            image_url = 'https://telegra.ph' + result[0]['src']

            share_button = InlineKeyboardButton("Share Now☘️", url=f"https://telegram.me/share/url?url={image_url}")
            reply_markup = InlineKeyboardMarkup([[share_button]])

            message.edit_text(f"✅ Your Image Successfully Uploaded to Telegraph🚀\n\n"
                              f"Your Link 🔗 : {image_url}\n\n"
                              f"Uploaded with ECHO!",
                              reply_markup=reply_markup)

            logger.info(f"📤 User {user.username or user.id} uploaded an image to Telegraph.")
        else:
            message.edit_text("❌ Failed to upload the image.")
            logger.error(f"⚠️ User {user.username or user.id} failed to upload an image to Telegraph.")
    else:
        update.message.reply_text("Telegraph Image Upload Plugin Disabled by the person who deployed this Echo Variant 💔")

def setup_dispatcher(dispatcher):
    clear_leftover_images()
    dispatcher.add_handler(CommandHandler('uptotgph', upload_to_telegraph))
