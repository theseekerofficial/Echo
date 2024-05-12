# super_plugins/guardian/welcomer/welcomer.py
import os
import sys
from loguru import logger
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode, Message
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, Filters, ChatMemberHandler

from super_plugins.guardian.welcomer.welcomer_logic import handle_chat_member_update, preview_welcome_message

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def welcomer_setup_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        chat_id = query.data.split('_')[-1]
        context.user_data['wlc_chat_id'] = chat_id
        chat = context.bot.get_chat(chat_id)
        
        user_member = chat.get_member(query.from_user.id)
        bot_member = chat.get_member(context.bot.id)

        user_has_permissions = has_required_permissions(user_member)
        bot_has_permissions = has_required_permissions(bot_member)

        if not user_has_permissions or not bot_has_permissions:
            missing_permissions = []
            if not user_has_permissions:
                missing_permissions.append("User")
            if not bot_has_permissions:
                missing_permissions.append("Bot")
            missing_perms_text = " and ".join(missing_permissions)
            query.answer(f"{missing_perms_text} lack necessary permissions ('Change Group Info', 'Invite Users') in this chat.", show_alert=True)
            return

    try:
        chat_id = context.user_data['wlc_chat_id']
        chat = context.bot.get_chat(chat_id)
        chat_name = chat.title
        
        collection = db[str(chat_id)]
        doc = collection.find_one({'identifier': 'welcomer'})
        
        if doc is None:
            logger.info(f"No welcomer document found for chat_id {chat_id}. Using default settings.")
            welcomer_state = False
            send_in_pm = False
            wlc_msg_stats = "❌"
            wlc_media_stats = "❌"
            wlc_buttons_stats = "❌"
            wlc_topic_stats = "❌"
        else:
            welcomer_state = doc.get('welcomer_state', False)
            send_in_pm = doc.get('set_pm', False) if doc else False
            wlc_msg_stats = "✅" if doc.get('welcome_msg', False) else "❌"
            wlc_media_stats = "✅" if doc.get('media_id', False) else "❌"
            wlc_buttons_stats = "✅" if doc.get('welcome_buttons', False) else "❌"
            wlc_topic_stats = "✅" if doc.get('topic_id', False) else "❌"
            
        state_button = InlineKeyboardButton("❌ Deactivate Welcomer", callback_data=f"deactivate_welcomer_{chat_id}") if welcomer_state else InlineKeyboardButton("✅ Activate Welcomer", callback_data=f"activate_welcomer_{chat_id}")
        pm_button = InlineKeyboardButton("Send in PM 📨 [✅]", callback_data=f"wlc_toggle_pm_{chat_id}") if send_in_pm else InlineKeyboardButton("Send in PM 📨 [❌]", callback_data=f"wlc_toggle_pm_{chat_id}")
        status_text = "Activated" if welcomer_state else "Deactivated"
        send_in_pm_ststs = "✅" if send_in_pm else "❌"
        
        keyboard = [
            [InlineKeyboardButton("✍️ Text", callback_data=f"set_welcome_text_{chat_id}"), InlineKeyboardButton(" 👁️ See", callback_data=f"see_welcome_text_{chat_id}")],
            [InlineKeyboardButton("📸 Media", callback_data=f"set_welcome_media_{chat_id}"), InlineKeyboardButton("👁️ See", callback_data=f"see_welcome_media_{chat_id}")],
            [InlineKeyboardButton("🔘 URL Buttons", callback_data=f"set_welcome_buttons_{chat_id}"), InlineKeyboardButton("👁️ See", callback_data=f"see_welcome_buttons_{chat_id}")],
            [InlineKeyboardButton("📌 Set a Topic", callback_data=f"set_welcome_topic_{chat_id}"), pm_button],
            [state_button, InlineKeyboardButton("🪻 Preview a Snapshot", callback_data=f"preview_welcome_message_{chat_id}")],
            [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"grd_back_to_primary_menu_{chat_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            query.edit_message_text(text=f"❄️ Setup a custom welcome message for your <code>{chat_name}</code> group\n\n⚡ Feature Status: <code>{status_text}</code>\n\n<i>Welcome Message</i>: {wlc_msg_stats}\n<i>Welcome Media</i>: {wlc_media_stats}\n<i>Welcome Buttons</i>: {wlc_buttons_stats}\n<i>Topic Enabled</i>: {wlc_topic_stats}\n<i>Send in PM too</i>: {send_in_pm_ststs}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            need_to_edit_msg = context.user_data['wlc_msg_message_id']
            context.bot.edit_message_text(chat_id=update.message.chat_id, text=f"❄️ Setup a custom welcome message for your <code>{chat_name}</code> group\n\n⚡ Feature Status: <code>{status_text}</code>\n\n<i>Welcome Message</i>: {wlc_msg_stats}\n<i>Welcome Media</i>: {wlc_media_stats}\n<i>Welcome Buttons</i>: {wlc_buttons_stats}\n<i>Topic Enabled</i>: {wlc_topic_stats}\n<i>Send in PM too</i>: {send_in_pm_ststs}", reply_markup=reply_markup, message_id=need_to_edit_msg, parse_mode=ParseMode.HTML)
            context.user_data.pop('wlc_msg_message_id')
    except Exception as e:
        logger.error(f"Failed to setup welcomer: {e}")
        query.answer("Error during setup. Check bot's membership and permissions.", show_alert=True)

def has_required_permissions(member):
    if member.status == 'creator':
        return True
    required_permissions = ['can_change_info', 'can_invite_users']
    return all(getattr(member, perm, False) for perm in required_permissions)

def handle_set_text(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    user_id = query.from_user.id
    chat = context.bot.get_chat(chat_id)
    chat_name = chat.title

    context.user_data['awaiting_text'] = {'chat_id': chat_id, 'user_id': user_id}
    context.user_data['awt_wlc_text'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")],
        [InlineKeyboardButton("♻️ Delete", callback_data=f"delete_welcome_entry-text{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = query.edit_message_text(
        text=f"""⭕ Currently Engaging on: <code>{chat_name}</code>\n\n📝 Now Send a custom text for your group welcome message\n\nYou can use below custom handlers:\n\n<code>[id]\n[first_name]\n[second_name]\n[mention]\n[username]\n[time(timezone)]\n[date(timezone)]\n[group_name]\n[group_id]\n[admin_count]\n[invite_link]</code>\n\n<i>Also you can use HTML tags for formatting the message</i>\n\n<code>(&lt;b&gt, &lt;i&gt, &lt;u&gt, &lt;code&gt, &lt;tg-spoiler&gt)</code>\n\n<i>Hyper Links are also support too;</i>\nExample: <code>&lt;a href="https://www.example.com"&gt;Visit Example Website&lt;/a&gt;</code>""", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['wlc_msg_message_id'] = msg.message_id

def handle_set_media(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    user_id = query.from_user.id
    chat = context.bot.get_chat(chat_id)
    chat_name = chat.title

    context.user_data['awaiting_media'] = {'chat_id': chat_id, 'user_id': user_id}
    context.user_data['awt_wlc_media'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")],
        [InlineKeyboardButton("♻️ Delete", callback_data=f"delete_welcome_entry-media{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = query.edit_message_text(
        text=f"⭕ Currently Engaging on: <code>{chat_name}</code>\n\n📸 Now send me a media file to send along with the welcome message. <i>It can be anything; Video, Photo, GIF, Document</i>", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    context.user_data['wlc_msg_message_id'] = msg.message_id

def handle_set_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    user_id = query.from_user.id
    chat = context.bot.get_chat(chat_id)
    chat_name = chat.title

    context.user_data['awaiting_buttons'] = {'chat_id': chat_id, 'user_id': user_id}
    context.user_data['awt_wlc_buttons'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")],
        [InlineKeyboardButton("♻️ Delete", callback_data=f"delete_welcome_entry-buttons{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = query.edit_message_text(
        text=f"""⭕ Currently Engaging on: <code>{chat_name}</code>\n\n<i>🚀 Create Your Custom URL Button List for Welcome Messages. You can customize your welcome messages by adding URL buttons that link to various resources. Here's how you can format your button lists to make your messages more interactive and user-friendly:</i>

<i>Format Guide:</i>

<b>Use " - " to separate the button label and the URL link.
Use " | " to place multiple buttons on the same row.
Start a new line for each row of buttons you want to create.</b>

<i>Special Handlers</i> - <code>invite_link</code> (to show invite link to your group chat as a button), <code>rules</code>(create a rules button that shows rules message if previously set)
Put special handlers in your button text. but remember to separate them with "|" if the raw has other buttons

<i>Example:</i>

<b>Button1 Label - https://link1.com | Button2 Label - https://link2.com
Button3 Label - https://link3.com | rules
invite_link</b>

<i>This format will generate three buttons in total:

Two buttons on the top row.
One button on the bottom row.
You can add as many buttons as you need using this format to enhance your welcome messages and guide users effectively. 🌟</i>""", parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)
    context.user_data['wlc_msg_message_id'] = msg.message_id

def handle_set_topic(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    user_id = query.from_user.id
    chat = context.bot.get_chat(chat_id)
    chat_name = chat.title

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'welcomer'})
    current_topic = doc['topic_id'] if doc and 'topic_id' in doc else "No Topic Was Set Before"

    response_text = (
        f"⭕ Currently Engaging on: <code>{chat_name}</code>\n\n"
        f"📝 Now Send your group topic link that you want to send welcome message when a user joins the group.<i>⚠️ This option is totally optional and if your group didn't enable topics, ignore this option</i>\n\n"
        f"🌲 Current Setup Topic: <code>{current_topic}</code>"
    )

    context.user_data['awaiting_topic'] = {'chat_id': chat_id, 'user_id': user_id}
    context.user_data['awt_wlc_topic'] = True
    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")],
        [InlineKeyboardButton("♻️ Delete", callback_data=f"delete_welcome_entry-topic{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = query.edit_message_text(
        text=response_text,
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_markup
    )
    context.user_data['wlc_msg_message_id'] = msg.message_id

def receive_user_inputs(update: Update, context: CallbackContext):
    if context.user_data.get('awt_wlc_text'):
        user_data = context.user_data.get('awaiting_text', {})
        if update.message.from_user.id == user_data['user_id']:
            text = update.message.text
            collection = db[str(user_data['chat_id'])]

            collection.update_one(
                {'identifier': 'welcomer'},
                {'$set': {'welcome_msg': text}},
                upsert=True
            )
            logger.info(f"New Welcome Message Saved for [{user_data['chat_id']}]")
        
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            context.user_data.pop('awaiting_text', None)
            context.user_data.pop('awt_wlc_text')  

            welcomer_setup_callback(update, context)

    elif context.user_data.get('awt_wlc_media'):
        user_data = context.user_data.get('awaiting_media', {})
        if update.message.from_user.id == user_data['user_id']:
            media = None
            f_type = None
            if update.message.photo:
                media = update.message.photo[-1] 
                f_type = "photo"
            elif update.message.video:
                media = update.message.video
                f_type = "video"
            elif update.message.document:
                media = update.message.document
                f_type = "document"
            elif update.message.audio:
                media = update.message.audio
                f_type = "audio"
            elif update.message.animation:
                media = update.message.animation
                f_type = "document"

            if media:
                file_id = media.file_id
                collection = db[str(user_data['chat_id'])]

            collection.update_one(
                {'identifier': 'welcomer'},
                {'$set': {'media_id': file_id, 'media_type': f_type}},
                upsert=True
            )
            logger.info(f"New Welcome Media Saved for [{user_data['chat_id']}]")

            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            context.user_data.pop('awaiting_media', None)
            context.user_data.pop('awt_wlc_media')  

            welcomer_setup_callback(update, context)

    elif context.user_data.get('awt_wlc_buttons'):
        user_data = context.user_data.get('awaiting_buttons', {})
        if update.message.from_user.id == user_data['user_id']:
            text = update.message.text
            collection = db[str(user_data['chat_id'])]

            collection.update_one(
                {'identifier': 'welcomer'},
                {'$set': {'welcome_buttons': text}},
                upsert=True
            )
            logger.info(f"New Welcome Buttons Saved for [{user_data['chat_id']}]")
        
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            context.user_data.pop('awaiting_buttons', None)
            context.user_data.pop('awt_wlc_buttons')  

            welcomer_setup_callback(update, context)

    elif context.user_data.get('awt_wlc_topic'):
        link = update.message.text
        user_data = context.user_data.get('awaiting_topic', {})

        try:
            if "/c/" in link:
                parts = link.split('/')
                topic_id = parts[-1]
                chat_id_from_link = "-100" + parts[-2]
            else:
                parts = link.split('/')
                topic_id = parts[-1]
                username_from_link = parts[-2]

                chat = context.bot.get_chat(chat_id=f"@{username_from_link}")
                chat_id_from_link = chat.id if chat else None

            original_chat_id = user_data['chat_id']

            if str(chat_id_from_link) != str(original_chat_id):
                update.message.reply_text(
                    "⚠️ The chat identifier in the provided link does not match the current editing group ID. Please recheck your topic link!",
                    parse_mode=ParseMode.HTML)
                return
            
            collection = db[str(original_chat_id)]
            collection.update_one(
                {'identifier': 'welcomer'},
                {'$set': {'topic_id': topic_id}},
                upsert=True
            )
            logger.info(f"New Welcome Topic Saved for [{user_data['chat_id']}]")

            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            context.user_data.pop('awaiting_topic', None)  
            context.user_data.pop('awt_wlc_topic') 

            welcomer_setup_callback(update, context)

        except Exception as e:
            logger.error(f"Failed to process topic link: {e}")
            update.message.reply_text("Failed to process the topic link. Please try again.")

def handle_see_welcome_text(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]
    
    doc = collection.find_one({'identifier': 'welcomer'})
    if doc and 'welcome_msg' in doc:
        keyboard = [[InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=f"🛡️ Current welcome message;\n\n{doc['welcome_msg']}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        query.answer("No config for this chat", show_alert=True)

def handle_see_welcome_media(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    user_id = query.from_user.id
    collection = db[str(chat_id)]
    
    doc = collection.find_one({'identifier': 'welcomer'})
    if doc and 'media_id' in doc and 'media_type' in doc:
        file_id = doc['media_id']
        media_type = doc['media_type']
        keyboard = [[InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if media_type == 'photo': 
            context.bot.send_photo(chat_id=user_id, photo=file_id, caption="🛡️ Here's the current welcome media that send along with welcome message.", reply_markup=reply_markup)
        elif media_type == 'video':
            context.bot.send_video(chat_id=user_id, video=file_id, caption="🛡️ Here's the current welcome media that send along with welcome message.", reply_markup=reply_markup)
        elif media_type == 'audio':
            context.bot.send_audio(chat_id=user_id, audio=file_id, caption="🛡️ Here's the current welcome media that send along with welcome message.", reply_markup=reply_markup)
        else:  
            context.bot.send_document(chat_id=user_id, document=file_id, caption="🛡️ Here's the current welcome media that send along with welcome message", reply_markup=reply_markup, parse_mode=ParseMode.HTML)        
        
        query.delete_message() 
        
    else:
        query.answer("No config for this chat", show_alert=True)

def handle_see_welcome_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]

    doc = collection.find_one({'identifier': 'welcomer'})
    if doc and 'welcome_buttons' in doc:
        button_text = doc['welcome_buttons']
        
        rows = button_text.split('\n') 
        keyboard = []
        for row in rows:
            buttons = row.split(' | ')
            button_list = []
            for btn in buttons:
                parts = btn.split(' - ')
                if len(parts) == 2:
                    button_list.append(InlineKeyboardButton(parts[0], url=parts[1]))
                elif btn.strip().lower() == 'rules':
                    rules_button = InlineKeyboardButton("⚜️Rules ⚜️", url=f"https://t.me/{context.bot.username}?start=show_rules_{chat_id}")
                    button_list.append(rules_button)
                elif btn.strip().lower() == 'invite_link':
                    try:
                        invite_link = context.bot.create_chat_invite_link(chat_id=chat_id)
                        invite_button = InlineKeyboardButton(f"{context.bot.get_chat(chat_id).title}", url=invite_link.invite_link)
                        button_list.append(invite_button)
                    except Exception as e:
                        logger.error(f"Failed to create invite link for chat {chat_id}. Error: {e}")
                        continue

            if button_list:
                keyboard.append(button_list)

        keyboard.append([InlineKeyboardButton("🔙 Back 🔙", callback_data="welcomer_back_to_main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text=f"🛡️ Current welcome message buttons configuration:\n\n<code>{button_text}</code>", reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        query.answer("No config for this chat", show_alert=True)
        
def activate_welcomer(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]
    collection.update_one({'identifier': 'welcomer'}, {'$set': {'welcomer_state': True}}, upsert=True)
    welcomer_setup_callback(update, context)  

def deactivate_welcomer(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]
    collection.update_one({'identifier': 'welcomer'}, {'$set': {'welcomer_state': False}}, upsert=True)
    welcomer_setup_callback(update, context) 

def toggle_pm(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'welcomer'})

    current_state = False
    
    if doc:
        current_state = doc.get('set_pm', False)
    
    new_state = not current_state
    collection.update_one(
        {'identifier': 'welcomer'},
        {'$set': {'set_pm': new_state}},
        upsert=True
    )
    logger.info(f"Welcomer PM Send Status Changed to {new_state} in [{chat_id}]")
    
    query.answer(f"Send in PM is now {'Enabled' if new_state else 'Disabled'}", show_alert=True)
    welcomer_setup_callback(update, context)

def display_welcome_dashboard(update: Update, context: CallbackContext):
    chat_id = context.user_data['wlc_chat_id']
    chat = context.bot.get_chat(chat_id)
    chat_name = chat.title

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'welcomer'})

    if doc is None:
        logger.info(f"No welcomer config document found for chat_id {chat_id}. Using default settings.")
        welcomer_state = False
        send_in_pm = False
        wlc_msg_stats = "❌"
        wlc_media_stats = "❌"
        wlc_buttons_stats = "❌"
        wlc_topic_stats = "❌"
    else:
        welcomer_state = doc.get('welcomer_state', False)
        send_in_pm = doc.get('set_pm', False) if doc else False
        wlc_msg_stats = "✅" if doc.get('welcome_msg', False) else "❌"
        wlc_media_stats = "✅" if doc.get('media_id', False) else "❌"
        wlc_buttons_stats = "✅" if doc.get('welcome_buttons', False) else "❌"
        wlc_topic_stats = "✅" if doc.get('topic_id', False) else "❌"
    
    state_button = InlineKeyboardButton("❌ Deactivate Welcomer", callback_data=f"deactivate_welcomer_{chat_id}") if welcomer_state else InlineKeyboardButton("✅ Activate Welcomer", callback_data=f"activate_welcomer_{chat_id}")
    pm_button = InlineKeyboardButton("Send in PM 📨 [✅]", callback_data=f"wlc_toggle_pm_{chat_id}") if send_in_pm else InlineKeyboardButton("Send in PM 📨 [❌]", callback_data=f"wlc_toggle_pm_{chat_id}")
    status_text = "Activated" if welcomer_state else "Deactivated"
    send_in_pm_ststs = "✅" if send_in_pm else "❌"

    context.user_data.pop('awt_wlc_text', None)
    context.user_data.pop('awt_wlc_media', None)
    context.user_data.pop('awt_wlc_buttons', None) 
    context.user_data.pop('awt_wlc_topic', None) 
    context.user_data.pop('awaiting_text', None)
    context.user_data.pop('awaiting_media', None)
    context.user_data.pop('awaiting_buttons', None)
    context.user_data.pop('awaiting_topic', None)
    
    keyboard = [
        [InlineKeyboardButton("✍️ Text", callback_data=f"set_welcome_text_{chat_id}"),
         InlineKeyboardButton("👁️ See", callback_data=f"see_welcome_text_{chat_id}")],
        [InlineKeyboardButton("📸 Media", callback_data=f"set_welcome_media_{chat_id}"),
         InlineKeyboardButton("👁️ See", callback_data=f"see_welcome_media_{chat_id}")],
        [InlineKeyboardButton("🔘 URL Buttons", callback_data=f"set_welcome_buttons_{chat_id}"),
         InlineKeyboardButton("👁️ See", callback_data=f"see_welcome_buttons_{chat_id}")],
        [InlineKeyboardButton("📌 Set a Topic", callback_data=f"set_welcome_topic_{chat_id}"), pm_button],
        [state_button, InlineKeyboardButton("🪻 Preview a Snapshot", callback_data=f"preview_welcome_message_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"grd_back_to_primary_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"❄️ Setup a custom welcome message for your <code>{chat_name}</code> group\n\n⚡ Feature Status: <code>{status_text}</code>\n\n<i>Welcome Message</i>: {wlc_msg_stats}\n<i>Welcome Media</i>: {wlc_media_stats}\n<i>Welcome Buttons</i>: {wlc_buttons_stats}\n<i>Topic Enabled</i>: {wlc_topic_stats}\n<i>Send in PM too</i>: {send_in_pm_ststs}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    query.delete_message()

def delete_welcome_entry(update: Update, context: CallbackContext):
    query = update.callback_query
    parts = query.data.split('-')
    if len(parts) < 3:
        logger.error("Callback data is malformed: " + query.data)
        query.answer("An error occurred. Please try again.", show_alert=True)
        return

    action = parts[1]
    chat_id = "-" + parts[2]  

    entry_map = {
        'text': 'welcome_msg',
        'media': {'media_id': "", 'media_type': ""},
        'buttons': 'welcome_buttons',
        'topic': 'topic_id'
    }

    entry_to_delete = entry_map.get(action)
    if not entry_to_delete:
        logger.error("Invalid action specified: " + action)
        query.answer("Invalid operation requested.", show_alert=True)
        return

    collection = db[str(chat_id)]
    if isinstance(entry_to_delete, dict):
        update_action = {'$unset': entry_to_delete}
    else:
        update_action = {'$unset': {entry_to_delete: ""}}

    collection.update_one({'identifier': 'welcomer'}, update_action)
    query.answer(f"{action.capitalize()} Deleted ♻️", show_alert=True)
    display_welcome_dashboard(update, context)

def setup_welcomer(dp):
    dp.add_handler(CallbackQueryHandler(welcomer_setup_callback, pattern=r"^set_welcomer_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_set_text, pattern=r"^set_welcome_text_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_set_media, pattern=r"^set_welcome_media_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_set_buttons, pattern=r"^set_welcome_buttons_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_see_welcome_text, pattern=r"^see_welcome_text_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_see_welcome_media, pattern=r"^see_welcome_media_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_see_welcome_buttons, pattern=r"^see_welcome_buttons_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_set_topic, pattern=r"^set_welcome_topic_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(display_welcome_dashboard, pattern="welcomer_back_to_main_menu"))
    dp.add_handler(CallbackQueryHandler(activate_welcomer, pattern=r"^activate_welcomer_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(deactivate_welcomer, pattern=r"^deactivate_welcomer_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(delete_welcome_entry, pattern=r"^delete_welcome_entry-\w+-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(preview_welcome_message, pattern=r"^preview_welcome_message_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(toggle_pm, pattern=r"^wlc_toggle_pm_-(\d+)$"))
    dp.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.CHAT_MEMBER), group=16)
    dp.add_handler(MessageHandler(Filters.all & Filters.chat_type.private & ~Filters.command, receive_user_inputs), group=17)
