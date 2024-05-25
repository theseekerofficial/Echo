# super_plugins/guardian/logger/logger.py
import os
import re
from loguru import logger
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackContext, MessageHandler, Filters, CallbackQueryHandler

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def logger_setup_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        user_id = query.from_user.id
        chat_id = query.data.split('_')[-1]
        chat_name = context.bot.get_chat(chat_id).title
    else:
        user_id = context.user_data.get('sended_user_id')
        chat_id = context.user_data.get('group_chat_id')
        chat_name = context.bot.get_chat(chat_id).title
        need_to_edit_msg = context.user_data['need_to_edit_logger_msg']

    chat_member = context.bot.get_chat_member(chat_id, user_id)
    bot_member = context.bot.get_chat_member(chat_id, context.bot.id)

    required_permissions = ['can_change_info', 'can_delete_messages', 'can_invite_users', 'can_pin_messages']
    
    if query:
        missing_bot_perms = [perm for perm in required_permissions if not getattr(bot_member, perm, False)]
        if missing_bot_perms:
            query.answer(f"Bot is missing required permissions: {', '.join(missing_bot_perms)}.", show_alert=True)
            return
            
        if chat_member.status == 'creator':
            pass
        else:
            missing_user_perms = [perm for perm in required_permissions if not getattr(chat_member, perm, False)]
            if missing_user_perms:
                query.answer(f"You are missing required permissions: {', '.join(missing_user_perms)}.", show_alert=True)
                logger.warning(f"Unauthorized attempted to access logger menu by [{user_id}]")
                return
    
    collection = db[str(chat_id)]
    log_chat = collection.find_one({'identifier': 'logger'})
    if not log_chat:
        logger.info(f"No Logger config found for [{chat_id}]. Using default settings")

    if log_chat:
        logger_state = log_chat.get('logger_state', False)
    else:
        logger_state = False
        
    logger_status_text = "Activated" if logger_state else "Deactivated"
    logger_button_text = "❌ Deactivate Logger" if logger_state else "✅ Activate Logger"
    
    if log_chat and 'log_chat' in log_chat:
        status_text = "<i>Logger Chat</i>: ✅"
    else:
        status_text = "<i>Logger Chat</i>: ❌"
    
    message = f"<b>📝 Set up a Log Chat</b>\n\n<i>Track your <code>{chat_name}</code> group action and recent activity easily with Logger.</i>\n\n<code>Click 'Setup chat' to setup a chat (Both group and channels are supported)</code>\n<code>Use 'Action Selector' to set what components to log in your group</code>\n\n⚡ Feature Status: <code>{logger_status_text}</code>\n\n{status_text}"
    keyboard = [
        [InlineKeyboardButton("Setup Chat ⚙️", callback_data=f"grd_logger_setup_{chat_id}"),
         InlineKeyboardButton("Action Selector 🎭", callback_data=f"grd_logger_action_{chat_id}")],
        [InlineKeyboardButton(logger_button_text, callback_data=f"grd_logger_toggle_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"grd_back_to_primary_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        context.bot.edit_message_text(chat_id=user_id, text=message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg)
        
    context.user_data.pop('sended_user_id', None)
    context.user_data.pop('expecting_logger_chat_id', None)
    context.user_data.pop('group_chat_id', None)
    context.user_data.pop('need_to_edit_logger_msg', None)

def handle_logger_setup(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat_name = context.bot.get_chat(chat_id).title
    bot_username = context.bot.username
    collection = db[str(chat_id)]
    log_chat = collection.find_one({'identifier': 'logger'})

    if log_chat:
        log_chat_id = log_chat.get('log_chat', 'Not set')
    else:
        log_chat_id = "Not set"

    keyboard = [
        [InlineKeyboardButton("Delete ♻️", callback_data=f"grd_logger_delete_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"logger_back_to_main_menu_{chat_id}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"Send the chat ID of the chat where you want to send logs of your {chat_name}.\n\n<u>Conditions</u>\n<code>You must be the owner of the log chat. \n{bot_username} must be admin in that log chat</code>\n\n<i>Current Log chat:</i> <code>{log_chat_id}</code>"
    msg = query.edit_message_text(text=message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['expecting_logger_chat_id'] = True
    context.user_data['group_chat_id'] = chat_id
    context.user_data['need_to_edit_logger_msg'] = msg.message_id

def chat_id_handler(update: Update, context: CallbackContext):
    if 'expecting_logger_chat_id' not in context.user_data:
        return
        
    if context.user_data['expecting_logger_chat_id']:
        chat_id = update.message.text.strip()
        if not re.match(r'^-100\d+', chat_id):
            update.message.reply_text("Invalid Chat ID. Send a Log Chat ID starting with '-100'")
            return

        try:
            chat_member = context.bot.get_chat_member(chat_id, context.bot.id)
            if chat_member.status not in ['administrator', 'creator']:
                update.message.reply_text("The bot is not an admin in the provided chat. Please add the bot as an admin and try again.")
                return
        except Exception as e:
            update.message.reply_text(str(e))
            return
        
        context.user_data['sended_user_id'] = update.message.from_user.id
        group_chat_id = context.user_data.get('group_chat_id')

        collection = db[group_chat_id]

        collection.update_one(
            {'identifier': 'logger'},
            {'$set': {'log_chat': chat_id}},
            upsert=True
        )
        logger.info(f"New logger chat saved for [{group_chat_id}]")

        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        
        logger_setup_menu(update, context)

def handle_logger_toggle(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]

    collection = db[str(chat_id)]
    log_chat = collection.find_one({'identifier': 'logger'})
    if log_chat:
        current_state = log_chat.get('logger_state', False)
    else:
        current_state = False
    
    collection.update_one({'identifier': 'logger'}, {'$set': {'logger_state': not current_state}}, upsert=True)
    logger.info(f"Logger status change from {current_state} to {not current_state} in [{chat_id}]")

    logger_setup_menu(update, context)

def handle_logger_action_selector(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat_name = context.bot.get_chat(chat_id).title

    collection = db[str(chat_id)]
    log_settings = collection.find_one({'identifier': 'logger'})

    if log_settings:
        log_welcomer = log_settings.get('log_welcomer', False)
        log_goodbye = log_settings.get('log_goodbye', False)
        log_rules = log_settings.get('log_rules', False)
        log_min_chngs = log_settings.get('log_min_chngs', False)
        log_captcha = log_settings.get('log_captcha', False)
        log_link_gen = log_settings.get('log_linkgen', False)
    else:
        log_welcomer = False
        log_goodbye = False
        log_rules = False
        log_min_chngs = False
        log_captcha = False
        log_link_gen = False


    keyboard = [
        [InlineKeyboardButton(f"Welcomer [{'✅' if log_welcomer else '❌'}]", callback_data=f"log_toggle_welcomer_{chat_id}"),
         InlineKeyboardButton(f"Goodbye [{'✅' if log_goodbye else '❌'}]", callback_data=f"log_toggle_goodbye_{chat_id}")],
        [InlineKeyboardButton(f"Rules [{'✅' if log_rules else '❌'}]", callback_data=f"log_toggle_rules_{chat_id}"),
         InlineKeyboardButton(f"Captcha [{'✅' if log_captcha else '❌'}]", callback_data=f"log_toggle_captcha_{chat_id}")],
        [InlineKeyboardButton(f"Link Gen [{'✅' if log_link_gen else '❌'}]", callback_data=f"log_toggle_linkgen_{chat_id}"),
         InlineKeyboardButton(f"Minor Changes [{'✅' if log_min_chngs else '❌'}]", callback_data=f"log_toggle_minchngs_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"logger_back_to_main_menu_{chat_id}")]
    ]

    log_wlc_text = 'Activated ✅' if log_welcomer else 'Deactivated ❌'
    log_gby_text = 'Activated ✅' if log_goodbye else 'Deactivated ❌'
    log_ruls_text = 'Activated ✅' if log_rules else 'Deactivated ❌'
    log_captcha_text = 'Activated ✅' if log_captcha else 'Deactivated ❌'
    log_minchngs_text = 'Activated ✅' if log_min_chngs else 'Deactivated ❌'
    log_linkgen_text = 'Activated ✅' if log_link_gen else 'Deactivated ❌'
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"<i>Select the elements you want to log in your {chat_name} group.</i>\n\n<b><i>Welcomer</i></b>:\n└ <code>{log_wlc_text}</code>\n<b><i>Goodbye</i></b>:\n└ <code>{log_gby_text}</code>\n<b><i>Rules</i></b>:\n└ <code>{log_ruls_text}</code>\n<b><i>Captcha</i></b>:\n└ <code>{log_captcha_text}</code>\n<b><i>Link Gen</i></b>:\n└ <code>{log_linkgen_text}</code>\n<b><i>Minor Chnages</i></b>:\n└ <code>{log_minchngs_text}</code>"
    query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def handle_logger_feature_toggle(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    feature = query.data.split('_')[-2]

    if feature == "minchngs":
        feature = "min_chngs"
    
    collection = db[str(chat_id)]
    log_settings = collection.find_one({'identifier': 'logger'}) or {}
    
    if log_settings:
        current_state = log_settings.get(f"log_{feature}", False)
    else:
        current_state = False
        
    collection.update_one({'identifier': 'logger'}, {'$set': {f"log_{feature}": not current_state}}, upsert=True)

    handle_logger_action_selector(update, context)

def handle_logger_delete(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]
    result = collection.update_one({'identifier': 'logger'}, {'$unset': {'log_chat': ""}})

    if result.modified_count > 0:
        query.answer("Chat ID Deleted Successfully", show_alert=True)
    else:
        query.answer("No Chat ID to delete or already deleted", show_alert=True)

    logger_setup_menu(update, context)

def setup_logger(dp):
    dp.add_handler(CallbackQueryHandler(logger_setup_menu, pattern=r"^set_logger_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_logger_setup, pattern=r"^grd_logger_setup_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_logger_toggle, pattern=r"^grd_logger_toggle_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(logger_setup_menu, pattern=r"^logger_back_to_main_menu_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_logger_action_selector, pattern=r"^grd_logger_action_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_logger_feature_toggle, pattern=r"^log_toggle_(welcomer|goodbye|rules|captcha|linkgen|minchngs)_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_logger_delete, pattern=r"^grd_logger_delete_-(\d+)$"))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command, chat_id_handler), group=21)
