import os
import logging
from imdb import IMDb
from bson import ObjectId
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from plugins.doc_spotter.doc_spotter_fsub import is_user_member_of_fsub_chats, prompt_to_join_fsub_chats
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler, Updater, CallbackQueryHandler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup MongoDB connection
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["Echo_Doc_Spotter"]
echo_db = client["Echo"]
imdb = IMDb()  # IMDb instance

PAGE_SIZE = 10
doc_spotter_plugin_enabled = None

def get_doc_spotter_plugin_enabled():
    global doc_spotter_plugin_enabled
    if doc_spotter_plugin_enabled is None:
        doc_spotter_plugin_enabled_str = get_env_var_from_db('DOC_SPOTTER_PLUGIN')
        doc_spotter_plugin_enabled = doc_spotter_plugin_enabled_str.lower() == 'true' if doc_spotter_plugin_enabled_str else False
    return doc_spotter_plugin_enabled

def has_user_started_bot(user_id):
    user_record = echo_db["user_and_chat_data"].find_one({"user_id": user_id})
    return bool(user_record)

def listen_to_groups(update: Update, context: CallbackContext):
    if not get_doc_spotter_plugin_enabled():
        update.message.reply_text("Doc Spotter Plugin Disabled by the person who deployed this Echo variant💔")
        return

    # Check if the user has started the bot
    if not has_user_started_bot(update.message.from_user.id):
        # Obtain the bot's username dynamically
        bot_username = context.bot.get_me().username
        
        # Create the URL to start a conversation with the bot
        start_bot_url = f"https://t.me/{bot_username}?start=welcome"
        
        # Create an InlineKeyboardMarkup with the URL button
        keyboard = [[InlineKeyboardButton("Start Echo ❄️", url=start_bot_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Reply with the message and the URL button
        update.message.reply_text("Hmm... Look like you didn't start me in PM(Privet Message). Please go and start me in PM, So we can start your file seeking journey!💥", reply_markup=reply_markup)
        return
    
    message_text = update.message.text.lower()
    chat_id = update.message.chat.id
    user_id = find_user_by_group(chat_id)
    message_sender_user_id = update.message.from_user.id
    m_user = update.message.from_user

    if not is_user_member_of_fsub_chats(message_sender_user_id, chat_id, client, context):
        prompt_to_join_fsub_chats(update, context, client)
        return 
    
    # Check if the user has a username
    if m_user.username:
        user_mention = f"@{m_user.username}"
    else:
        # Fallback to just using the first name without mentioning if there's no username
        user_mention = m_user.first_name
    
    if not db["Listening_Groups"].find_one({"group_id": str(chat_id)}):
        # If the group is not registered, simply return and do nothing
        return
    
    # If the group is registered, proceed with the rest of the function
    loading_message_text = f"Hold on {user_mention}, searching for '{update.message.text.lower()}'..."
    loading_message = update.message.reply_text(loading_message_text)
    
    if user_id:
        collection_name = f"DS_collection_{user_id}"
        search_text_regex = message_text.replace(" ", "[ ._-]")
        search_criteria = {"file_name": {"$regex": search_text_regex, "$options": "i"}}
        results = list(db[collection_name].find(search_criteria))
        context.user_data['search_criteria'] = search_criteria
        context.user_data['search_results'] = results

        if results:
            try:
                movies = imdb.search_movie(message_text)
                if movies:
                    movie = movies[0]
                    movie_id = movie.movieID
                    movie_details = imdb.get_movie(movie_id)

                    # Attempt to use the full-size cover URL for a higher resolution image
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
                        # If no photo URL is available, use the default image
                        raise Exception("No photo URL found.")
                else:
                    # If no movies are found, use the default image
                    raise Exception("No movies found.")
            except Exception as e:
                # In case of any error, default to the file list with the default image and caption
                logging.error(f"🚫 Error fetching IMDb data: {e}")  # Log the error
                display_page_buttons(update, context, results, 0, user_id)
        else:
            context.bot.delete_message(chat_id=update.message.chat.id, message_id=loading_message.message_id)
            update.message.reply_text("No matching files found.")

def display_page_buttons(update, context, results, page, user_id, imdb_info=None, photo_url=None, is_pagination=False):
    chat_id = update.effective_chat.id
    message_sender_user_id = update.message.from_user.id
    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    start_index = page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(results))

    buttons = []
    for result in results[start_index:end_index]:
        file_name = result["file_name"]
        file_size = format_file_size(result.get("file_size", 0))
        quality = extract_quality(file_name)
        quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
        file_name_display = f"{quality_and_size} {file_name}"
        doc_id = f"dse_{result['_id']}_{message_sender_user_id}"  # Modify this line
        buttons.append([InlineKeyboardButton(text=file_name_display, callback_data=doc_id)])

    # Include the page count display
    page_count_button = InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("👈 Prev", callback_data=f"prev_{page - 1}_{user_id}_{message_sender_user_id}"))
    nav_buttons.append(page_count_button)
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next 👉", callback_data=f"next_{page + 1}_{user_id}_{message_sender_user_id}"))
    
    # Add navigation buttons if they exist
    if nav_buttons:
        buttons.append(nav_buttons)  # Add as a separate row
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # Determine which image to send
    if not photo_url:  # If no IMDb photo, use default image
        photo_path = os.path.join('assets', 'doc_spotter.jpg')  # Update this path as necessary
        caption = imdb_info if imdb_info else "Here is what I found in the database:"
        with open(photo_path, 'rb') as photo:
            context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
    else:
        # If IMDb info is too long, send it as a separate text message
        if imdb_info and len(imdb_info) > 1024:
            message = context.bot.send_message(chat_id=chat_id, text=imdb_info[:1024] + "... (continued)")
            imdb_message_id = message.message_id
            context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption="Here is what I found in the database:", reply_markup=reply_markup, reply_to_message_id=imdb_message_id)
        else:
            # Send IMDb info with the photo and buttons
            context.bot.send_photo(chat_id=chat_id, photo=photo_url, caption=imdb_info, reply_markup=reply_markup)
    logging.info(f"✅ User {update.effective_user.id} received IMDB info and poster for '{update.message.text}' in chat {update.message.chat.id}")

def format_file_size(size_in_bytes):
    # Convert file size from bytes to a readable format (KB, MB, GB)
    if size_in_bytes < 1024:
        return f"{size_in_bytes}B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f}KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / (1024**2):.2f}MB"
    else:
        return f"{size_in_bytes / (1024**3):.2f}GB"

def extract_quality(file_name):
    # Extract quality information from the file name
    qualities = ["144p", "240p", "360p", "480p", "540p", "720p", "1080p", "4K", "8K"]
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
    # This seems to be the intended user_id for sending files back.
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    s_user_id = find_user_by_group(chat_id)  # The user_id associated with the chat_id from the groups.

    parts = callback_data.split("_")
    
    # Dynamically get the bot's name and username
    bot_name = context.bot.get_me().first_name
    bot_username = context.bot.get_me().username

    if callback_data.startswith("dse_"):
        doc_id = parts[1]  # Adjusted to match new callback data format
        message_sender_user_id = int(parts[2])  # Ensure this is an int for comparison

        if user_id != message_sender_user_id:
            # Show an inline alert to the user
            query.answer("Mind your own business. Why don't you search for something of your own? 🚨", show_alert=True)
            return
        
        collection_name = f"DS_collection_{s_user_id}"
        result = db[collection_name].find_one({"_id": ObjectId(doc_id)})

        if result:
            file_id = result['file_id']
            caption = result.get('caption', '')  # Get the caption if it exists, else default to empty string
            try:
                # Check the file type and send accordingly with caption
                if result.get('file_type') in ['photo', 'image']: 
                    context.bot.send_photo(chat_id=user_id, photo=file_id, caption=caption)
                elif result.get('file_type') == 'video':
                    context.bot.send_video(chat_id=user_id, video=file_id, caption=caption)
                elif result.get('file_type') == 'audio':
                    context.bot.send_audio(chat_id=user_id, audio=file_id, caption=caption)
                else:  # Default to document if not matching specific types
                    context.bot.send_document(chat_id=user_id, document=file_id, caption=caption)
                
                # Answer the query with a notification message
                alert_message = f"Check PM of {bot_name} [@{bot_username}]. Your file will be there 📨"
                query.answer(alert_message, show_alert=False)  # Use 'False' for a toast notification
            except Exception as e:
                print(f"Error sending file: {e}")
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
                # Proceed with pagination since the user IDs match
                handle_pagination(update, context, target_page, user_id_from_callback, message_sender_user_id_from_callback)
            else:
                # User IDs do not match; send a warning message
                query.answer("Mind your own business. Why don't you search for something of your own? 🚨", show_alert=True)
        else:
            query.answer("Pagination error.", show_alert=True)

def handle_pagination(update, context, target_page, user_id, message_sender_user_id):
    query = update.callback_query
    message_type = context.user_data.get('message_type', 'default')
    
    collection_name = f"DS_collection_{user_id}"
    search_criteria = context.user_data['search_criteria']
    results = list(db[collection_name].find(search_criteria))

    if results:
        # Pass the `query.from_user.id` as `message_sender_user_id`
        reply_markup = generate_buttons_for_page(results, target_page, user_id, message_sender_user_id)

        # Proceed to update the message or send a new message based on the results
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

def generate_buttons_for_page(results, page, user_id, message_sender_user_id):
    PAGE_SIZE = 10
    total_pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    start_index = page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(results))

    buttons = []
    for result in results[start_index:end_index]:
        file_name = result["file_name"]
        file_size = format_file_size(result.get("file_size", 0))
        quality = extract_quality(file_name)
        quality_and_size = f"[{file_size}/{quality}]" if quality else f"[{file_size}]"
        file_name_display = f"{quality_and_size} {file_name}"
        doc_id = f"dse_{str(result['_id'])}_{message_sender_user_id}"
        buttons.append([InlineKeyboardButton(text=file_name_display, callback_data=doc_id)])

    # Include the page count display
    page_count_button = InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("👈 Prev", callback_data=f"prev_{page - 1}_{user_id}_{message_sender_user_id}"))
    nav_buttons.append(page_count_button)
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next 👉", callback_data=f"next_{page + 1}_{user_id}_{message_sender_user_id}"))
    
    # Add navigation buttons if they exist
    if nav_buttons:
        buttons.append(nav_buttons)  # Add as a separate row
    reply_markup = InlineKeyboardMarkup(buttons)
    return reply_markup


def setup_ds_executor_dispatcher(dispatcher):
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups & ~Filters.command, listen_to_groups), group=3)
    dispatcher.add_handler(CallbackQueryHandler(file_callback_handler, pattern=r'^(prev_\d+_\d+_\d+|next_\d+_\d+_\d+|noop|dse_[a-f0-9]+_\d+)$'))

