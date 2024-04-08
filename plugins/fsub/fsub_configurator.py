# plugins/fsub/fsub_configurator.py
import os
import re
import logging
from pymongo import MongoClient
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from plugins.fsub.fsub_executor import check_membership_and_restrict, handle_try_now
from telegram.ext import CallbackContext, MessageHandler, Filters, CallbackQueryHandler, CommandHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

client = MongoClient(MONGODB_URI)
db = client['Echo']

def start_fsub(update: Update, context: CallbackContext) -> None:
    f_sub_plugin_enabled_str = get_env_var_from_db('F_SUB_PLUGIN')
    f_sub_plugin_enabled = f_sub_plugin_enabled_str.lower() == 'true' if f_sub_plugin_enabled_str else False

    if f_sub_plugin_enabled:
        keyboard = [
            [InlineKeyboardButton("Setup F-Sub Task", callback_data="e_fsub_setup")],
            [InlineKeyboardButton("Delete F-Sub Task(s)", callback_data="e_fsub_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            query = update.callback_query
            query.edit_message_text(text='F-Sub Menu', reply_markup=reply_markup)
        else:
            update.message.reply_text('F-Sub Menu', reply_markup=reply_markup)
    else:
        update.message.reply_text("F-Sub Plugin Disabled by the person who deployed this Echo Variant 💔")

def fsub_setup_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="♻️ Now, send your Group ID.\n\n💥 Tip: This is the chat ID that the bot checks incoming messages from users.\n\n🔴 Chat ID should need to start as '-100'\n🔴 Only Group chat ids acceptable\n🔴 Bot Must Be Admin ⚠️")
    context.user_data['fsub_setup_step'] = 'awaiting_monitoring_chat_id'
    context.user_data['fsub_setup_message_id'] = query.message.message_id  
    
def fsub_collect_chat_id(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    message_id = context.user_data.get('fsub_setup_message_id')
    message_text = update.message.text.strip()
    step = context.user_data.get('fsub_setup_step')

    def bot_is_admin(provided_chat_id):
        try:
            member = context.bot.get_chat_member(chat_id=provided_chat_id, user_id=context.bot.id)
            return member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"🚫 Error checking admin status: {str(e)}")
            return False

    def validate_chat_ids(chat_ids):
        chat_ids_list = chat_ids.split(',')
        return all(re.match(r"^-100\d+$", chat_id.strip()) and bot_is_admin(chat_id.strip()) for chat_id in chat_ids_list)

    if step == 'awaiting_monitoring_chat_id':
        if re.match(r"^-100\d+$", message_text) and bot_is_admin(message_text):
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"🚫 Error deleting message: {str(e)}")

            if db['Fsub_Configs'].find_one({'monitoring_chat_id': message_text}):
                context.bot.send_message(chat_id=chat_id, text="🚫 This monitoring chat ID is already assigned for a task. Task setup cancelled.\n\n💡If you are the task owner delete F-Sub task and add new one")
                del context.user_data['fsub_setup_step']
                del context.user_data['fsub_setup_message_id']
                return

            context.user_data['fsub_monitoring_chat_id'] = message_text
            context.user_data['fsub_setup_step'] = 'awaiting_checking_chat_id'
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text="♻️ Now, send the chat IDs your users need to subscribe to, separated by commas.\n\nE.g. <code>-100123456789,-100987654321,-100918273645</code>\n\n💥 Tip: These are the chat IDs where the bot checks if the user is a member of specific chats.\n\n🔴 Chat IDs should start with '-100'\n🔴 Both Channel and Group IDs acceptable\n🔴 Bot Must Be Admin ⚠️", parse_mode=ParseMode.HTML)
        else:
            context.bot.send_message(chat_id=chat_id, reply_to_message_id=message_id,
                                      text="⚠️ Bot is not an admin in the provided chat or the chat ID is incorrect. Please add the bot as an admin and ensure the Chat ID starts with '-100'.")

    elif step == 'awaiting_checking_chat_id':
        if validate_chat_ids(message_text):  
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"🚫 Error deleting message: {str(e)}")

            user_id = update.message.from_user.id
            monitoring_chat_id = context.user_data['fsub_monitoring_chat_id']

            db['Fsub_Configs'].insert_one({
                'user_id': user_id,
                'monitoring_chat_id': monitoring_chat_id,
                'checking_chat_ids': message_text  
            })
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ F-Sub Task Setup Success!\n\n💥 Tip: Make sure to keep the bot as admin in all specified chats for uninterrupted functioning.")
            logger.info(f"New F-Sub Task Setup by [{user_id}] 🚀")
            del context.user_data['fsub_setup_step']
            del context.user_data['fsub_setup_message_id']
        else:
            context.bot.send_message(chat_id=chat_id, reply_to_message_id=message_id,
                                      text="⚠️ One or more provided Chat IDs are incorrect or the bot is not an admin. Please ensure all Chat IDs start with '-100' and the bot is added as an admin.")

def delete_fsub_task_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    tasks = db['Fsub_Configs'].find({'user_id': user_id})
    
    keyboard = []
    for task in tasks:
        chat_name = get_chat_name(task['monitoring_chat_id'], context)
        button_text = chat_name or task['monitoring_chat_id']
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"e_fsub_select_{task['monitoring_chat_id']}")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="e_fsub_back")])

    if not keyboard:
        keyboard = [[InlineKeyboardButton("Back", callback_data="e_fsub_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="🚫 No tasks found for you. Create one!", reply_markup=reply_markup)
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Select a task to delete:", reply_markup=reply_markup)

def confirm_delete_fsub_task(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    monitoring_chat_id = query.data.split('_')[-1]
    task = db['Fsub_Configs'].find_one({'monitoring_chat_id': monitoring_chat_id})
    
    monitoring_chat_name = get_chat_name(task['monitoring_chat_id'], context) or task['monitoring_chat_id']

    checking_chat_ids = task['checking_chat_ids'].split(',')
    checking_chat_names = []
    for chat_id in checking_chat_ids:
        chat_name = get_chat_name(chat_id.strip(), context) or chat_id.strip()
        checking_chat_names.append(chat_name)

    checking_chats_display = ', '.join(checking_chat_names)

    message_text = f"♻️Want to Delete this task?\n\n<code>🌀 Monitoring Chat: {monitoring_chat_name}\n🌀 Checking Chat(s): {checking_chats_display}</code>"
    
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"e_fsub_confirm_delete_{task['monitoring_chat_id']}")],
        [InlineKeyboardButton("No", callback_data="e_fsub_delete_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def execute_delete_fsub_task(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    monitoring_chat_id = query.data.split('_')[-1]
    
    chat_name_or_id = get_chat_name(monitoring_chat_id, context) or monitoring_chat_id
    
    db['Fsub_Configs'].delete_one({'monitoring_chat_id': monitoring_chat_id})
    
    user_id = query.from_user.id
    remaining_tasks = db['Fsub_Configs'].count_documents({'user_id': user_id})

    query.answer(f"F-Sub Task deleted. <<{chat_name_or_id}>> ✅", show_alert=True)
    logger.info(f"F-Sub Task <<{chat_name_or_id}>> deleted by [{user_id}] 🚀")
    
    if remaining_tasks > 0:
        delete_fsub_task_menu(update, context)
    else:
        start_fsub(update, context)

def get_chat_name(chat_id, context):
    try:
        chat = context.bot.get_chat(chat_id)
        return chat.title
    except Exception as e:
        logger.warning(f"⚠️ Warning: Error getting chat name for {chat_id}: {str(e)}")
        return None

def register_fsub_handlers(dp):
    dp.add_handler(token_system.token_filter(CommandHandler("fsub", start_fsub)))
    dp.add_handler(CallbackQueryHandler(fsub_setup_callback, pattern='^e_fsub_setup$'))
    dp.add_handler(CallbackQueryHandler(delete_fsub_task_menu, pattern='^e_fsub_delete$'))
    dp.add_handler(CallbackQueryHandler(confirm_delete_fsub_task, pattern='^e_fsub_select_'))
    dp.add_handler(CallbackQueryHandler(start_fsub, pattern='^e_fsub_back$'))
    dp.add_handler(CallbackQueryHandler(execute_delete_fsub_task, pattern='^e_fsub_confirm_delete_'))
    dp.add_handler(CallbackQueryHandler(delete_fsub_task_menu, pattern='^e_fsub_delete_cancel$'))
    dp.add_handler(CallbackQueryHandler(handle_try_now, pattern='^try_now_'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, fsub_collect_chat_id, pass_user_data=True), group=11)
    dp.add_handler(MessageHandler(Filters.chat_type.groups, check_membership_and_restrict), group=12)
