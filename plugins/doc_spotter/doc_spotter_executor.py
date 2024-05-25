import os
import logging
import requests
from imdb import IMDb
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db
from modules.utilities.url_shortener import get_short_url
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto, ParseMode
from plugins.doc_spotter.doc_spotter_fsub import is_user_member_of_fsub_chats, prompt_to_join_fsub_chats
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler, Updater, CallbackQueryHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["Echo_Doc_Spotter"]
echo_db = client["Echo"]
imdb = IMDb() 

DS_IMDB_ACTIVATE_str = get_env_var_from_db('DS_IMDB_ACTIVATE')
DS_IMDB_ACTIVATE = DS_IMDB_ACTIVATE_str.lower() == 'true' if DS_IMDB_ACTIVATE_str else False

DS_URL_BUTTONS_str = get_env_var_from_db('DS_URL_BUTTONS')
DS_URL_BUTTONS = DS_URL_BUTTONS_str.lower() == 'true' if DS_URL_BUTTONS_str else False

OWNER = int(get_env_var_from_db('OWNER'))
AUTHORIZED_USERS_str = get_env_var_from_db('AUTHORIZED_USERS')  
AUTHORIZED_USERS = [int(user_id.strip()) for user_id in AUTHORIZED_USERS_str.split(',')] if AUTHORIZED_USERS_str else []

PAGE_SIZE = 10
doc_spotter_plugin_enabled = None

def get_doc_spotter_plugin_enabled():
    global doc_spotter_plugin_enabled
    if doc_spotter_plugin_enabled is None:
        doc_spotter_plugin_enabled_str = get_env_var_from_db('DOC_SPOTTER_PLUGIN')
        doc_spotter_plugin_enabled = doc_spotter_plugin_enabled_str.lower() == 'true' if doc_spotter_plugin_enabled_str else False
    return doc_spotter_plugin_enabled

def has_user_started_bot(update, message_sender_user_id):

    user_record = echo_db["user_and_chat_data"].find_one({"user_id": message_sender_user_id})
    return bool(user_record)

def prompt_user_to_start_bot_in_pm(update: Update, context: CallbackContext):
    bot_username = context.bot.get_me().username
    start_bot_url = f"https://t.me/{bot_username}?start=welcome"
    keyboard = [[InlineKeyboardButton("Start Echo ❄️", url=start_bot_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Hmm... Looks like you didn't start me in PM (Private Message). Please go and start me in PM, so we can start your file-seeking journey!💥", reply_markup=reply_markup)

def listen_to_groups(update: Update, context: CallbackContext):
    message_text = update.message.text.lower()
    chat_id = update.message.chat.id
    user_id = find_user_by_group(chat_id)
    message_sender_user_id = update.message.from_user.id
    m_user = update.message.from_user
    info_db_collection = db['Listening_Groups']
    topic_id_exist = info_db_collection.find_one({"group_id": str(chat_id)})
    message_thread_id_to_check = update.message.message_thread_id
    if message_thread_id_to_check is None:
        message_thread_id_to_check = 1
    
    if not db["Listening_Groups"].find_one({"group_id": str(chat_id)}):
        return

    if 'topic_id' in topic_id_exist and int(topic_id_exist['topic_id']) != message_thread_id_to_check:
        return
    
    if not get_doc_spotter_plugin_enabled():
        update.message.reply_text("Doc Spotter Plugin Disabled by the person who deployed this Echo variant💔")
        return
    
    if not has_user_started_bot(update, message_sender_user_id):
        prompt_user_to_start_bot_in_pm(update, context)
        return

    if not is_user_member_of_fsub_chats(message_sender_user_id, chat_id, client, context):
        prompt_to_join_fsub_chats(update, context, client)
        return 
    
    if m_user.username:
        user_mention = f"@{m_user.username}"
    else:
        user_mention = m_user.first_name
    
    if not db["Listening_Groups"].find_one({"group_id": str(chat_id)}):
        return
    
    loading_message_text = f"<code>Hold on </code>{user_mention},<code> searching for </code><i>'{update.message.text.lower()}'</i>..."
    loading_message = update.message.reply_text(loading_message_text, parse_mode=ParseMode.HTML)
    
    if user_id:
        collection_name = f"DS_collection_{user_id}"
        search_text_regex = message_text.replace(" ", "[ ._-]")
        search_criteria = {"file_name": {"$regex": search_text_regex, "$options": "i"}}
        results = list(db[collection_name].find(search_criteria))
        context.user_data['search_criteria'] = search_criteria
        context.user_data['search_results'] = results

        if results:
            if DS_IMDB_ACTIVATE:
                try:
                    movies = imdb.search_movie(message_text)
                    if movies:
                        movie = movies[0]
                        movie_id = movie.movieID
                        movie_details = imdb.get_movie(movie_id)

                        photo_url = movie_details.get('full-size cover url', movie_details.get('cover url', None))

                        if photo_url:
                            title = movie_details.get('title', 'N/A')
                            aka = ", ".join(movie_details.get('akas', ['N/A']))
                            rating = movie_details.get('rating', 'N/A')
                            release_info = f"https://www.imdb.com/title/tt{movie_id}/releaseinfo"
                            genres = ', '.join([f"#{genre.replace(' ', '_')}" for genre in movie_details.get('genres', ['N/A'])])
                            plot = movie_details.get('plot outline', 'Plot not available.')
                            languages = ", ".join(movie_details.get('languages', ['N/A']))
                            country = ", ".join(movie_details.get('countries', ['N/A']))
                            caption = (f"Title✍️: {title}\nAlso Known As🗃️: {aka}\nRating⭐️: {rating}\n"
                                       f"Release Info🚀: {release_info}\nGenre🎭: {genres}\nLanguage🗣️: {languages}\n"
                                       f"Country of Origin🌏: {country}\n\nStory Line📖: {plot}")
                            
                            context.bot.delete_message(chat_id=update.message.chat.id, message_id=loading_message.message_id)
                            
                            display_page_buttons(update, context, results, 0, user_id, imdb_info=caption, photo_url=photo_url)
                        else:
                            raise Exception("No photo URL found.")
                    else:
                        raise Exception("No movies found.")
                except Exception as e:
                    logging.error(f"🚫 Error fetching IMDb data: {e}")
                    context.bot.delete_message(chat_id=update.message.chat.id, message_id=loading_message.message_id)
                    display_page_buttons(update, context, results, 0, user_id)
            else:
                context.bot.delete_message(chat_id=update.message.chat.id, message_id=loading_message.message_id)
                display_page_buttons(update, context, results, 0, user_id)
        else:
            context.bot.delete_message(chat_id=update.message.chat.id, message_id=loading_message.message_id)
            update.message.reply_text("No matching files found.")

def is_subscription_valid(user_id):
    current_date = datetime.now().date()
    user_doc = echo_db["Paid_Users"].find_one({"user_id": user_id})

    if user_doc:
        expire_date_str = user_doc.get("expire_date", "")
        expire_date = datetime.strptime(expire_date_str, "%d-%m-%Y").date()

        if current_date <= expire_date:
            return True  
    return False  

def display_page_buttons(update, context, results, page, user_id, imdb_info=None, photo_url=None, is_pagination=False):
    chat_id = update.effective_chat.id
    message_sender_user_id = update.message.from_user.id
    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    start_index = page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(results))
    info_collection = db['Listening_Groups']
    original_group_id = update.effective_chat.id
    topic_id_exist = info_collection.find_one({"group_id": str(chat_id)})
    if topic_id_exist and 'topic_id' in topic_id_exist:
        topic_id = topic_id_exist['topic_id']
        if topic_id == "1":
            topic_id = None
    else:
        topic_id = None

    bot_username = context.bot.get_me().username
    buttons = []

    if DS_URL_BUTTONS:
        for result in results[start_index:end_index]:
            file_name = result["file_name"]
            file_id = str(result['_id'])
            file_size = format_file_size(result.get("file_size", 0))
            quality = extract_quality(file_name)
            quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
            doc_id = f"{file_id}_{message_sender_user_id}"
            long_url = f"https://t.me/{bot_username}?start=file_{doc_id}_{original_group_id}"
            if message_sender_user_id == OWNER or message_sender_user_id in AUTHORIZED_USERS or is_subscription_valid(message_sender_user_id):
                short_url = long_url 
            else:
                short_url = get_short_url(long_url)            
            file_name_display = f"{quality_and_size} {file_name}"
            buttons.append([InlineKeyboardButton(text=file_name_display, url=short_url)])
    else:
        for result in results[start_index:end_index]:
            file_name = result["file_name"]
            file_size = format_file_size(result.get("file_size", 0))
            quality = extract_quality(file_name)
            quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
            file_name_display = f"{quality_and_size} {file_name}"
            doc_id = f"dse_{result['_id']}_{message_sender_user_id}"  
            buttons.append([InlineKeyboardButton(text=file_name_display, callback_data=doc_id)])

    page_count_button = InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("👈 Prev", callback_data=f"prev_{page - 1}_{user_id}_{message_sender_user_id}"))
    nav_buttons.append(page_count_button)
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next 👉", callback_data=f"next_{page + 1}_{user_id}_{message_sender_user_id}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(buttons)

    if DS_IMDB_ACTIVATE and imdb_info and photo_url:
      if not photo_url:
          photo_path = os.path.join('assets', 'doc_spotter.jpg')
          caption = imdb_info if imdb_info else "Here is what I found in the database:"
          with open(photo_path, 'rb') as photo:
              context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup, message_thread_id=topic_id)
      else:
          if imdb_info and len(imdb_info) > 1024:
              message = context.bot.send_message(chat_id=chat_id, text=imdb_info[:1024] + "... (continued)", message_thread_id=topic_id)
              imdb_message_id = message.message_id
              context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption="Here is what I found in the database:", reply_markup=reply_markup, reply_to_message_id=imdb_message_id, message_thread_id=topic_id)
          else:
              context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=imdb_info, reply_markup=reply_markup, message_thread_id=topic_id)
    else:
        photo_path = os.path.join('assets', 'doc_spotter.jpg')
        caption = "Here is what I found in the database:"
        with open(photo_path, 'rb') as photo:
            context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup, message_thread_id=topic_id)
    logging.info(f"✅ User {update.effective_user.id} received IMDB info and poster for '{update.message.text}' in chat {update.message.chat.id}")

def get_user_buttons(user_id):
    user_buttons = db["URL_Buttons_Sets"].find_one({"user_id": user_id})
    if not user_buttons:
        return None  

    buttons_raw = user_buttons["buttons_raw"]
    buttons_list = []
    button_lines = buttons_raw.split('\n')
    for line in button_lines:
        button_row = [InlineKeyboardButton(text=part.split(' - ')[0].strip(), url=part.split(' - ')[1].strip())
                      for part in line.split('|')]
        buttons_list.append(button_row)
    return buttons_list

def send_file_to_user(chat_id, doc_id, original_group_id, context):
    user_id = find_user_by_group(original_group_id)  
    
    if not user_id:
        logging.error(f"Could not find user ID for group ID: {original_group_id}")
        context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your request. Contact the Doc Spotter Setuped User to resolve this issue")
        return
    
    collection_name = f"DS_collection_{user_id}"
    collection = db[collection_name]

    try:
        file_document = collection.find_one({"_id": ObjectId(doc_id)})

        if file_document:
            if file_document.get('proceed_using_method_2'):
                transfer_temp_chat_id = file_document.get('transfer_temp_chat_id')
                if transfer_temp_chat_id:
                    source_chat_id = file_document.get('chat_id')
                    message_id = file_document.get('msg_id')
                    
                    try:
                        forwarded_message = context.bot.forward_message(
                            chat_id=int(transfer_temp_chat_id),
                            from_chat_id=int(source_chat_id),
                            message_id=int(message_id)
                        )
                    except Exception as e:
                        context.bot.send_message(chat_id=chat_id, text=f"Requested file is being deleted or not available in source chat | Error: {e}")
                        collection.delete_one({'_id': ObjectId(doc_id)})
                        return
                        
                    forwarded_file_id = get_file_id_from_forwarded_message(forwarded_message)
                    try:
                        context.bot.delete_message(chat_id=transfer_temp_chat_id, message_id=forwarded_message.message_id)
                    except:
                        logger.warning(f"Faild to delete temp file in [{transfer_temp_chat_id}] check is the bot have correct permission(s)")
                    if forwarded_file_id:
                        send_forwarded_file(chat_id, forwarded_file_id, file_document, context, user_id)
                        return
            else:
                file_id = file_document.get('file_id')
                file_name = file_document.get('file_name')
                file_type = file_document.get('file_type')
                caption = file_document.get('caption', '')
                custom_buttons = get_user_buttons(user_id)

                reply_markup = InlineKeyboardMarkup(custom_buttons) if custom_buttons else None
                
                if file_type == 'photo':
                    context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, reply_markup=reply_markup)
                elif file_type == 'video':
                    context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption, reply_markup=reply_markup)
                elif file_type == 'audio':
                    context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption, reply_markup=reply_markup)
                else:  
                    context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption, reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id=chat_id, text="Sorry, the requested file could not be found.")
    except Exception as e:
        logging.error(f"Error sending file to user: {e}")
        context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your request.")
        
def format_file_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes}B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f}KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / (1024**2):.2f}MB"
    else:
        return f"{size_in_bytes / (1024**3):.2f}GB"

def extract_quality(file_name):
    qualities = ["144p", "240p", "360p", "480p", "540p", "720p", "1080p", "2160p", "4K", "8K"]
    for quality in qualities:
        if quality.lower() in file_name.lower():
            return quality
    return ""
            
def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def find_user_by_group(group_id):
    record = db["Listening_Groups"].find_one({"group_id": str(group_id)})
    return record["user_id"] if record else None

def file_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    s_user_id = find_user_by_group(chat_id)  

    parts = callback_data.split("_")
    
    bot_name = context.bot.get_me().first_name
    bot_username = context.bot.get_me().username

    if callback_data.startswith("dse_"):
        doc_id = parts[1]
        message_sender_user_id = int(parts[2])

        if user_id != message_sender_user_id:
            query.answer("Mind your own business. Why don't you search for something of your own? 🚨", show_alert=True)
            return
        
        collection_name = f"DS_collection_{s_user_id}"
        result = db[collection_name].find_one({"_id": ObjectId(doc_id)})

        if result:
            if result.get('proceed_using_method_2'):
                transfer_temp_chat_id = result.get('transfer_temp_chat_id')
                if transfer_temp_chat_id:
                    i_source_chat_id = result.get('chat_id')
                    message_id = result.get('msg_id')
                    
                    try:
                        forwarded_message = context.bot.forward_message(
                            chat_id=int(transfer_temp_chat_id),
                            from_chat_id=int(i_source_chat_id),
                            message_id=int(message_id)
                        )
                    except Exception as e:
                        context.bot.send_message(chat_id=chat_id, text=f"Requested file is being deleted or not available in source chat | Error: {e}")
                        db[collection_name].delete_one({'_id': ObjectId(doc_id)})
                        return

                    alert_message = f"Check PM of {bot_name} [@{bot_username}]. Your file will be there 📨"
                    query.answer(alert_message, show_alert=True)      
                    forwarded_file_id = get_file_id_from_forwarded_message(forwarded_message)
                    try:
                        context.bot.delete_message(chat_id=transfer_temp_chat_id, message_id=forwarded_message.message_id)
                    except:
                        logger.warning(f"Faild to delete temp file in [{transfer_temp_chat_id}] check is the bot have correct permission(s)")
                    if forwarded_file_id:
                        send_forwarded_file(user_id, forwarded_file_id, result, context, s_user_id)
                        return
            else:
                file_id = result['file_id']
                caption = result.get('caption', '')
                custom_buttons = get_user_buttons(s_user_id)
                reply_markup = InlineKeyboardMarkup(custom_buttons) if custom_buttons else None
                
                try:
                    if result.get('file_type') in ['photo', 'image']: 
                        context.bot.send_photo(chat_id=user_id, photo=file_id, caption=caption, reply_markup=reply_markup)
                    elif result.get('file_type') == 'video':
                        context.bot.send_video(chat_id=user_id, video=file_id, caption=caption, reply_markup=reply_markup)
                    elif result.get('file_type') == 'audio':
                        context.bot.send_audio(chat_id=user_id, audio=file_id, caption=caption, reply_markup=reply_markup)
                    else:  
                        context.bot.send_document(chat_id=user_id, document=file_id, caption=caption, reply_markup=reply_markup)
                    
                    alert_message = f"Check PM of {bot_name} [@{bot_username}]. Your file will be there 📨"
                    query.answer(alert_message, show_alert=False)  
                except Exception as e:
                    logging.error(f"Error sending file: {e}")
                    query.answer("Failed to send the file.", show_alert=True)
        else:
            query.answer("File not found.", show_alert=True)
            
    elif callback_data.startswith(("prev_", "next_")):
        parts = callback_data.split("_")
        if len(parts) == 4:
            direction, page_str, user_id, message_sender_user_id = parts[0], parts[1], parts[2], parts[3]
            target_page = int(page_str)
            user_id_from_callback = int(user_id)
            message_sender_user_id_from_callback = int(message_sender_user_id)
            if query.from_user.id == message_sender_user_id_from_callback:
                handle_pagination(update, context, target_page, user_id_from_callback, message_sender_user_id_from_callback)
            else:
                query.answer("Mind your own business. Why don't you search for something of your own? 🚨", show_alert=True)
        else:
            query.answer("Pagination error.", show_alert=True)

def get_file_id_from_forwarded_message(forwarded_message):
    if forwarded_message.photo:
        return forwarded_message.photo[-1].file_id
    elif forwarded_message.video:
        return forwarded_message.video.file_id
    elif forwarded_message.audio:
        return forwarded_message.audio.file_id
    elif forwarded_message.document:
        return forwarded_message.document.file_id
    return None

def send_forwarded_file(chat_id, file_id, file_document, context, user_id):
    file_type = file_document.get('file_type')
    caption = file_document.get('caption', '')
    custom_buttons = get_user_buttons(user_id)

    reply_markup = InlineKeyboardMarkup(custom_buttons) if custom_buttons else None

    try:
        if file_type == 'photo':
            context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, reply_markup=reply_markup)
        elif file_type == 'video':
            context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption, reply_markup=reply_markup)
        elif file_type == 'audio':
            context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption, reply_markup=reply_markup)
        else:
            context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error sending forwarded file: {e}")
        context.bot.send_message(chat_id=chat_id, text=f"Sorry, there was an error processing your request. | Inform the Echo Owner about this error - {e}")

def handle_pagination(update, context, target_page, user_id, message_sender_user_id):
    query = update.callback_query
    message_type = context.user_data.get('message_type', 'default')
    
    collection_name = f"DS_collection_{user_id}"
    search_criteria = context.user_data['search_criteria']
    results = list(db[collection_name].find(search_criteria))

    if results:
        reply_markup = generate_buttons_for_page(update, context, results, target_page, user_id, message_sender_user_id)

        if 'imdb_info' in context.user_data:
            imdb_info = context.user_data['imdb_info']
            if imdb_info and len(imdb_info) > 1024:
                query.edit_message_text(text=imdb_info[:1024] + "... (continued)")
                query.edit_message_reply_markup(reply_markup=reply_markup)
            else:
                query.edit_message_caption(caption=imdb_info, reply_markup=reply_markup)
        else:
            query.edit_message_reply_markup(reply_markup=reply_markup)
    else:
        query.edit_message_text(text="No documents found for this page.")
    query.answer()

def generate_buttons_for_page(update, context, results, page, user_id, message_sender_user_id):
    PAGE_SIZE = 10
    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    start_index = page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(results))
    original_group_id = update.effective_chat.id

    bot_username = context.bot.get_me().username
    buttons = []

    if DS_URL_BUTTONS:
        for result in results[start_index:end_index]:
            file_name = result["file_name"]
            file_id = str(result['_id'])
            file_size = format_file_size(result.get("file_size", 0))
            quality = extract_quality(file_name)
            quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
            doc_id = f"{file_id}_{message_sender_user_id}"
            long_url = f"https://t.me/{bot_username}?start=file_{doc_id}_{original_group_id}"
            if message_sender_user_id == OWNER or message_sender_user_id in AUTHORIZED_USERS or is_subscription_valid(message_sender_user_id):
                short_url = long_url 
            else:
                short_url = get_short_url(long_url)            
            file_name_display = f"{quality_and_size} {file_name}"
            buttons.append([InlineKeyboardButton(text=file_name_display, url=short_url)])
    else:
        for result in results[start_index:end_index]:
            file_name = result["file_name"]
            file_size = format_file_size(result.get("file_size", 0))
            quality = extract_quality(file_name)
            quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
            file_name_display = f"{quality_and_size} {file_name}"
            doc_id = f"dse_{str(result['_id'])}_{message_sender_user_id}"
            buttons.append([InlineKeyboardButton(text=file_name_display, callback_data=doc_id)])

    page_count_button = InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("👈 Prev", callback_data=f"prev_{page - 1}_{user_id}_{message_sender_user_id}"))
    nav_buttons.append(page_count_button)
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next 👉", callback_data=f"next_{page + 1}_{user_id}_{message_sender_user_id}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(buttons)
    return reply_markup


def setup_ds_executor_dispatcher(dispatcher):
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups & ~Filters.command, listen_to_groups), group=3)
    dispatcher.add_handler(CallbackQueryHandler(file_callback_handler, pattern=r'^(prev_\d+_\d+_\d+|next_\d+_\d+_\d+|noop|dse_[a-f0-9]+_\d+)$'))
