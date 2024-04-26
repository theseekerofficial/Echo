# plugins/fileflex/fileflex.py
import os
import logging
from pymongo import MongoClient
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from plugins.fileflex.fileflex_chat_job_executor import fileflex_chat_job_executor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, Filters, CommandHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client.Echo_FileFlex

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

custom_caption_instruction_text = """<b>🖊️ Step 1: Custom Caption</b>
<i>Please type the caption you would like to use for your files. You can use special placeholders:</i>

- <code>{caption}</code> to include the original caption (if any).
- <code>{file_name}</code> to include the original file name.
- <code>{file_type}</code> for the type of file (e.g., Photo, Video, Document).
- <code>{file_size}</code> for the size of the file.
- <code>{link}</code> to add a hyperlink. Use "-" to separate Hyperlink Text and Link
    ~ Usage: <code>{link}</code><b>Text - Link</b><code>{link}</code>

<u>HTML Handler Support</u>

- FileFlex Plugin support all telegram support HTML handlers <code>(&lt;b&gt, &lt;i&gt, &lt;u&gt, &lt;code&gt)</code>
- Remember to close every HTML handler you open. [<code>&lt;/b&gt for &lt;b&gt | &lt;/i&gt for &lt;i&gt | &lt;/u&gt for &lt;u&gt | &lt;/code&gt for &lt;code&gt</code>]
    ~ Usage: To bold a text, <code>&lt;b&gt</code><b>Bold Text</b><code>&lt;/b&gt</code>

For example:
<code>{caption}</code>
<code>&lt;b&gt{file_name}&lt;/b&gt</code>
<code>&lt;i&gt</code><i>Your Custom Text Here</i><code>&lt;/i&gt</code>
<b>File Type:</b> <code>{file_type}</code>
<b>Size:</b> <code>{file_size}</code>
<code>{link}Click Here! - https://example.com{link}</code>

<i>Once you've sent the caption, you'll be asked to provide URL buttons in the next step.</i>

🛑 <b>Send as </b><code>skip</code> <b>to skip setup a caption</b>

⛔ <b>Type /cancel to stop the process</b>"""

custom_buttons_instruction_text = """<b>🔗 Step 2: URL Buttons</b>
<i>Now, send the buttons for your file(s). Use the ' - ' to separate button text from the URL, and ' | ' to place buttons side by side. To start a new line of buttons, Type in a new line.</i>

For example:
<code>Website - https://example.com | Help - https://example.com/help</code>
<code>Contact - https://example.com/contact</code>

<b>This will provide a 3 Buttons format. (Website & Help in 1st line, Contact in 2nd line)</b>

<i>Once you've provided the url button list, send your files in the next step.</i>

🛑 <b>Send as </b><code>skip</code> <b>to skip setup URL buttons</b>

⛔ <b>Type /cancel to stop the process</b>"""

def fileflex_menu(update: Update, context: CallbackContext):
    fileflex_enabled_str = get_env_var_from_db('FILEFLEX_PLUGIN')
    fileflex_enabled = fileflex_enabled_str.lower() == 'true' if fileflex_enabled_str else False

    if fileflex_enabled:
        if update.effective_chat.type != 'private':
            update.message.reply_text("Please use this feature in PM. This effort to avoid spamming in groups.")
            return
        
        keyboard = [
            [InlineKeyboardButton("Real-Time FileFlex", callback_data="fileflex_rt")],
            [InlineKeyboardButton("Add/Edit Template", callback_data="fileflex_global_template"), InlineKeyboardButton("Delete Template", callback_data="fileflex_delete_template")],
            [InlineKeyboardButton("FileFlex Chat Job", callback_data="fileflex_chat_job"), InlineKeyboardButton("Delete Chat Job(s)", callback_data="fileflex_delete_chat_job")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
        if update.callback_query:
            context.user_data.clear()
            query = update.callback_query
            query.edit_message_text(text='FileFlex Main Menu', reply_markup=reply_markup)
        else:
            update.message.reply_text('FileFlex Main Menu', reply_markup=reply_markup)
    else:
        update.message.reply_text("FileFlex Plugin Disabled by the person who deployed this Echo Variant 💔")

def real_time_fileflex(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("Instant Flex", callback_data="fileflex_instant"), InlineKeyboardButton("Pre-Config Flex", callback_data="fileflex_preconfig")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data="fileflex_back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Select a FileFlex mode", reply_markup=reply_markup)

def handle_global_template(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back 🔙", callback_data="fileflex_back_to_main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['fileflex_stage'] = 'global_template_caption'
    gt_msg = query.edit_message_text(text=custom_caption_instruction_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['last_message_id'] = gt_msg.message_id

def instant_fileflex(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back 🔙", callback_data="fileflex_rt")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = query.edit_message_text(text=custom_caption_instruction_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['last_message_id'] = msg.message_id
    context.user_data['fileflex_stage'] = 'caption'

def handle_user_response(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    
    if 'fileflex_stage' not in context.user_data:
        return  
    
    if context.user_data['fileflex_stage'] == 'caption':
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete user message: {e}")
        context.user_data['fileflex_caption'] = user_input
        try:
            need_to_edit_msg = context.user_data['last_message_id']
            msg = context.bot.edit_message_text(text=custom_buttons_instruction_text, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg, chat_id=update.effective_chat.id)
            context.user_data['last_message_id'] = msg.message_id
        except Exception as e:
            msg = update.message.reply_text(text=custom_buttons_instruction_text, parse_mode=ParseMode.HTML)
            context.user_data['last_message_id'] = msg.message_id
        context.user_data['fileflex_stage'] = 'url_buttons'

    elif context.user_data['fileflex_stage'] == 'url_buttons':
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete user message: {e}")
            
        button_lines = user_input.strip().split('\n')
        try:
            keyboard_layout = []
            for line in button_lines:
                buttons = line.split('|')
                row = [InlineKeyboardButton(text=btn.split(" - ")[0].strip(), url=btn.split(" - ")[1].strip()) for btn in buttons if " - " in btn]
                keyboard_layout.append(row)
            context.user_data['fileflex_buttons'] = keyboard_layout
            try:
                need_to_edit_msg = context.user_data['last_message_id']
                done_button = [[InlineKeyboardButton("Done!", callback_data="fileflex_done")]]
                done_markup = InlineKeyboardMarkup(done_button)
                msg = context.bot.edit_message_text("""<b>📁 Step 3: Send Your Files</b>
<i>Send the files you want to share. You can send multiple files one after the other.</i>
<i>Supported file types: <b>Documents, Videos, Images, Audios</b></i>

<i>Once you've sent all your files, click the 'Done!' button to process them.</i>

⛔ Type /cancel to stop the process""", reply_markup=done_markup, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg, chat_id=update.effective_chat.id)
            except Exception as e:
                done_button = [[InlineKeyboardButton("Done!", callback_data="fileflex_done")]]
                done_markup = InlineKeyboardMarkup(done_button)
                msg = update.message.reply_text("""<b>📁 Step 3: Send Your Files</b>
<i>Send the files you want to share. You can send multiple files one after the other.</i>
<i>Supported file types: <b>Documents, Videos, Images, Audios</b></i>

<i>Once you've sent all your files, click the 'Done!' button to process them.</i>

⛔ Type /cancel to stop the process""", reply_markup=done_markup, parse_mode=ParseMode.HTML)
                context.user_data['last_message_id'] = msg.message_id
            context.user_data['fileflex_stage'] = 'collect_files'
        except IndexError:
            update.message.reply_text("Incorrect format. Please send again using the correct format: Text1 - URL1 | Text2 - URL2. Use new lines to separate button rows.\n\n⛔ Type /cancel to stop the process")

    elif context.user_data['fileflex_stage'] == 'global_template_caption':
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete user message: {e}")
        try:
            need_to_edit_msg = context.user_data['last_message_id']
            context.user_data['global_template_caption'] = user_input
            gt_msg = context.bot.edit_message_text(text=custom_buttons_instruction_text, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg, chat_id=update.effective_chat.id)
        except Exception as e:
            context.user_data['global_template_caption'] = user_input
            gt_msg = update.message.reply_text(text=custom_buttons_instruction_text, parse_mode=ParseMode.HTML)
        context.user_data['last_message_id'] = gt_msg.message_id
        context.user_data['fileflex_stage'] = 'global_template_buttons'
    
    elif context.user_data['fileflex_stage'] == 'global_template_buttons':
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete user message: {e}")
        try:
            need_to_edit_msg = context.user_data['last_message_id']
            context.user_data['global_template_buttons'] = user_input
            context.bot.edit_message_text(text="Your Global FileFlex template is Ready ✅", message_id=need_to_edit_msg, chat_id=update.effective_chat.id)
        except Exception as e:
            context.user_data['global_template_buttons'] = user_input
            update.message.reply_text("Your Global FileFlex template is Ready ✅")

        save_global_template_to_mongodb(context.user_data['global_template_caption'], context.user_data['global_template_buttons'], update.effective_user.id)
        context.user_data.clear()

    elif context.user_data['fileflex_stage'] == 'expect_chat_id':
        try:
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete user message: {e}")
            if user_input.startswith("-100"):
                chat_id = int(user_input)
                existing_record = db.FileFlex_Chat_Jobs.find_one({"chat_id": chat_id})
                if existing_record:
                    update.message.reply_text("This chat ID is already set up by a user. Please use a different chat ID.\n\n⛔ Type /cancel to stop the process")
                    return
                    
                try:
                    chat_member = context.bot.get_chat_member(chat_id, context.bot.id)
                    if chat_member.status in ['administrator', 'creator']:
                        db.FileFlex_Chat_Jobs.insert_one({'user_id': update.effective_user.id, 'chat_id': chat_id})
                        need_to_edit_msg = context.user_data['last_message_id']
                        context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=context.user_data.get('last_message_id'),
                            text="Your FileFlex Chat Job created successfully! ✅\n\n♦️ Note: Chat Jobs using your Global FileFlex Template for files!"
                        )
                        context.user_data.clear()
                    else:
                        update.message.reply_text("⚠️ I am not an admin in the provided chat. Please add me as an admin and try again.\n\n⛔ Type /cancel to stop the process")
                except Exception as e:
                    update.message.reply_text(f"Failed to verify bot status in the chat: {str(e)}. Make sure I'm added to the chat and try again.\n\n⛔ Type /cancel to stop the process")
            else:
                update.message.reply_text("⚠️ Invalid chat ID. Please ensure it starts with -100 and try again.\n\n⛔ Type /cancel to stop the process")
        except ValueError:
            update.message.reply_text("⚠️ Please send a valid chat ID that starts with -100.\n\n⛔ Type /cancel to stop the process")

def process_caption(template, message, context):
    file = None
    file_name = ''
    file_type = ''
    file_size = 0

    if message.document:
        file = message.document
        file_name = message.document.file_name
        file_type = file.mime_type.split('/')[-1].upper()
        file_size = file.file_size
    elif message.photo and message.photo[-1]:
        file = message.photo[-1]
        file_type = 'PHOTO'
    elif message.video:
        file = message.video
        file_name = message.video.file_name
        file_type = file.mime_type.split('/')[-1].upper()
        file_size = file.file_size
    elif message.audio:
        file = message.audio
        file_name = message.audio.file_name
        file_type = file.mime_type.split('/')[-1].upper()
        file_size = file.file_size

    if file_size < 1024:
        file_size_str = f"{file_size} bytes"
    elif file_size < 1024 * 1024:
        file_size_str = f"{file_size / 1024:.2f} KB"
    elif file_size < 1024 * 1024 * 1024:
        file_size_str = f"{file_size / 1024 / 1024:.2f} MB"
    else:
        file_size_str = f"{file_size / 1024 / 1024 / 1024:.2f} GB"

    original_caption = message.caption or ''
    template = template.replace("{caption}", original_caption)
    template = template.replace("{file_name}", file_name)
    template = template.replace("{file_type}", file_type)
    template = template.replace("{file_size}", file_size_str)

    while "{link}" in template:
        start_index = template.find("{link}") + 6
        end_index = template.find("{link}", start_index)
        if end_index == -1:
            break
        link_text, link_url = template[start_index:end_index].split(" - ")
        template = template[:start_index - 6] + f'<a href="{link_url.strip()}">{link_text.strip()}</a>' + template[end_index + 6:]

    return template

def collect_files(update: Update, context: CallbackContext):
    if 'fileflex_stage' in context.user_data and context.user_data['fileflex_stage'] == 'collect_files':
        file = update.message.document or \
               (update.message.photo[-1] if update.message.photo else None) or \
               (update.message.video if update.message.video else None) or \
               (update.message.audio if update.message.audio else None)

        if file:
            context.user_data.setdefault('fileflex_files', []).append(update.message)
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
        else:
            update.message.reply_text("No valid file detected, please send a document, photo, video, or audio.")


def finalize_file_sending(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    files = context.user_data.get('fileflex_files', [])
    buttons = context.user_data.get('fileflex_buttons', [])
    
    if not files:
        query.edit_message_text("No files were processed because none were sent. Please try again.")
        context.user_data.clear()
        return
    
    reply_markup = InlineKeyboardMarkup(buttons)

    for file_message in files:
        if context.user_data['fileflex_caption'].strip().lower() == "skip":
            processed_caption = ''
        else:
            processed_caption = process_caption(context.user_data['fileflex_caption'], file_message, context)
        
        if file_message.document:
            context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_message.document.file_id,
                caption=processed_caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif file_message.photo:
            context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=file_message.photo[-1].file_id,  
                caption=processed_caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif file_message.video:
            context.bot.send_video(
                chat_id=query.message.chat_id,
                video=file_message.video.file_id,
                caption=processed_caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        elif file_message.audio:
            context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=file_message.audio.file_id,
                caption=processed_caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            continue  
        
    context.user_data.clear()
    query.edit_message_text("All files have been processed. ✅")

def save_global_template_to_mongodb(caption, buttons, user_id):
    db.FileFlex_G_Captions.update_one(
        {"user_id": user_id},
        {"$set": {"caption": caption}},
        upsert=True
    )
    
    db.FileFlex_G_Buttons.update_one(
        {"user_id": user_id},
        {"$set": {"buttons": buttons}},
        upsert=True
    )

def pre_config_fileflex(update: Update, context: CallbackContext):
    query = update.callback_query

    user_id = update.effective_user.id
    caption_record = db.FileFlex_G_Captions.find_one({"user_id": user_id})
    buttons_record = db.FileFlex_G_Buttons.find_one({"user_id": user_id})

    if not caption_record or not buttons_record:
        query.answer("You do not have a Global FileFlex Template. Create one in FileFlex main menu", show_alert=True)
    else:
        query.answer()
        context.user_data['fileflex_caption'] = caption_record['caption']
        inl_url_buttons = buttons_record['buttons']
        button_lines = inl_url_buttons.strip().split('\n')
        try:
            keyboard_layout = []
            for line in button_lines:
                buttons = line.split('|')
                row = [InlineKeyboardButton(text=btn.split(" - ")[0].strip(), url=btn.split(" - ")[1].strip()) for btn in buttons if " - " in btn]
                keyboard_layout.append(row)
            context.user_data['fileflex_buttons'] = keyboard_layout
        except IndexError as e:
            update.message.reply_text(f"Incorrect button list format in your global template. Please review it and add correct template again\n\n Example: Text1 - URL1 | Text2 - URL2. Use new lines to separate button rows.\n\nYour Button Error is {e}")
        done_button = [[InlineKeyboardButton("Done!", callback_data="fileflex_done")]]
        reply_markup = InlineKeyboardMarkup(done_button)
        context.user_data['fileflex_stage'] = 'collect_files'
        query.edit_message_text(text="<b>📁 Step 3: Send Your Files</b>\nSend the files you want to share. Click the 'Done!' button when you are finished.\n\n⛔ Type /cancel to stop the process", parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def handle_fileflex_chat_job(update: Update, context: CallbackContext):
    query = update.callback_query

    user_id = update.effective_user.id
    caption_record = db.FileFlex_G_Captions.find_one({"user_id": user_id})
    buttons_record = db.FileFlex_G_Buttons.find_one({"user_id": user_id})

    if not caption_record or not buttons_record:
        query.answer("You do not have a Global FileFlex Template. Create one in FileFlex main menu first!", show_alert=True)
        return
    
    context.user_data['fileflex_stage'] = 'expect_chat_id'
    keyboard = [[InlineKeyboardButton("🔙 Back 🔙", callback_data="fileflex_back_to_main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    cj_msg = query.edit_message_text(text="🗨️ Send me a chat ID where I am an admin. The chat ID should start with <code>-100</code>.\n\n⛔ Type /cancel to stop the process", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['last_message_id'] = cj_msg.message_id

def handle_delete_chat_jobs(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    jobs = list(db.FileFlex_Chat_Jobs.find({"user_id": user_id}))

    if not jobs:
        query.answer("You do not have any FileFlex Chat Jobs. Create one!", show_alert=True)
        return

    buttons = []
    for job in jobs:
        chat_id = job['chat_id']
        try:
            chat = context.bot.get_chat(chat_id)
            chat_name = chat.title or "Unnamed Chat"
        except:
            chat_name = f"Chat ID {chat_id}"
        buttons.append([InlineKeyboardButton(chat_name, callback_data=f"fileflex_delete_job_{chat_id}")])
        
    buttons.append([InlineKeyboardButton("🔙 Back 🔙", callback_data=f"fileflex_back_to_main_menu")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text("Select a chat job to delete:", reply_markup=reply_markup)

def confirm_delete_job(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    try:
        chat = context.bot.get_chat(chat_id)
        chat_name = chat.title
    except Exception as e:
        chat_name = f"Chat ID {chat_id}"
        logger.error(f"Error getting chat name: {e}")

    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"fileflex_confirm_delete_{chat_id}"), InlineKeyboardButton("No", callback_data="fileflex_back_to_main_menu")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"fileflex_delete_chat_job")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"Do you want to delete this FileFlex chat job?\n\n<i>Selected Chat Job: </i><code>{chat_name}</code> [<code>{chat_id}</code>]", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def delete_job(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[3])
    db.FileFlex_Chat_Jobs.delete_one({"chat_id": chat_id})
    query.answer(f"Chat Job [{chat_id}] deleted successfully ✅")

    jobs = list(db.FileFlex_Chat_Jobs.find({"user_id": query.from_user.id}))
    if jobs:
        handle_delete_chat_jobs(update, context)
    else:
        query.edit_message_text("All chat jobs have been deleted. Returning to main menu...", reply_markup=None)
        fileflex_menu(update, context)

def handle_delete_template(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    caption_record = db.FileFlex_G_Captions.find_one({"user_id": user_id})
    buttons_record = db.FileFlex_G_Buttons.find_one({"user_id": user_id})
    
    if not caption_record and not buttons_record:
        query.answer("No G-Template available for you. Create one first!", show_alert=True)
    else:
        caption_text = caption_record['caption'] if caption_record else "No caption found"
        buttons_text = str(buttons_record['buttons']) if buttons_record else "No buttons set"
        
        confirm_keyboard = [
            [InlineKeyboardButton("Yes", callback_data="fileflex_del_g_temp_yes"),
             InlineKeyboardButton("No", callback_data="fileflex_del_g_temp_no")]
        ]
        reply_markup = InlineKeyboardMarkup(confirm_keyboard)
        query.edit_message_text(
            text=f"<i><b>Your G-Caption:</b></i>\n<code>{caption_text}</code>\n\n<i><b>Your URL Button:</b></i>\n<code>{buttons_text}</code>\n\n<b><i>Do you want to delete this template from database?</i></b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

def confirm_delete_template(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    if "yes" in query.data:
        db.FileFlex_G_Captions.delete_one({"user_id": user_id})
        db.FileFlex_G_Buttons.delete_one({"user_id": user_id})
        query.answer(f"Your Global Template deleted successfully ✅")
    fileflex_menu(update, context)

file_filters = Filters.document | Filters.photo | Filters.video | Filters.audio

def register_fileflex_handlers(dp):
    dp.add_handler(token_system.token_filter(CommandHandler('fileflex', fileflex_menu)))
    dp.add_handler(CallbackQueryHandler(real_time_fileflex, pattern='^fileflex_rt$'))
    dp.add_handler(CallbackQueryHandler(instant_fileflex, pattern='^fileflex_instant$'))
    dp.add_handler(CallbackQueryHandler(finalize_file_sending, pattern='^fileflex_done$'))
    dp.add_handler(CallbackQueryHandler(pre_config_fileflex, pattern='^fileflex_preconfig$'))
    dp.add_handler(CallbackQueryHandler(handle_fileflex_chat_job, pattern='^fileflex_chat_job$'))
    dp.add_handler(CallbackQueryHandler(handle_global_template, pattern='^fileflex_global_template$'))
    dp.add_handler(CallbackQueryHandler(handle_delete_template, pattern='^fileflex_delete_template$'))
    dp.add_handler(CallbackQueryHandler(handle_delete_chat_jobs, pattern='^fileflex_delete_chat_job$'))
    dp.add_handler(CallbackQueryHandler(confirm_delete_template, pattern='^fileflex_del_g_temp_(yes|no)$'))
    dp.add_handler(CallbackQueryHandler(confirm_delete_job, pattern='^fileflex_delete_job_-\\d+$'))
    dp.add_handler(CallbackQueryHandler(delete_job, pattern='^fileflex_confirm_delete_-\\d+$'))
    dp.add_handler(CallbackQueryHandler(fileflex_menu, pattern='^fileflex_back_to_main_menu$'))
    dp.add_handler(MessageHandler(~Filters.command & Filters.text & Filters.chat_type.private, handle_user_response, pass_user_data=True), group=13)
    dp.add_handler(MessageHandler(~Filters.command & file_filters & Filters.chat_type.private, collect_files, pass_user_data=True), group=13)
    dp.add_handler(MessageHandler((Filters.update.message | Filters.update.channel_post) & ~Filters.text, fileflex_chat_job_executor), group=14)
