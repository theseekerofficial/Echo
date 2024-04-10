import os
import logging
from bson import ObjectId
from pymongo import MongoClient
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from plugins.clonegram.clonegram_executor import register_cg_executor_handlers
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, Filters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["Echo_Clonegram"]

def clonegram_command(update: Update, context: CallbackContext) -> None:
    clonegram_plugin_enabled_str = get_env_var_from_db('CLONEGRAM_PLUGIN')
    clonegram_plugin_enabled = clonegram_plugin_enabled_str.lower() == 'true' if clonegram_plugin_enabled_str else False

    keyboard = [
        [InlineKeyboardButton("Set up Clonegram Task", callback_data='setup_clonegram_task')],
        [InlineKeyboardButton("Delete a Clonegram Task", callback_data='delete_clonegram_task')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if clonegram_plugin_enabled:
        text = 'Choose a method to configure Clonegram:'
    else:
        text = "Clonegram Plugin Disabled by the person who deployed this Echo Variant 💔"

    if update.message:
        update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)

def setup_clonegram_task(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data['setup_step'] = 'source'
    query.edit_message_text(text="Okay, follow this:\n\n1) Add me to your source chat (Group or Channel)\n\n2) Now send me that source chat id\n\nTip:\nAdmin Role is required for channels. But for groups, it's not necessary if the bot's 'Group Privacy' is disabled in @BotFather. Contect the deployed person to know about that")

def save_chat_id(update: Update, context: CallbackContext) -> None:
    setup_step = context.user_data.get('setup_step')
    
    if setup_step in ['source', 'destination']:
        chat_id = update.message.text.strip()
        if chat_id.startswith('-100'):
            if setup_step == 'source':
                context.user_data['source_chat_id'] = chat_id
                context.user_data['setup_step'] = 'destination'
                update.message.reply_text("Okay, follow this:\n\n1) Add me to your destination chat (Group or Channel) and make me a admin\n\n2) Now send me that destination chat id")
            elif setup_step == 'destination':
                context.user_data['destination_chat_id'] = chat_id
                # Move to the next step - choosing clone type
                context.user_data['setup_step'] = 'clone_type'
                keyboard = [
                    [InlineKeyboardButton("Forward Messages", callback_data='forward_messages')],
                    [InlineKeyboardButton("Clone Messages", callback_data='clone_messages')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("How do you want to process this clone task?", reply_markup=reply_markup)
        else:
            update.message.reply_text("Invalid Chat ID. Please make sure the Chat ID starts with '-100'.")
    else:
        return

def handle_clone_type_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data['clone_type'] = 'forward' if query.data == 'forward_messages' else 'clone'
    # Prepare message type selection buttons
    message_types = ["Text", "Photos", "Videos", "Documents", "Audios", "Stickers"]
    keyboard = [[InlineKeyboardButton(msg_type, callback_data=msg_type.lower()) for msg_type in message_types[i:i+2]] for i in range(0, len(message_types), 2)]
    keyboard.append([InlineKeyboardButton("Done Selecting", callback_data='done_selecting')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("What type of messages do you want to clone?", reply_markup=reply_markup)
    context.user_data['message_types'] = {msg_type.lower(): False for msg_type in message_types}  

def handle_message_type_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    msg_type = query.data

    if msg_type == 'done_selecting':
        if not any(context.user_data['message_types'].values()):
            query.answer("You need to select at least one media type before clicking 'Done Selecting'", show_alert=True)
            return  
        
        finalize_selection(update, context)
        return

    # Toggle selection for the media type
    context.user_data['message_types'][msg_type] = not context.user_data['message_types'][msg_type]

    # Update the list of media types with the current selections
    message_types = ["text", "photos", "videos", "documents", "audios", "stickers"]
    keyboard = []

    for i in range(0, len(message_types), 2):
        row = [InlineKeyboardButton(f"{message_types[j].capitalize()} {'✅' if context.user_data['message_types'][message_types[j]] else ''}",
                                    callback_data=message_types[j]) for j in range(i, min(i + 2, len(message_types)))]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Done Selecting", callback_data='done_selecting')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("What type of messages do you want to clone/forward from source chat?", reply_markup=reply_markup)

def finalize_selection(update: Update, context: CallbackContext):
    logger.info(f"✅ User {update.callback_query.from_user.id} finalized their selections.")
    query = update.callback_query
    selections = context.user_data['message_types']
    user_id = query.from_user.id
    source_chat_id = context.user_data.get('source_chat_id')
    destination_chat_id = context.user_data.get('destination_chat_id')
    clone_type = context.user_data.get('clone_type')
    document = {
        'source_chat_id': source_chat_id,
        'destination_chat_id': destination_chat_id,
        'user_id': user_id,
        'clone_type': clone_type,
        **{f"allow_{k}": str(v).lower() for k, v in selections.items()}  
    }
    db["Clonegram_Tasks"].insert_one(document)
    query.edit_message_text("Your Clonegram Task has been set up successfully.")
    context.user_data.clear()  

def delete_clonegram_task(update: Update, context: CallbackContext, check_remaining=False) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    tasks = list(db["Clonegram_Tasks"].find({"user_id": user_id}))

    if not tasks:
        if check_remaining:
            keyboard = [
                [InlineKeyboardButton("Set up Clonegram Task", callback_data='setup_clonegram_task')],
                [InlineKeyboardButton("Delete a Clonegram Task", callback_data='delete_clonegram_task')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                query.edit_message_text(text='Choose a method to configure Clonegram:', reply_markup=reply_markup)
            else:
                chat_id = update.effective_chat.id if update.effective_chat else user_id
                context.bot.send_message(chat_id=chat_id, text='Choose a method to configure Clonegram:', reply_markup=reply_markup)
        else:
            query.answer("You do not have any Clonegram Tasks. Create one!", show_alert=True)
        return

    keyboard = []
    for task in tasks:
        source_chat_name = get_chat_name(context.bot, task['source_chat_id'])
        destination_chat_name = get_chat_name(context.bot, task['destination_chat_id'])
        button_text = f"{source_chat_name} to {destination_chat_name}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"clonegram_delete_{task['_id']}")])

    keyboard.append([InlineKeyboardButton("Back", callback_data=f"clonegram_back_to_main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Choose a task to delete:", reply_markup=reply_markup)

def get_chat_name(bot, chat_id):
    try:
        chat = bot.get_chat(chat_id)
        return chat.title or chat.username
    except Exception as e:
        logger.error(f"Failed to fetch chat name for {chat_id}: {e}")
        return str(chat_id)

def confirm_task_deletion(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    task_id = query.data.split("_")[-1]
    logger.info(f"Attempting to delete task with ID: {task_id}")

    query.answer()  

    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"clonegram_confirm_delete_{task_id}")],
        [InlineKeyboardButton("No", callback_data="delete_clonegram_task")]  
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        query.edit_message_text(text="Do you want to delete this Clonegram task?", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to edit message for task deletion confirmation: {e}")


def execute_task_deletion(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    task_id_str = query.data.split("_")[-1] 
    task_id = ObjectId(task_id_str) 
    db["Clonegram_Tasks"].delete_one({"_id": task_id})
    query.answer("Clonegram task deleted successfully.", show_alert=True)
    logger.info(f"🗑️ Clonegram Task {task_id} deleted from db")
    delete_clonegram_task(update, context, check_remaining=True)

def cancel_task_deletion(update: Update, context: CallbackContext) -> None:
    delete_clonegram_task(update, context)  

def register_clonegram_handlers(dp):    
    dp.add_handler(token_system.token_filter(CommandHandler('clonegram', clonegram_command)))
    dp.add_handler(CallbackQueryHandler(setup_clonegram_task, pattern='^setup_clonegram_task$'))
    dp.add_handler(MessageHandler((Filters.text & ~Filters.command) & (Filters.chat_type.private | Filters.chat_type.groups), save_chat_id), group=8)
    dp.add_handler(CallbackQueryHandler(handle_clone_type_selection, pattern='^(forward_messages|clone_messages)$'))
    dp.add_handler(CallbackQueryHandler(handle_message_type_selection, pattern='^(text|photos|videos|documents|audios|stickers|done_selecting)$'))

    dp.add_handler(CallbackQueryHandler(delete_clonegram_task, pattern='^delete_clonegram_task$'))
    dp.add_handler(CallbackQueryHandler(confirm_task_deletion, pattern='^clonegram_delete_[\w\d]+$'))
    dp.add_handler(CallbackQueryHandler(execute_task_deletion, pattern='^clonegram_confirm_delete_[\w\d]+$'))
    dp.add_handler(CallbackQueryHandler(cancel_task_deletion, pattern='^delete_clonegram_task$'))
    dp.add_handler(CallbackQueryHandler(clonegram_command, pattern='^clonegram_back_to_main_menu$'))
    
    register_cg_executor_handlers(dp)
