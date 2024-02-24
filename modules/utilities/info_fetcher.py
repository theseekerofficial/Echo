import os
import re
import random
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton

def send_user_id_info(update: Update, context: CallbackContext) -> None:
    args = context.args
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    message_id = update.message.message_id

    if update.message.chat.type in ["group", "supergroup"]:
        keyboard = [
            [InlineKeyboardButton("Group info", callback_data=f"if_groupinfo_{chat_id}_{user_id}"),
             InlineKeyboardButton("My info", callback_data=f"if_myinfo_{user_id}_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"{update.message.from_user.mention_markdown()}, what info do you need to see?",
                                  reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        return
    
    # If arguments are provided, handle them with a different function
    if args:
        send_info_by_username_or_id(update, context)
        return
        
    try:
        chat_id = update.message.chat_id
        message = update.message.reply_to_message if update.message.reply_to_message else update.message
        target = None

        if message.forward_from:
            target = message.forward_from
            caption = user_or_bot_caption(target)
        elif message.forward_from_chat:
            target = message.forward_from_chat
            caption = chat_caption(target)
        else:
            target = message.from_user
            caption = user_or_bot_caption(target, own=True)

        send_profile_or_default_photo(context, target, chat_id, caption, update)
    except BadRequest as e:
        context.bot.send_message(chat_id=chat_id, text="⚠️ Error retrieving information. Please try again.", parse_mode=ParseMode.MARKDOWN)
        
def user_or_bot_caption(user, own=False, is_bot=None):
    # Determine entity type based on is_bot parameter or user.is_bot attribute
    entity_type = "Bot" if is_bot or (hasattr(user, 'is_bot') and user.is_bot) else "User"
    prefix = "Your" if own else f"Forwarded {entity_type}"
    username = f"@{user.username}" if hasattr(user, 'username') and user.username else "None"
    profile_link = f"tg://user?id={user.id}" if not hasattr(user, 'username') or not user.username else f"https://t.me/{user.username}"
    caption = f"*{prefix} Profile Information:*_(Check the Info Category in help for details on using the Info command)_\n\n" \
              f"🆔 {entity_type} ID: `{user.id}`\n" \
              f"👤 Full Name: *{user.full_name}*\n" \
              f"🔗 Username: *{username}*\n"
    if hasattr(user, 'language_code'):
        caption += f"🌐 Language: *{user.language_code if user.language_code else 'Not specified'}*\n"
    caption += f"🔗 Profile Link: [Click Here]({profile_link})"
    if not own:
        caption += f"\n🤖 Is Bot: *{'Yes' if entity_type == 'Bot' else 'No'}*"
    return caption

def chat_caption(chat):
    chat_type = "Channel" if chat.type == 'channel' else "Group"
    username = f"@{chat.username}" if chat.username else "None"
    chat_link = f"https://t.me/{chat.username}" if chat.username else "Not available"
    caption = f"*Forwarded {chat_type} Information:*\n\n" \
              f"🆔 Chat ID: `{chat.id}`\n" \
              f"👤 Chat Name: *{chat.title}*\n" \
              f"🔗 Username: *{username}*\n" \
              f"🔗 Chat Link: [Click Here]({chat_link})"
    return caption

def send_profile_or_default_photo(context, target, chat_id, caption, update):
    try:
        # For users, attempt to fetch and send a profile photo
        if hasattr(target, 'is_bot') or (hasattr(target, 'type') and target.type == 'private'):
            photos = context.bot.get_user_profile_photos(target.id, limit=1)
            if photos.photos:
                photo_file_id = photos.photos[0][-1].file_id
                context.bot.send_photo(chat_id=chat_id, photo=photo_file_id, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
                return
        # For chats or if no photo is available, send a default photo
        send_default_photo(context, chat_id, caption, update)
    except BadRequest:
        send_default_photo(context, chat_id, caption, update)

def send_default_photo(context, chat_id, caption, update):
    default_images_directory = os.path.join(os.getcwd(), 'assets', 'info_assets')
    default_image_filenames = [f for f in os.listdir(default_images_directory) if os.path.isfile(os.path.join(default_images_directory, f))]
    selected_filename = random.choice(default_image_filenames)
    default_photo_path = os.path.join(default_images_directory, selected_filename)
    with open(default_photo_path, 'rb') as default_photo:
        context.bot.send_photo(chat_id=chat_id, photo=default_photo, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

def send_info_by_username_or_id(update: Update, context: CallbackContext) -> None:
    args = context.args
    chat_id = update.message.chat_id

    if not args:
        # Handle the case where no arguments are provided by showing the user's own info
        target = update.message.from_user
        caption = user_or_bot_caption(target, own=True)
        send_profile_or_default_photo(context, target, chat_id, caption, update)
        return

    entity_id_or_username = args[0]
    if entity_id_or_username.isdigit():
        entity_id_or_username = int(entity_id_or_username)

    try:
        entity = context.bot.get_chat(entity_id_or_username)

        # Determine if the entity is a user, group, or channel based on the type attribute
        if entity.type == 'private':
            # Since get_chat doesn't differentiate between a user and a bot, you might need to customize this part
            is_bot = False  # Placeholder, adjust based on your application's needs
            caption = user_or_bot_caption(entity, is_bot=False)  # Customize this part to correctly handle bot detection if necessary
        elif entity.type in ['group', 'supergroup', 'channel']:
            caption = chat_caption(entity)
        else:
            # Fallback or error handling for unsupported entity types
            caption = "Unsupported entity type."
            context.bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
            return

        send_profile_or_default_photo(context, entity, chat_id, caption, update)

    except BadRequest as e:
        error_message = "Could not fetch information for the provided username or ID."
        context.bot.send_message(chat_id=chat_id, text=error_message, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

def button_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data.split("_")
    command, info_type, target_id, user_id = data

    # Authorization check
    if query.from_user.id != int(user_id):
        query.answer("Not Yours!", show_alert=True)
        return
    else:
        query.answer()

    if info_type == "groupinfo":
        # Fetch and send group info
        entity = context.bot.get_chat(target_id)
        caption = chat_caption(entity)
        send_profile_or_default_photo(context, entity, target_id, caption, query)
    elif info_type == "myinfo":
        # Fetch and send user info
        entity = context.bot.get_chat(user_id)
        caption = user_or_bot_caption(entity, own=True)
        send_profile_or_default_photo(context, entity, query.message.chat_id, caption, query)

    query.message.delete()   

# Modify the register_id_command function to handle commands with arguments
def register_id_command(dispatcher):
    id_handler = CommandHandler("info", send_user_id_info, pass_args=True, run_async=True)
    dispatcher.add_handler(id_handler)

    callback_handler = CallbackQueryHandler(button_callback_handler, pattern="^if_")
    dispatcher.add_handler(callback_handler)
