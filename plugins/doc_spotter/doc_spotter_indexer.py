import os
import logging
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Filters, MessageHandler, Updater

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["Echo_Doc_Spotter"]

# Command handler for /docspotter
def docspotter_command(update: Update, context: CallbackContext) -> None:
    doc_spotter_plugin_enabled_str = get_env_var_from_db('DOC_SPOTTER_PLUGIN')
    doc_spotter_plugin_enabled = doc_spotter_plugin_enabled_str.lower() == 'true' if doc_spotter_plugin_enabled_str else False

    if doc_spotter_plugin_enabled:
        keyboard = [
            [InlineKeyboardButton("Index Files", callback_data='index_files')],
            [InlineKeyboardButton("Set Up Group(s) to Begin Spotting", callback_data='setup_group')],
            [InlineKeyboardButton("Setup F-Sub for Listening Group(s)", callback_data='setup_fsub')],
            [InlineKeyboardButton("Manage Index/Listen/F-Sub Chats", callback_data='manage_indexers')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Select Process Mode for Doc Spotter Module:', reply_markup=reply_markup)
    else:
        update.message.reply_text("Doc Spotter Plugin Disabled by the Person who deployed this Echo variant 💔")

# Implement the manage_indexers callback
def manage_indexers_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("Manage Index Channel(s)", callback_data='dsi_manage_index_channels')],
        [InlineKeyboardButton("Manage Listening Group(s)", callback_data='dsi_manage_listening_groups')],
        [InlineKeyboardButton("Manage F-Sub Chat(s)", callback_data='dsi_manage_fsub_chats')],
        [InlineKeyboardButton("Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Now Choose an option to proceed", reply_markup=reply_markup)

# Implement the manage_index_channels callback
def manage_index_channels_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    indexed_channels = list(client["Echo_Doc_Spotter"]["Indexed_Channels"].find({"user_id": user_id}))
    keyboard = []

    if not indexed_channels:
        keyboard.append([InlineKeyboardButton("No Indexed Channels Found", callback_data='no_action')])
    else:
        for channel in indexed_channels:
            channel_id = channel["channel_id"]
            try:
                chat_info = context.bot.get_chat(channel_id)
                chat_name = chat_info.title
            except Exception as e:
                logging.error(f"Error fetching chat {channel_id}: {e}")
                chat_name = "Channel"
            button_label = f"{chat_name} [{channel_id}]"
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f'dsi_channel_{channel_id}')])

    keyboard.append([InlineKeyboardButton("Back", callback_data='dsi_back_to_indexers')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Here are your Indexed Channels:", reply_markup=reply_markup)

def manage_listening_groups_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    listening_groups = list(client["Echo_Doc_Spotter"]["Listening_Groups"].find({"user_id": user_id}))
    keyboard = []

    if not listening_groups:
        keyboard.append([InlineKeyboardButton("No Listening Groups Found", callback_data='no_action')])
    else:
        for group in listening_groups:
            group_id = group["group_id"]
            try:
                chat_info = context.bot.get_chat(group_id)
                chat_name = chat_info.title
            except Exception as e:
                logging.error(f"Error fetching chat {group_id}: {e}")
                chat_name = "Group"
            button_label = f"{chat_name} [{group_id}]"
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f'dsi_group_{group_id}')])

    keyboard.append([InlineKeyboardButton("Back", callback_data='dsi_back_to_indexers')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Here are your Listening Groups:", reply_markup=reply_markup)

def manage_fsub_chats_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    fsub_chats = list(client["Echo_Doc_Spotter"]["Fsub_Chats"].find({"user_id": user_id}))
    keyboard = []

    if not fsub_chats:
        keyboard.append([InlineKeyboardButton("No F-Sub Chats Found", callback_data='no_action')])
    else:
        for fsub_chat in fsub_chats:
            fsub_chat_id = fsub_chat["chat_id"]
            try:
                chat_info = context.bot.get_chat(fsub_chat_id)
                chat_name = chat_info.title
            except Exception as e:
                logging.error(f"Error fetching chat {fsub_chat_id}: {e}")
                chat_name = "Chat"
            button_label = f"{chat_name} [{fsub_chat_id}]"
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f'dsi_fsub_{fsub_chat_id}')])

    keyboard.append([InlineKeyboardButton("Back", callback_data='dsi_back_to_indexers')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Here are your F-Sub chats:", reply_markup=reply_markup)

def back_to_main_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    # Prepare the original keyboard layout
    keyboard = [
        [InlineKeyboardButton("Index Files", callback_data='index_files')],
        [InlineKeyboardButton("Set Up Group(s) to Begin Spotting", callback_data='setup_group')],
        [InlineKeyboardButton("Setup F-Sub for Listening Group(s)", callback_data='setup_fsub')],
        [InlineKeyboardButton("Manage Index/Listen/F-Sub Chats", callback_data='manage_indexers')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.message:
        query.edit_message_text(text='Select Process Mode for Doc Spotter Module:', reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Select Process Mode for Doc Spotter Module:', reply_markup=reply_markup)

def setup_fsub_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    text = "Let's setup F-Sub for your Listening Group(s). Follow these steps.\n\n" \
           "1) Add me to your F-Sub chat [channel/group] as an admin\n" \
           "2) Send Telegram id of your F-Sub chat."
    keyboard = [[InlineKeyboardButton("Back", callback_data='back_to_main')]]  # Optionally provide a way back
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    context.user_data['awaiting_fsub_chat_id'] = True 

# Implement the channel selection callback with Yes/No options for deletion
def channel_selected_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    channel_id = query.data.split('_')[2]  
    query.answer()

    confirmation_message = f"Are you want to stop indexing and delete the selected channel from my database?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f'dsi_delete_channel_{channel_id}')],  
        [InlineKeyboardButton("No", callback_data='dsi_manage_index_channels')]  
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=confirmation_message, reply_markup=reply_markup)

def group_selected_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    group_id = query.data.split('_')[2]  
    query.answer()

    confirmation_message = f"Do you want me to stop listening and delete the selected group from my database?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f'dsi_delete_group_{group_id}')],
        [InlineKeyboardButton("No", callback_data='dsi_manage_listening_groups')]  
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=confirmation_message, reply_markup=reply_markup)

def fsub_selected_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.data.split('_')[2]
    query.answer()

    confirmation_message = "Do you want to stop using and delete the selected F-Sub chat from my database?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f'dsi_delete_fsub_{chat_id}')],
        [InlineKeyboardButton("No", callback_data='dsi_manage_fsub_chats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=confirmation_message, reply_markup=reply_markup)

# Implement the deletion callback
def delete_channel_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    channel_id = query.data.split('_')[3]  
    result = db["Indexed_Channels"].delete_one({"channel_id": channel_id})
    if result.deleted_count > 0:
        query.answer("Channel removed.")
        logger.info(f"🗑️ Indexed channel deleted: {channel_id} by user {update.effective_user.id}")
    else:
        query.answer("Failed to remove channel or channel not found.")
    # Refresh the list of channels
    manage_index_channels_callback(update, context)

def delete_group_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    group_id = query.data.split('_')[3]  
    result = db["Listening_Groups"].delete_one({"group_id": group_id})
    if result.deleted_count > 0:
        query.answer("Group removed.")
        logger.info(f"🗑️ Listening group deleted: {group_id} by user {update.effective_user.id}")
    else:
        query.answer("Failed to remove group or group not found.")
    # Refresh the list of groups
    manage_listening_groups_callback(update, context)

def delete_fsub_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.data.split('_')[3]
    result = db["Fsub_Chats"].delete_one({"chat_id": chat_id})
    if result.deleted_count > 0:
        query.answer("F-Sub chat removed.")
        logger.info(f"🗑️ F-Sub chat deleted: {chat_id} by user {update.effective_user.id}")
    else:
        query.answer("Failed to remove F-Sub chat or chat not found.")
    # Refresh the list of fsubs
    manage_fsub_chats_callback(update, context)

# New Callback handler for "Set Up Group(s) to Begin Spotting" button
def setup_group_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    text = "Okay, Now here are the steps.\n\n1) Add me to your group as an Admin with necessary permissions\n2) Send me your group's ID [e.g. -100123456789]"
    keyboard = [[InlineKeyboardButton("Back", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    context.user_data['awaiting_group_id'] = True  # Set a flag indicating we're now waiting for a group ID

# Callback handler for "Index Files" button
def index_files_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("Setup a channel for indexing", callback_data='setup_channel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Echo's Doc Spotter", reply_markup=reply_markup)

# Callback handler for "Setup a channel for indexing" button
def setup_channel_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    text = "Okay, follow this,\n\n1) Add me to your source channel as admin\n2) After that, send me your channel's ID [Starting with -100| e.g. -1001654958246]"
    keyboard = [[InlineKeyboardButton("Back", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    context.user_data['awaiting_channel_id'] = True  # Set a flag indicating we're now waiting for a channel ID

def handle_text(update: Update, context: CallbackContext) -> None:
    user_data = context.user_data
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    # For storing Channel ID
    if user_data.get('awaiting_channel_id'):
        if text.startswith('-100'):
            success = store_channel_id(user_id, text)
            if success:
                update.message.reply_text(f"🗂️Index Channel {text} saved successfully. From now I will index every file you send to this chat.")
            else:
                update.message.reply_text(f"⚠️The Chat id {text} is already configured by another user. So you cannot add that. If you think this was a mistake please contact the bot owner.")
        else:
            update.message.reply_text("❌Please try again! Provide a valid chat ID starting with -100.")
        user_data['awaiting_channel_id'] = False  # Reset the flag

    # For storing Group ID
    elif user_data.get('awaiting_group_id'):
        if text.startswith('-100'):
            success = store_group_id(user_id, text)
            if success:
                update.message.reply_text(f"👂Listening Group {text} saved successfully. From now on, I'll listen to messages sent to this group.")
            else:
                update.message.reply_text(f"⚠️The Chat id {text} is already configured by another user. So you cannot add that. If you think this was a mistake please the contact bot owner.")
        else:
            update.message.reply_text("❌Please try again! Provide a valid group ID starting with -100.")
        user_data['awaiting_group_id'] = False  # Reset the flag

    # Handling Fsub ID submission
    elif user_data.get('awaiting_fsub_chat_id'):
        if text.startswith('-100'):  # Validate chat ID format
            store_fsub_chat_id(user_id, text)
            update.message.reply_text(f"🔮F-Sub chat setup completed. From now I won't serve users who do not join/subscribe to your {text} chat🫡")
            user_data['awaiting_fsub_chat_id'] = False  # Reset the flag
        else:
            update.message.reply_text("❌Please try again! Provide a valid chat ID starting with -100.")
            user_data['awaiting_fsub_chat_id'] = False  # Reset the flag
    else:
        pass  # Implement any general text handling if necessary

def store_channel_id(user_id: int, channel_id: str):
    """Store each new channel ID in a separate document with safety check."""
    collection = db["Indexed_Channels"]
    # Check if this channel_id is already configured by another user
    exists = collection.find_one({"channel_id": channel_id})
    if exists and exists["user_id"] != user_id:
        # If exists and user_id is different, do not store/update and inform the user
        logger.info(f"🔄 Channel ID {channel_id} is already configured by another user. Stopped duplicating")
        return False
    elif not exists:
        # If not exists, insert new document
        collection.insert_one({"user_id": user_id, "channel_id": channel_id})
        logger.info(f"📡 New indexed channel set: {channel_id} by user {user_id}")
        return True

def store_group_id(user_id: int, group_id: str):
    """Store each new group ID in a separate document with safety check."""
    collection = db["Listening_Groups"]
    # Check if this group_id is already configured by another user
    exists = collection.find_one({"group_id": group_id})
    if exists and exists["user_id"] != user_id:
        # If exists and user_id is different, do not store/update and inform the user
        logger.info(f"🔄 Group ID {group_id} is already configured by another user. Stopped duplicating")
        return False
    elif not exists:
        # If not exists, insert new document
        collection.insert_one({"user_id": user_id, "group_id": group_id})
        logger.info(f"👥 New listening group set: {group_id} by user {user_id}")
        return True

def store_fsub_chat_id(user_id: int, chat_id: str):
    collection = db["Fsub_Chats"]
    # Check for duplicates before insertion
    exists = collection.find_one({"user_id": user_id, "chat_id": chat_id})
    if not exists:
        collection.insert_one({"user_id": user_id, "chat_id": chat_id})
        logger.info(f"🔔 New Fsub chat set: {chat_id} by user {user_id}")

# Process new file messages to extract and store file metadata
def process_new_file(update: Update, context: CallbackContext) -> None:
    message = update.message if update.message is not None else update.channel_post
    if message is None or message.chat.type != 'channel':
        return  # Exit if no message or if the message is not from a channel

    chat_id = str(message.chat.id)

    # Retrieve the user_id associated with this channel_id
    indexed_channel = db["Indexed_Channels"].find_one({"channel_id": chat_id})
    if indexed_channel is None:
        return  # Exit if the channel is not indexed

    user_id = indexed_channel["user_id"]  # Get the user_id who indexed this channel

    file_info = extract_file_info(message)
    if file_info:
        # Use the retrieved user_id to correctly name the collection
        store_file_info(str(user_id), *file_info)

def is_channel_indexed(chat_id):
    collection = db["Indexed_Channels"]
    return collection.find_one({"channel_id": chat_id}) is not None

def extract_file_info(message):
    file, file_type = None, None
    if message.document:
        file = message.document
        file_type = 'document'
    elif message.photo:
        file = message.photo[-1]
        file_type = 'photo'
    elif message.video:
        file = message.video
        file_type = 'video'
    elif message.audio:
        file = message.audio
        file_type = 'audio'
    elif message.animation:  
        file = message.animation
        file_type = 'gif'
    else:
        return None

    file_id = file.file_id
    file_name = getattr(file, 'file_name', 'Unknown')
    file_size = getattr(file, 'file_size', 0)
    mime_type = getattr(file, 'mime_type', 'Unknown')
    caption = message.caption if message.caption else 'No caption'

    return file_id, file_name, file_size, file_type, mime_type, caption

# Store file information in MongoDB
def store_file_info(user_id, file_id, file_name, file_size, file_type, mime_type, caption):
    collection_name = f"DS_collection_{user_id}"
    collection = db[collection_name]
    collection.insert_one({
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "file_type": file_type,
        "mime_type": mime_type,
        "caption": caption
    })

# Setup bot handlers
def setup_ds_dispatcher(dispatcher):
    dispatcher.add_handler(CommandHandler("docspotter", docspotter_command))
    dispatcher.add_handler(CallbackQueryHandler(index_files_callback, pattern='^index_files$'))
    dispatcher.add_handler(CallbackQueryHandler(setup_channel_callback, pattern='^setup_channel$'))
    dispatcher.add_handler(CallbackQueryHandler(setup_group_callback, pattern='^setup_group$'))
    dispatcher.add_handler(CallbackQueryHandler(manage_indexers_callback, pattern='^manage_indexers$'))
    dispatcher.add_handler(CallbackQueryHandler(manage_index_channels_callback, pattern='^dsi_manage_index_channels$'))
    dispatcher.add_handler(CallbackQueryHandler(channel_selected_callback, pattern='^dsi_channel_'))
    dispatcher.add_handler(CallbackQueryHandler(delete_channel_callback, pattern='^dsi_delete_channel_'))
    dispatcher.add_handler(CallbackQueryHandler(manage_listening_groups_callback, pattern='^dsi_manage_listening_groups$'))
    dispatcher.add_handler(CallbackQueryHandler(group_selected_callback, pattern='^dsi_group_'))
    dispatcher.add_handler(CallbackQueryHandler(delete_group_callback, pattern='^dsi_delete_group_'))
    dispatcher.add_handler(CallbackQueryHandler(manage_fsub_chats_callback, pattern='^dsi_manage_fsub_chats$'))
    dispatcher.add_handler(CallbackQueryHandler(fsub_selected_callback, pattern='^dsi_fsub_'))
    dispatcher.add_handler(CallbackQueryHandler(delete_fsub_callback, pattern='^dsi_delete_fsub_'))
    dispatcher.add_handler(CallbackQueryHandler(setup_fsub_callback, pattern='^setup_fsub$'))
    dispatcher.add_handler(CallbackQueryHandler(manage_indexers_callback, pattern='^dsi_back_to_indexers$'))
    dispatcher.add_handler(CallbackQueryHandler(back_to_main_callback, pattern='^back_to_main$'))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, handle_text), group=2)
    dispatcher.add_handler(MessageHandler(Filters.document, process_new_file), group=2)
    dispatcher.add_handler(MessageHandler(Filters.photo, process_new_file), group=2)
    dispatcher.add_handler(MessageHandler(Filters.video, process_new_file), group=2)
    dispatcher.add_handler(MessageHandler(Filters.audio, process_new_file), group=2)
    dispatcher.add_handler(MessageHandler(Filters.animation, process_new_file), group=2)
