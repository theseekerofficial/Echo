# modules/codecapsule.py
import os
import sys
import time
import logging
import subprocess
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

current_process = None

os.environ['RUNNING_THROUGH_CODECAPSULE'] = 'true'

def codecapsule_command(update: Update, context: CallbackContext) -> None:
    owner = get_env_var_from_db("OWNER")
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("Run a Supporter Plugin", callback_data="codecapsule_runplugin")],
        [InlineKeyboardButton("Active Supporter Plugin(s)", callback_data="cc_scr_mng_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("CodeCapsule Main Menu 💊", reply_markup=reply_markup)

def codecapsule_button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    owner = get_env_var_from_db("OWNER")

    if query.data == "codecapsule_runplugin":
        if str(user_id) != owner:
            query.answer("You are not allowed to use this feature", show_alert=True)
        else:
            query.answer()
            query.edit_message_text(text="Send an Official Echo Verified Supporting Plugin.\n\n✅Supported Plugins\n♦️<code>TeleFileDex.py</code>\n♦️<code>TeleCloner.py</code>", parse_mode=ParseMode.HTML)
            context.chat_data['expecting_python_file'] = True

def codecapsule_file_handler(update: Update, context: CallbackContext) -> None:
    global current_process
    if context.chat_data.get('expecting_python_file'):
        owner = get_env_var_from_db("OWNER")
        user_id = update.message.from_user.id

        if str(user_id) == owner:
            document = update.message.document
            file_name = document.file_name
            file_config = {
                'TeleFileDex.py': {'line': 152, 'identifier': "k$#jCojZ8siWWEdEy1^lu%2YsmA1cH5y0LG"},
                'TeleCloner.py': {'line': 258, 'identifier': "C@K$y1vRpB@^nT*8wsrK!1hUGpTsf6UdpNN"},
                'SafeSync.py': {'line': 44, 'identifier': "2jyJVUaVOg3!ubY54FV$Iv88zmvblYoMqou"}
            }

            if file_name in file_config:
                file = context.bot.get_file(document.file_id)
                file_path = os.path.join('supporting_plugins', file_name)
                file.download(custom_path=file_path)
                
                config = file_config[file_name]
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        codex_identifier = lines[config['line']].strip()
                    
                    expected_identifier = f'codex_identifier = "{config["identifier"]}"'
                    
                    if codex_identifier == expected_identifier:
                        screen_name = f"echo_plugin_{document.file_unique_id}"
                        context.user_data['s_p_screen_name'] = screen_name
                        command = f"screen -dmS {screen_name} python3 {file_path}"
                        subprocess.run(command, shell=True, check=True)
                        s_plugin_name = file_name
                        logger.info(f"{s_plugin_name} Plugin on the run...")
                        update.message.reply_text(f"""<code>{s_plugin_name}</code> Plugin Initiated in a screen session. Click the button below or go to "Active Supporter Plugin(s)" menu to terminate it.""",
                                                  reply_markup=InlineKeyboardMarkup([
                                                      [InlineKeyboardButton("🚫 Stop 🚫", callback_data=f"s_p_codecapsule_stopplugin_{screen_name}")]
                                                  ]), parse_mode=ParseMode.HTML)
                    else:
                        os.remove(file_path)
                        update.message.reply_text("The identifier in the uploaded file does not match the expected value.")
                except Exception as e:
                    os.remove(file_path)
                    update.message.reply_text(f"An error occurred while verifying the file: {str(e)}")
            else:
                update.message.reply_text(f"The file must be one of the supported types: {', '.join(file_config.keys())}.")
        else:
            update.message.reply_text("You are not authorized to send files.")

        context.chat_data['expecting_python_file'] = False

def stop_plugin_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    owner = get_env_var_from_db("OWNER")

    screen_name = context.user_data['s_p_screen_name']

    if str(user_id) == owner:
        command = f"screen -S {screen_name} -X quit"
        try:
            subprocess.run(command, shell=True, check=True)
            logger.info("Screen Terminated ♦️")
            query.edit_message_text(text="🚫 Supporting plugin screen session has been terminated.")
        except Exception as e:
            query.edit_message_text(text=f"Failed to stop the session: {str(e)}")
    else:
        query.answer("You are not allowed to use this feature.", show_alert=True)

def list_active_plugins(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    owner = get_env_var_from_db("OWNER")
    if str(user_id) != owner:
        query.answer("You are not allowed to use this feature", show_alert=True)
        return

    try:
        result = subprocess.check_output("screen -list | grep 'echo_plugin_'", shell=True).decode('utf-8')
        screens = [line.split()[0] for line in result.strip().split('\n')]
        if screens:
            keyboard = [[InlineKeyboardButton(screen, callback_data=f"cc_scr_mng_{screen}")] for screen in screens]
            query.edit_message_text(text="Ongoing Active Supporter Plugins", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text(text="No active supporter plugins found.")
    except subprocess.CalledProcessError:
        query.edit_message_text(text="No active supporter plugins found.")

def confirm_terminate_plugin(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    screen_name = query.data.split("_")[-1]
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"ccc_scr_mng_terminate_yes_{screen_name}"),
         InlineKeyboardButton("No", callback_data="cc_scr_mng_list")]
    ]
    msg = query.edit_message_text(text=f"Do you want to Terminate this Supporter Plugin: {screen_name}?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['need_to_del_msg_id'] = msg.message_id

def terminate_plugin(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    screen_name = query.data.split("_")[-1]
    full_scr_name = f"echo_plugin_{screen_name}"
    need_to_del_msg = context.user_data['need_to_del_msg_id']
    try:
        subprocess.run(f"screen -S {full_scr_name} -X quit", shell=True, check=True)
        logger.info("Screen Terminated ♦️")
        keyboard = [
            [InlineKeyboardButton("Run a Supporting Plugin", callback_data="codecapsule_runplugin")],
            [InlineKeyboardButton("Active Supporter Plugin(s)", callback_data="cc_scr_mng_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.answer("Supporter Plugin Terminated ✅", show_alert=True)
        context.bot.delete_message(chat_id=user_id, message_id=need_to_del_msg)
        context.bot.send_message(text="CodeCapsule Main Menu 💊", chat_id=user_id, reply_markup=reply_markup)
    except Exception as e:
        query.edit_message_text(text=f"Failed to stop the session: {str(e)}")

def setup_codecapsule_handlers(dp):
    if not os.path.exists('supporting_plugins'):
        os.makedirs('supporting_plugins')
        logger.info("'supporting_plugins' dir created ✅")
    else:
        for file in os.listdir('supporting_plugins'):
            file_path = os.path.join('supporting_plugins', file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        logger.info("'supporting_plugins' Cleanup completed 🧹")

    dp.add_handler(CommandHandler("codecapsule", codecapsule_command))
    dp.add_handler(CallbackQueryHandler(codecapsule_button_handler, pattern="^codecapsule_runplugin$"))
    dp.add_handler(MessageHandler(Filters.document.file_extension("py"), codecapsule_file_handler), group=15)
    dp.add_handler(CallbackQueryHandler(stop_plugin_handler, pattern=r"^s_p_codecapsule_stopplugin.*$"))
    dp.add_handler(CallbackQueryHandler(list_active_plugins, pattern="^cc_scr_mng_list$"))
    dp.add_handler(CallbackQueryHandler(confirm_terminate_plugin, pattern=r"^cc_scr_mng_.*$"))
    dp.add_handler(CallbackQueryHandler(terminate_plugin, pattern="^ccc_scr_mng_terminate_yes_"))
