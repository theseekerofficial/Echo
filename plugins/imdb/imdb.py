import re
import logging
from imdb import IMDb
from modules.configurator import get_env_var_from_db
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto, ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create an instance of the IMDb class
ia = IMDb()

def imdb_search(update: Update, context: CallbackContext, is_callback=False) -> None:
    imdb_plugin_enabled_str = get_env_var_from_db('IMDb_PLUGIN')
    imdb_plugin_enabled = imdb_plugin_enabled_str.lower() == 'true' if imdb_plugin_enabled_str else False

    if imdb_plugin_enabled:
        if is_callback:
            query = update.callback_query
            search_query = context.user_data.get('last_search', '')
            chat_id = query.message.chat_id
        else:
            search_query = ' '.join(context.args)
            chat_id = update.effective_chat.id
            context.user_data['last_search'] = search_query  

        if not search_query:
            text = "Please provide a movie or TV series name. Usage: `/imdb Avengers`"
            if is_callback:
                query.edit_message_text(text=text)
            else:
                update.message.reply_text(text)
            return

        search_results = ia.search_movie(search_query)[:10] 
        if not search_results:
            text = "No results found."
            if is_callback:
                query.edit_message_text(text=text)
            else:
                update.message.reply_text(text)
            return

        buttons = [
            [InlineKeyboardButton(f"{result['title']} ({result.get('year', 'N/A')})", callback_data=f"imdb_{result.movieID}")]
            for result in search_results
        ]
        caption = f"Here are the 10 best match for <code>{search_query}</code> on IMDb:"
        if is_callback:
            query.edit_message_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            context.bot.send_photo(chat_id=chat_id, photo=open('assets/imdb.jpg', 'rb'), caption=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text("IMDb Plugin Disabled by the person who deployed this Echo Variant 💔")

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def truncate_html_content(s, max_length=1024):
    if len(s) <= max_length:
        return s
    
    tags_and_entities = re.findall(r'<[^>]+>|&[^;]+;', s)
    split_regex = r'(<[^>]+>|&[^;]+;)'
    parts = re.split(split_regex, s)
    
    new_str = ""
    length = 0
    for part in parts:
        if part in tags_and_entities:
            new_str += part
        else:
            if length + len(part) > max_length:
                new_str += part[:max_length - length]
                break
            else:
                new_str += part
                length += len(part)
    
    new_str = re.sub(r'&[^;]+$', '', new_str) 
    new_str = re.sub(r'<[^>]+$', '', new_str)
    
    return new_str + "…"

def imdb_details_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    movie_id = query.data.split('_')[1]

    logger.info(f"🔍 Fetching details for movie ID: {movie_id}")

    movie = ia.get_movie(movie_id)
    if not movie:
        logger.error(f"❌ Failed to retrieve details for movie ID: {movie_id}")
        query.edit_message_text(text="Failed to retrieve details.")
        return

    # Construct IMDb URL
    imdb_url = f"https://www.imdb.com/title/tt{movie_id}/"

    # HTML formatted details
    details = f"<b>Title:</b> {escape_html(movie.get('title', 'N/A'))}\n\n" \
              f"<b>Also Known As:</b> {escape_html(', '.join(movie.get('akas', ['N/A'])))}\n\n" \
              f"<b>Rating:</b> {escape_html(str(movie.get('rating', 'N/A')))}\n\n" \
              f"<b>Release Info:</b> {escape_html(str(movie.get('year', 'N/A')))}\n\n" \
              f"<b>Genre:</b> {escape_html(', '.join(movie.get('genres', ['N/A'])))}\n\n" \
              f"<b>Language:</b> {escape_html(', '.join(movie.get('languages', ['N/A'])))}\n\n" \
              f"<b>Country of Origin:</b> {escape_html(', '.join(movie.get('countries', ['N/A'])))}\n\n" \
              f"<i>Story Line:</i> {escape_html(movie.get('plot outline', 'N/A'))}\n\n" \
              f"<a href='https://www.imdb.com/title/tt{movie_id}/videogallery/'>🎥 Trailer Link</a>"

    details = truncate_html_content(details, 1024)
    
    poster_url = movie.get('full-size cover url', movie.get('cover url'))

    buttons = [
        [InlineKeyboardButton("IMDb Link 🔗", url=imdb_url)],
        [InlineKeyboardButton("🔙 Back", callback_data="imdb_back"),
         InlineKeyboardButton("❌ Close", callback_data="imdb_close")]
    ]

    if len(details) > 1024 and poster_url:
        details_caption = details[:1021] + "…"  
        details_followup = details[1021:]

        message = context.bot.send_photo(chat_id=query.message.chat_id, photo=poster_url, caption=details_caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        
        context.bot.send_message(chat_id=query.message.chat_id, text=details_followup, parse_mode=ParseMode.HTML)
    elif poster_url:
        message = context.bot.send_photo(chat_id=query.message.chat_id, photo=poster_url, caption=details, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        message = context.bot.send_message(chat_id=query.message.chat_id, text=details, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    query.message.delete()

    logger.info(f"✅ Successfully sent details for movie ID: {movie_id}")

def imdb_back_callback(update: Update, context: CallbackContext) -> None:
    imdb_search(update, context, is_callback=True)

def imdb_close_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.delete()

def register_imdb_handlers(dp):
    dp.add_handler(CommandHandler("imdb", imdb_search))
    dp.add_handler(CallbackQueryHandler(imdb_details_callback, pattern="^imdb_[0-9]+"))
    dp.add_handler(CallbackQueryHandler(imdb_back_callback, pattern="^imdb_back$"))
    dp.add_handler(CallbackQueryHandler(imdb_close_callback, pattern="^imdb_close$"))
