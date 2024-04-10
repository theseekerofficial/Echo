import os
import uuid
import logging
import requests
from pathlib import Path
from telegram import Update
from pymongo import MongoClient
from modules.token_system import TokenSystem
from modules.allowed_chats import allowed_chats_only
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

temp_dir = Path(__file__).parent / "Removebg_Temp"
temp_dir.mkdir(parents=True, exist_ok=True)

REMOVEBG_API_KEY = get_env_var_from_db("REMOVEBG_API")
MONGODB_URI = get_env_var_from_db("MONGODB_URI")

client = MongoClient(MONGODB_URI)
db = client["Echo"]

def set_rbg_api(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    api_key = ' '.join(context.args)
    
    if not api_key:
        update.message.reply_text("Please provide your remove.bg API key. Usage: /setrbgapi <your_api_key>")
        return

    db.RemoveBG_APIs.update_one(
        {'user_id': user_id},
        {'$set': {'api_key': api_key}},
        upsert=True
    )
    
    update.message.reply_html("Your remove.bg API key has been set successfully. ✅\n\n<i>⭕Use /showrbgapi to see you API Key.\n⭕Use /delrbgapi to delete your API Key from database.\n⭕Refer /help command for more info</i>")

def remove_background(update: Update, context: CallbackContext):
    removebg_plugin_enabled_str = get_env_var_from_db('REMOVEBG_PLUGIN')
    removebg_plugin_enabled = removebg_plugin_enabled_str.lower() == 'true' if removebg_plugin_enabled_str else False
    
    if removebg_plugin_enabled:
    
        user_id = update.effective_user.id
    
        user_api_data = db.RemoveBG_APIs.find_one({'user_id': user_id})
        user_api_key = user_api_data['api_key'] if user_api_data else None
    
        api_key_to_use = user_api_key if user_api_key else REMOVEBG_API_KEY
    
        if api_key_to_use:
            if update.message.reply_to_message and update.message.reply_to_message.photo:
                photo = update.message.reply_to_message.photo[-1]  
                context.user_data['photo_file_id'] = photo.file_id
            
                keyboard = [
                    [InlineKeyboardButton("Transparent Background (Recommended)", callback_data='background_transparent')],
                    [InlineKeyboardButton("Non-Transparent Background", callback_data='background_non_transparent')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_html('Choose the background type:\n\n<i>If you use free remove.bg API Key keep in mind about limits. You can see your key usage using /rbgusage command</i>', reply_markup=reply_markup)
            else:
                update.message.reply_text('Please reply to an image with /removebg to remove its background.')
                logger.info("User did not reply to an image ⚠️")
        else:
            update.message.reply_html("⚠️No Global or Personal remove.bg API found.\n\n<i>Please provide your remove.bg API key. Usage: /setrbgapi [your_api_key]</i>")
    else:
        update.message.reply_html("RemoveBG Plugin Disabled by the person who deployed this Echo Variant 💔")

def background_choice_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    background_choice = query.data
    user_id = update.effective_user.id

    user_api = db.RemoveBG_APIs.find_one({'user_id': user_id})
    api_key = user_api['api_key'] if user_api else REMOVEBG_API_KEY
    
    if 'photo_file_id' in context.user_data:
        photo_file_id = context.user_data['photo_file_id']
        file = context.bot.getFile(photo_file_id)
        query.message.delete()
        
        unique_filename = str(uuid.uuid4())
        temp_image_path = temp_dir / f"{unique_filename}_original.png"
        processed_image_path = temp_dir / f"{unique_filename}_processed.png"
        rbg_img_caption = "Powered by @Echo_AIO"
        
        file.download(custom_path=str(temp_image_path))

        try:
            headers = {'X-Api-Key': api_key}
            with open(temp_image_path, 'rb') as image_file:
                response = requests.post(
                    'https://api.remove.bg/v1.0/removebg',
                    files={'image_file': image_file},
                    headers=headers,
                    stream=True
                )

            if response.status_code == requests.codes.ok:
                with open(processed_image_path, 'wb') as out_file:
                    out_file.write(response.content)

                if background_choice == 'background_transparent':
                    with open(processed_image_path, 'rb') as final_image:
                        query.message.reply_document(document=final_image, filename=f"{unique_filename}_no_bg.png", caption=rbg_img_caption)
                        logger.info("Sent transparent background image as document 🪟")
                else:
                    with open(processed_image_path, 'rb') as final_image:
                        query.message.reply_photo(photo=final_image, caption=rbg_img_caption)
                        logger.info("Sent non-transparent background image as photo 🖼️")
            else:
                query.message.reply_text('Failed to remove background. Please try again later.')
                logger.error("Failed to remove background 😟")

        except Exception as e:
            logger.error(f"Error processing image ❌: {e}")
            query.message.reply_text('An error occurred while processing the image. Please try again.')
            
        finally:
            # Clean up: Remove the temporary files
            temp_image_path.unlink(missing_ok=True)
            processed_image_path.unlink(missing_ok=True)

    else:
        query.message.reply_text("An error occurred. Please try the command again.")
        logger.info("Photo file ID not found in user data. ❌")

    del context.user_data['photo_file_id']

def rbg_usage(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    owner_id = get_env_var_from_db("OWNER")
    authorized_users_str = get_env_var_from_db("AUTHORIZED_USERS")
    authorized_users = [int(user_id) for user_id in authorized_users_str.split(',')]

    user_api_data = db.RemoveBG_APIs.find_one({'user_id': user_id})
    user_api_key = user_api_data['api_key'] if user_api_data else None
    
    def get_api_usage(api_key):
        try:
            headers = {"X-Api-Key": api_key}
            response = requests.get("https://api.remove.bg/v1.0/account", headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                total_credits = response_data['data']['attributes']['credits']['total']
                subscription_credits = response_data['data']['attributes']['credits']['subscription']
                payg_credits = response_data['data']['attributes']['credits']['payg']
                enterprise_credits = response_data['data']['attributes']['credits']['enterprise']
                free_calls = response_data['data']['attributes']['api']['free_calls']
                return True, total_credits, subscription_credits, payg_credits, enterprise_credits, free_calls
        except Exception as e:
            logger.error(f"Error fetching API usage info: {e}")
            return False, None, None, None, None, None
        return False, None, None, None, None, None

    if str(user_id) == owner_id or str(user_id) in authorized_users:
        global_usage_message = "<i>No Global API key available.</i>\n\n"
        if REMOVEBG_API_KEY:
            success, total_credits, subscription_credits, payg_credits, enterprise_credits, free_calls = get_api_usage(REMOVEBG_API_KEY)
            if success:
                global_usage_message = f"<b><u>🌍 Global Remove.bg API Usage Information:</u></b>\n\n" \
                                       f"💳 <b>Total Credits:</b> {total_credits}\n" \
                                       f"🔄 <b>Subscription Credits:</b> {subscription_credits}\n" \
                                       f"💰 <b>Pay-As-You-Go Credits:</b> {payg_credits}\n" \
                                       f"🏢 <b>Enterprise Credits:</b> {enterprise_credits}\n" \
                                       f"🆓 <b>Free API Calls Left:</b> {free_calls}\n\n"

        personal_usage_message = "<i>No personal API key available.</i>"
        if user_api_key:
            success, total_credits, subscription_credits, payg_credits, enterprise_credits, free_calls = get_api_usage(user_api_key)
            if success:
                personal_usage_message = f"<b><u>👤 Personal Remove.bg API Usage Information:</u></b>\n\n" \
                                         f"💳 <b>Total Credits:</b> {total_credits}\n" \
                                         f"🔄 <b>Subscription Credits:</b> {subscription_credits}\n" \
                                         f"💰 <b>Pay-As-You-Go Credits:</b> {payg_credits}\n" \
                                         f"🏢 <b>Enterprise Credits:</b> {enterprise_credits}\n" \
                                         f"🆓 <b>Free API Calls Left:</b> {free_calls}"

        message = global_usage_message + personal_usage_message
        update.message.reply_html(message)

    else: 
        if user_api_key:
            success, total_credits, subscription_credits, payg_credits, enterprise_credits, free_calls = get_api_usage(user_api_key)
            if success:
                user_usage_message = f"<b><u>👤 Personal Remove.bg API Usage Information:</u></b>\n\n" \
                                         f"💳 <b>Total Credits:</b> {total_credits}\n" \
                                         f"🔄 <b>Subscription Credits:</b> {subscription_credits}\n" \
                                         f"💰 <b>Pay-As-You-Go Credits:</b> {payg_credits}\n" \
                                         f"🏢 <b>Enterprise Credits:</b> {enterprise_credits}\n" \
                                         f"🆓 <b>Free API Calls Left:</b> {free_calls}"
                update.message.reply_html(user_usage_message)
            else:
                update.message.reply_text("Failed to fetch API usage information for your key. Please try again later. ⚠️")
        else:
            update.message.reply_text("You haven't set a personal API key. Use /setrbgapi <your_api_key> to set up. 📐")

def show_rbg_api(update: Update, context: CallbackContext):
    removebg_plugin_enabled_str = get_env_var_from_db('REMOVEBG_PLUGIN')
    removebg_plugin_enabled = removebg_plugin_enabled_str.lower() == 'true' if removebg_plugin_enabled_str else False
    
    if removebg_plugin_enabled:
        user_id = update.effective_user.id
    
        user_api_data = db.RemoveBG_APIs.find_one({'user_id': user_id})
        if user_api_data:
            api_key = user_api_data['api_key']
            update.message.reply_text(f"Your remove.bg API key is:\n\n <code>{api_key}</code>", parse_mode='HTML')
        else:
            update.message.reply_text("You haven't set a personal API key. Use /setrbgapi <your_api_key> to set up. 📐")
    else:
        update.message.reply_html("RemoveBG Plugin Disabled by the person who deployed this Echo Variant 💔")

def del_rbg_api(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    result = db.RemoveBG_APIs.delete_one({'user_id': user_id})
    if result.deleted_count > 0:
        update.message.reply_text("Your remove.bg API key has been successfully deleted. ✅")
        logger.info(f"{user_id} Deleted his Removebg API Key ✅")
    else:
        update.message.reply_text("No personal API key found to delete. ⛔")

def setup_removebg(dp):    
    dp.add_handler(token_system.token_filter(CommandHandler('removebg', remove_background)))
    dp.add_handler(CommandHandler('setrbgapi', allowed_chats_only(set_rbg_api)))
    dp.add_handler(CommandHandler('showrbgapi', allowed_chats_only(show_rbg_api)))
    dp.add_handler(CommandHandler('delrbgapi', allowed_chats_only(del_rbg_api)))
    dp.add_handler(CommandHandler('rbgusage', allowed_chats_only(rbg_usage)))
    dp.add_handler(CallbackQueryHandler(background_choice_callback, pattern='^background_'))

