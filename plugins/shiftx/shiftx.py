# shiftx.py
import os
import logging
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from .shiftx_logics import pdf_to_word, jpeg_to_png, png_to_jpeg, svg_to_png, svg_to_jpeg, tiff_to_png, tiff_to_jpeg, webp_to_png, webp_to_jpeg, png_to_tiff, jpeg_to_tiff, png_to_webp, jpeg_to_webp, pdf_to_txt, txt_to_pdf, mp3_to_aac, aac_to_mp3, mp3_to_ogg, ogg_to_mp3, cleanup_file, temp_dir, is_correct_file_type

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

def shiftx_start(update: Update, _: CallbackContext) -> None:
    shiftx_plugin_enabled_str = get_env_var_from_db('SHIFTX_PLUGIN')
    shiftx_plugin_enabled = shiftx_plugin_enabled_str.lower() == 'true' if shiftx_plugin_enabled_str else False

    if not shiftx_plugin_enabled:
        update.message.reply_text("ShiftX Plugin Disabled by the person who deployed this Echo Variant 💔")
        return
        
    keyboard = [
        [InlineKeyboardButton("Documents", callback_data='shiftx_documents')],
        [InlineKeyboardButton("Images", callback_data='shiftx_images')],
        [InlineKeyboardButton("Audio", callback_data='shiftx_audio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        query = update.callback_query
        query.edit_message_text(text='Choose a category to start ShiftX 🔄️', reply_markup=reply_markup)
    else:
        update.message.reply_text('Choose a category to start ShiftX 🔄️', reply_markup=reply_markup)

def shiftx_documents_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("PDF to Word", callback_data='shiftx_pdf_to_word')],
        [InlineKeyboardButton("PDF to TXT", callback_data='shiftx_pdf_to_txt')],
        [InlineKeyboardButton("TXT to PDF", callback_data='shiftx_txt_to_pdf')],
        [InlineKeyboardButton("Back", callback_data='shiftx_back_to_main_menu')] 
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Now choose a file pair!", reply_markup=reply_markup)


def shiftx_images_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("JPEG to PNG", callback_data='shiftx_jpeg_to_png'),
         InlineKeyboardButton("JPEG to TIFF", callback_data='shiftx_jpeg_to_tiff'),
         InlineKeyboardButton("JPEG to WebP", callback_data='shiftx_jpeg_to_webp')],
        
        [InlineKeyboardButton("PNG to JPEG", callback_data='shiftx_png_to_jpeg'),
         InlineKeyboardButton("PNG to TIFF", callback_data='shiftx_png_to_tiff'),
         InlineKeyboardButton("PNG to WebP", callback_data='shiftx_png_to_webp')],

        [InlineKeyboardButton("SVG to PNG", callback_data='shiftx_svg_to_png'),
         InlineKeyboardButton("SVG to JPEG", callback_data='shiftx_svg_to_jpeg')],
        
        [InlineKeyboardButton("TIFF to PNG", callback_data='shiftx_tiff_to_png'),
         InlineKeyboardButton("TIFF to JPEG", callback_data='shiftx_tiff_to_jpeg')],
        
        [InlineKeyboardButton("WebP to PNG", callback_data='shiftx_webp_to_png'),
         InlineKeyboardButton("WebP to JPEG", callback_data='shiftx_webp_to_jpeg')],

        [InlineKeyboardButton("Back", callback_data='shiftx_back_to_main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Select the conversion type:", reply_markup=reply_markup)

def shiftx_audio_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("MP3 to AAC", callback_data='shiftx_mp3_to_aac')],
        [InlineKeyboardButton("AAC to MP3", callback_data='shiftx_aac_to_mp3')],
        [InlineKeyboardButton("MP3 to OGG", callback_data='shiftx_mp3_to_ogg')],  
        [InlineKeyboardButton("OGG to MP3", callback_data='shiftx_ogg_to_mp3')],
        [InlineKeyboardButton("Back", callback_data='shiftx_back_to_main_menu')] 
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Now choose a file pair!", reply_markup=reply_markup)


def shiftx_convert_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == 'shiftx_pdf_to_word':
        context.user_data['shiftx_action'] = 'pdf_to_word'
        text = "Okay, Now send your PDF file to me."

    elif data == 'shiftx_jpeg_to_png':  
        context.user_data['shiftx_action'] = 'jpeg_to_png'
        text = "Okay, Now send your JPEG file to me."

    elif data == 'shiftx_png_to_jpeg':  
        context.user_data['shiftx_action'] = 'png_to_jpeg'
        text = "Okay, Now send your PNG file to me."

    elif data == 'shiftx_svg_to_png':
        context.user_data['shiftx_action'] = 'svg_to_png'
        text = "Okay, Now send your SVG file to me."

    elif data == 'shiftx_svg_to_jpeg':
        context.user_data['shiftx_action'] = 'svg_to_jpeg'
        text = "Okay, Now send your SVG file to me."

    elif data.startswith('shiftx_'):
        action = data.replace('shiftx_', '')
        context.user_data['shiftx_action'] = action
        file_type = action.split('_to_')[0].upper()
        text = f"Okay, Now send your {file_type} file to me."
    
    query.edit_message_text(text=text)

def shiftx_file_handler(update: Update, context: CallbackContext) -> None:
    if 'shiftx_action' not in context.user_data:
        return  
        
    action = context.user_data['shiftx_action']
    if update.message.document:
        file = update.message.document
        file_name = file.file_name  
    elif update.message.audio:
        file = update.message.audio
        file_name = file.file_name if file.file_name else file.title

    if not file_name: 
        update.message.reply_text("Could not determine the file name.")
        return
    file_id = file.file_id
    new_file = context.bot.getFile(file_id)
    temp_file_path = os.path.join(temp_dir, file.file_name)

    if action == 'pdf_to_word':
        if not is_correct_file_type(file_name, '.pdf'):
            update.message.reply_text("Please send a PDF file.")
            return
        new_file.download(temp_file_path)
        word_file_path = temp_file_path.replace('.pdf', '_converted.docx')
        pdf_to_word(temp_file_path, word_file_path)
        update.message.reply_document(document=open(word_file_path, 'rb'), caption="Here's your converted WORD file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(word_file_path)
  
    elif action == 'pdf_to_txt':
        if not is_correct_file_type(file_name, '.pdf'):
            update.message.reply_text("Please send a PDF file.")
            return
        new_file.download(temp_file_path)
        txt_file_path = temp_file_path.replace('.pdf', '_converted.txt')
        pdf_to_txt(temp_file_path, txt_file_path)
        update.message.reply_document(document=open(txt_file_path, 'rb'), caption="Here's your converted TXT file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(txt_file_path)

    elif action == 'txt_to_pdf':
        if not is_correct_file_type(file_name, '.txt'):
            update.message.reply_text("Please send a TXT file.")
            return
        new_file.download(temp_file_path)
        pdf_file_path = temp_file_path.replace('.txt', '_converted.pdf')
        txt_to_pdf(temp_file_path, pdf_file_path)
        update.message.reply_document(document=open(pdf_file_path, 'rb'), caption="Here's your converted PDF file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(pdf_file_path)
    
    elif action == 'jpeg_to_png': 
        if not is_correct_file_type(file_name, '.jpeg'):
            update.message.reply_text("Please send a JPEG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        png_file_path = temp_file_path.replace('.jpeg', '.png').replace('.jpg', '.png')
        jpeg_to_png(temp_file_path, png_file_path)
        update.message.reply_document(document=open(png_file_path, 'rb'), caption="Here's your converted PNG File.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(png_file_path)

    elif action == 'png_to_jpeg': 
        if not is_correct_file_type(file_name, '.png'):
            update.message.reply_text("Please send a PNG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        jpeg_file_path = temp_file_path.replace('.png', '_converted.jpeg')
        png_to_jpeg(temp_file_path, jpeg_file_path)
        update.message.reply_document(document=open(jpeg_file_path, 'rb'), caption="Here's your converted JPEG File.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(jpeg_file_path)

    elif action == 'svg_to_png':
        if not is_correct_file_type(file_name, '.svg'):
            update.message.reply_text("Please send a SVG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        png_file_path = temp_file_path.replace('.svg', '_converted.png')
        svg_to_png(temp_file_path, png_file_path)
        update.message.reply_document(document=open(png_file_path, 'rb'), caption="Here's your converted PNG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(png_file_path)

    elif action == 'svg_to_jpeg':
        if not is_correct_file_type(file_name, '.svg'):
            update.message.reply_text("Please send a SVG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        jpeg_file_path = temp_file_path.replace('.svg', '_converted.jpeg')
        svg_to_jpeg(temp_file_path, jpeg_file_path)
        update.message.reply_document(document=open(jpeg_file_path, 'rb'), caption="Here's your converted JPEG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(jpeg_file_path)

    elif action == 'tiff_to_png':
        if not is_correct_file_type(file_name, '.tiff'):
            update.message.reply_text("Please send a TIFF file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        png_file_path = temp_file_path.replace('.tiff', '_converted.png').replace('.tif', '_converted.png')
        tiff_to_png(temp_file_path, png_file_path)
        update.message.reply_document(document=open(png_file_path, 'rb'), caption="Here's your converted PNG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(png_file_path)

    elif action == 'tiff_to_jpeg':
        if not is_correct_file_type(file_name, '.tiff'):
            update.message.reply_text("Please send a TIFF file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        jpeg_file_path = temp_file_path.replace('.tiff', '_converted.jpeg').replace('.tif', '_converted.jpeg')
        tiff_to_jpeg(temp_file_path, jpeg_file_path)
        update.message.reply_document(document=open(jpeg_file_path, 'rb'), caption="Here's your converted JPEG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(jpeg_file_path)

    elif action == 'webp_to_png':
        if not is_correct_file_type(file_name, '.webp'):
            update.message.reply_text("Please send a WEBP file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        png_file_path = temp_file_path.replace('.webp', '_converted.png')
        webp_to_png(temp_file_path, png_file_path)
        update.message.reply_document(document=open(png_file_path, 'rb'), caption="Here's your converted PNG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(png_file_path)

    elif action == 'webp_to_jpeg':
        if not is_correct_file_type(file_name, '.webp'):
            update.message.reply_text("Please send a WEBP file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        jpeg_file_path = temp_file_path.replace('.webp', '_converted.jpeg')
        webp_to_jpeg(temp_file_path, jpeg_file_path)
        update.message.reply_document(document=open(jpeg_file_path, 'rb'), caption="Here's your converted JPEG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(jpeg_file_path)

    elif action == 'png_to_tiff':
        if not is_correct_file_type(file_name, '.png'):
            update.message.reply_text("Please send a PNG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        tiff_file_path = temp_file_path.replace('.png', '_converted.tiff')
        png_to_tiff(temp_file_path, tiff_file_path)
        update.message.reply_document(document=open(tiff_file_path, 'rb'), caption="Here's your converted TIFF file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(tiff_file_path)

    elif action == 'jpeg_to_tiff':
        if not is_correct_file_type(file_name, '.jpeg'):
            update.message.reply_text("Please send a JPEG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        tiff_file_path = temp_file_path.replace('.jpeg', '_converted.tiff').replace('.jpg', '_converted.tiff')
        jpeg_to_tiff(temp_file_path, tiff_file_path)
        update.message.reply_document(document=open(tiff_file_path, 'rb'), caption="Here's your converted TIFF file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(tiff_file_path)

    elif action == 'png_to_webp':
        if not is_correct_file_type(file_name, '.png'):
            update.message.reply_text("Please send a PNG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        webp_file_path = temp_file_path.replace('.png', '_converted.webp')
        png_to_webp(temp_file_path, webp_file_path)
        update.message.reply_document(document=open(webp_file_path, 'rb'), caption="Here's your converted WebP file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(webp_file_path)

    elif action == 'jpeg_to_webp':
        if not is_correct_file_type(file_name, '.jpeg'):
            update.message.reply_text("Please send a JPEG file. Send as a File not as a Image")
            return
        new_file.download(temp_file_path)
        webp_file_path = temp_file_path.replace('.jpeg', '_converted.webp').replace('.jpg', '_converted.webp')
        jpeg_to_webp(temp_file_path, webp_file_path)
        update.message.reply_document(document=open(webp_file_path, 'rb'), caption="Here's your converted WebP file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(webp_file_path)

    elif action == 'mp3_to_aac':
        if not is_correct_file_type(file_name, '.mp3'):
            update.message.reply_text("Please send a MP3 file.")
            return
        new_file.download(temp_file_path)
        aac_file_path = temp_file_path.rsplit('.', 1)[0] + '.aac'
        mp3_to_aac(temp_file_path, aac_file_path)
        update.message.reply_document(document=open(aac_file_path, 'rb'), caption="Here's your converted AAC file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(aac_file_path)

    elif action == 'aac_to_mp3':
        if not is_correct_file_type(file_name, '.aac'):
            update.message.reply_text("Please send a AAC file.")
            return
        new_file.download(temp_file_path)
        mp3_file_path = temp_file_path.rsplit('.', 1)[0] + '.mp3'
        aac_to_mp3(temp_file_path, mp3_file_path)
        update.message.reply_document(document=open(mp3_file_path, 'rb'), caption="Here's your converted MP3 file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(mp3_file_path)

    elif action == 'mp3_to_ogg':
        if not is_correct_file_type(file_name, '.mp3'):
            update.message.reply_text("Please send an MP3 file.")
            return
        new_file.download(temp_file_path)
        ogg_file_path = temp_file_path.rsplit('.', 1)[0] + '.ogg'
        mp3_to_ogg(temp_file_path, ogg_file_path)
        update.message.reply_document(document=open(ogg_file_path, 'rb'), caption="Here's your converted OGG file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(ogg_file_path)

    elif action == 'ogg_to_mp3':
        if not is_correct_file_type(file_name, '.ogg'):
            update.message.reply_text("Please send an OGG file.")
            return
        new_file.download(temp_file_path)
        mp3_file_path = temp_file_path.rsplit('.', 1)[0] + '.mp3'
        ogg_to_mp3(temp_file_path, mp3_file_path)
        update.message.reply_document(document=open(mp3_file_path, 'rb'), caption="Here's your converted MP3 file.\n\nPowerd by @Echo_AIO")
        cleanup_file(temp_file_path)
        cleanup_file(mp3_file_path)
    
    del context.user_data['shiftx_action']

def register_shiftx_handlers(dp):    
    dp.add_handler(token_system.token_filter(CommandHandler('shiftx', shiftx_start)))
    dp.add_handler(CallbackQueryHandler(shiftx_documents_callback, pattern='^shiftx_documents$'))
    dp.add_handler(CallbackQueryHandler(shiftx_convert_callback, pattern='^shiftx_pdf_to_word$'))
    dp.add_handler(CallbackQueryHandler(shiftx_images_callback, pattern='^shiftx_images$'))  
    dp.add_handler(CallbackQueryHandler(shiftx_audio_callback, pattern='^shiftx_audio$'))
    dp.add_handler(CallbackQueryHandler(shiftx_convert_callback, pattern='^shiftx_(pdf_to_word|pdf_to_txt|txt_to_pdf|jpeg_to_png|png_to_jpeg|svg_to_png|svg_to_jpeg|tiff_to_png|tiff_to_jpeg|webp_to_png|webp_to_jpeg|png_to_tiff|jpeg_to_tiff|png_to_webp|jpeg_to_webp|mp3_to_aac|aac_to_mp3|mp3_to_ogg|ogg_to_mp3)$'))
    dp.add_handler(CallbackQueryHandler(shiftx_start, pattern='^shiftx_back_to_main_menu$'))
    dp.add_handler(MessageHandler(Filters.document & (Filters.chat_type.private | Filters.chat_type.groups), shiftx_file_handler), group=7)
    dp.add_handler(MessageHandler(Filters.audio & (Filters.chat_type.private | Filters.chat_type.groups), shiftx_file_handler), group=7)
