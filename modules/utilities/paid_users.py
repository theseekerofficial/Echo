# paid_users.py
import os
import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
from modules.allowed_chats import allowed_chats_only
from modules.configurator import get_env_var_from_db
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_paid(update: Update, context: CallbackContext):
    owner_id = get_env_var_from_db("OWNER")
    message = update.message.text.split()
    user_id = update.message.from_user.id

    if str(user_id) != owner_id:
        logger.warning(f"⚠️ Unauthorized access attempt to add paid users by {user_id}")
        update.message.reply_text("You do not have permission to use this command.")
        return

    if len(message) != 3:
        update.message.reply_html("Incorrect format. Use <code>/addpaid {subscription expire date - DD-MM-YYYY} {user_id of paid user}.</code>\n\nExample - <code>/addpaid 20-04-2024 123456789</code>")
        return

    _, expire_date, paid_user_id = message
    try:
        datetime.strptime(expire_date, "%d-%m-%Y")
        paid_user_id = int(paid_user_id)
    except ValueError:
        update.message.reply_text("Incorrect date format or user ID. Please use the format DD-MM-YYYY for date and provide a valid user ID.")
        return

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.Echo
    paid_users_collection = db.Paid_Users

    result = paid_users_collection.update_one(
        {"user_id": paid_user_id}, 
        {"$set": {
            "expire_date": expire_date, 
            "activated_date": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        }}, 
        upsert=True
    )

    if result.matched_count:
        update.message.reply_text(f"💸 Paid user {paid_user_id} updated successfully.")
        logger.info(f"💸 Paid user updated: User ID {paid_user_id}, Expire Date: {expire_date}")
    else:
        update.message.reply_text(f"💸 New paid user {paid_user_id} added successfully.")
        logger.info(f"💸 New paid user added: User ID {paid_user_id}, Expire Date: {expire_date}")

def show_paid_users(update: Update, context: CallbackContext):
    owner_id = get_env_var_from_db("OWNER")
    user_id = update.effective_user.id if update.effective_user else None  

    if str(user_id) != owner_id:
        if update.callback_query:
            update.callback_query.answer("You do not have permission to use this command.", show_alert=True)
            logger.warning(f"⚠️ Unauthorized access attempt to see paid users by {user_id}")
        else:
            update.message.reply_text("You do not have permission to use this command.")
            logger.warning(f"⚠️ Unauthorized access attempt to see paid users by {user_id}")
        return
    
    query = update.callback_query
    if query:
        page = int(query.data.split('_')[-1])
    else:
        page = 0

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.Echo
    paid_users_collection = db.Paid_Users

    all_paid_users = list(paid_users_collection.find({}))
    page_size = 8
    paginated_users = all_paid_users[page*page_size:(page+1)*page_size]

    keyboard = []
    temp_row = []

    for index, user in enumerate(paginated_users, start=1):
        try:
            user_info = context.bot.get_chat(user["user_id"])
            user_name = user_info.first_name if user_info.first_name else str(user["user_id"])
        except Exception:
            user_name = str(user["user_id"])
        temp_row.append(InlineKeyboardButton(user_name, callback_data=f"pu_user_{user['user_id']}_{page}")) 

        if index % 2 == 0 or index == len(paginated_users):
            keyboard.append(temp_row)
            temp_row = []

    total_users = paid_users_collection.count_documents({})
    if total_users == 0:
        update.message.reply_text(f"You did not have any paid users :(")
        return
    total_pages = (total_users + page_size - 1) // page_size
    
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("Previous", callback_data=f"pu_page_{page-1}"))
    navigation_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if (page+1) * page_size < total_users:
        navigation_buttons.append(InlineKeyboardButton("Next", callback_data=f"pu_page_{page+1}"))

    if navigation_buttons:
        keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Here are your paid users:" if not query else "Select a user:"

    if query:
        query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text=text, reply_markup=reply_markup)

def paid_user_details(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    user_id = int(parts[2])
    usager_id = update.effective_user.id
    page = int(parts[3])
    owner_id = get_env_var_from_db("OWNER")

    if str(usager_id) != owner_id:
        if update.callback_query:
            update.callback_query.answer("You do not have permission to use this command.", show_alert=True)
            logger.warning(f"⚠️ Unauthorized access attempt to see paid users by {usager_id}")
            return

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.Echo
    paid_user = db.Paid_Users.find_one({"user_id": user_id})

    if paid_user:
        try:
            user_info = context.bot.get_chat(user_id)
            user_name = user_info.first_name if user_info.first_name else "Not available"
            username = "@" + user_info.username if user_info.username else "Not available"
        except Exception:
            user_name = "Not available"
            username = "Not available"

        activated_date_str = paid_user.get("activated_date", "Not available")
        expire_date_str = paid_user.get("expire_date", "Not available")
        days_to_expire = "Not calculated"

        if "activated_date" in paid_user and "expire_date" in paid_user:
            try:
                activated_date = datetime.strptime(activated_date_str, "%d-%m-%Y %H:%M:%S")
                expire_date = datetime.strptime(expire_date_str, "%d-%m-%Y")
                days_to_expire = (expire_date - datetime.now()).days
            except ValueError:
                days_to_expire = "Error calculating"

        details = (f"🔷User ID: <code>{user_id}</code>\n"
                   f"🔷Username: {username}\n"
                   f"🔷Telegram Name: <code>{user_name}</code>\n"
                   f"🔷Activated Date: <code>{activated_date_str}</code>\n"
                   f"🔷Expire Date: <code>{expire_date_str}</code>\n"
                   f"🔷Days to Expire: <code>{days_to_expire}</code>")

        keyboard = [
            [InlineKeyboardButton("Back", callback_data=f"pu_back_{page}")],
            [InlineKeyboardButton("Delete this User", callback_data=f"pu_delete_{user_id}_{page}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(text=details, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        query.edit_message_text(text="User not found.")

def back_to_list(update: Update, context: CallbackContext):
    query = update.callback_query
    page = int(query.data.split('_')[-1])
    context.args = [str(page)]  
    show_paid_users(update, context)

def confirm_user_deletion(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    user_id = int(parts[2])
    page = int(parts[3])  

    text = f"Do you want to delete this paid user ({user_id}) from the database?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"pu_delete_confirm_{user_id}_{page}")],
        [InlineKeyboardButton("No", callback_data=f"pu_user_{user_id}_{page}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def delete_paid_user(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split("_")
    user_id = int(parts[3])
    page = int(parts[4])

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client.Echo
    db.Paid_Users.delete_one({"user_id": user_id})
    logger.info(f"🗑️ Paid user deleted: User ID {user_id}")

    query.answer(f"Paid user {user_id} deleted successfully.", show_alert=True)
    
    context.args = [str(page)]
    show_paid_users(update, context)

def paid_users_handlers(dp):
    dp.add_handler(CommandHandler('addpaid', allowed_chats_only(add_paid)))
    dp.add_handler(CommandHandler('paid', allowed_chats_only(show_paid_users)))
    dp.add_handler(CallbackQueryHandler(back_to_list, pattern='^pu_back_'))
    dp.add_handler(CallbackQueryHandler(paid_user_details, pattern='^pu_user_'))
    dp.add_handler(CallbackQueryHandler(show_paid_users, pattern='^pu_page_'))
    dp.add_handler(CallbackQueryHandler(delete_paid_user, pattern='^pu_delete_confirm_'))
    dp.add_handler(CallbackQueryHandler(confirm_user_deletion, pattern='^pu_delete_'))
    dp.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.answer(), pattern='^noop$'))
