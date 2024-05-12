# super_plugins/guardian/captcha/captcha.py
import os
import re
from loguru import logger
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, Filters

from super_plugins.guardian.captcha.captcha_logic import setup_captcha_logic_handlers

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']

def captcha_menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        chat_id = query.data.split('_')[-1]
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
    
    else:
        chat = context.user_data.get('cpt_chat_info')
        chat_id = chat.id
    
    collection = db[str(chat_id)]
    group_details = collection.find_one({'identifier': 'captcha'})
    
    if group_details:
        captcha_status = group_details.get('captcha_stats', False) if group_details else False
        cpt_mode = "✅" if group_details.get('captcha_mode', False) else "❌"
        topic_id = "✅" if group_details.get('topic_id', False) else "❌"
        cpt_message = "✅" if group_details.get('captcha_message', False) else "❌"
        cpt_media = "✅" if group_details.get('captcha_media_id', False) else "❌"
        cpt_button_info = "✅" if group_details.get('captcha_buttons_info', False) else "❌"
        cpt_punishment = "✅" if group_details.get('punishment', False) else "❌"
        cpt_punishment_time = "✅" if group_details.get('punishment_time', False) else "❌"
        no_cpt_for_added_users = "❌" if group_details.get('no_cpt_for_added_users', True) else "✅"
        no_cpt_for_added_users_btn_stats = group_details.get('no_cpt_for_added_users', True)
    else:
        captcha_status = False
        cpt_mode = "❌"
        topic_id = "❌"
        cpt_message = "❌"
        cpt_media = "❌"
        cpt_button_info = "❌"
        cpt_punishment = "❌"
        cpt_punishment_time = "❌"
        no_cpt_for_added_users = "❌"
        no_cpt_for_added_users_btn_stats = True

    cpt_status_text = "Activated" if captcha_status else "Deactivated"
    captcha_status_text = "Deactivate Captcha ❌" if captcha_status else "Activate Captcha ✅"
    no_cpt_for_added_users_str = "Enable Captcha for Invited Users ✅" if no_cpt_for_added_users_btn_stats else "Disable Captcha for Invited Users ❌"

    keyboard = [
        [InlineKeyboardButton("Mode ⚙️", callback_data=f"toggle_captcha_mode_{chat_id}"), InlineKeyboardButton("Setup a Topic 📌", callback_data=f"cpth_setup_topic_{chat_id}")],
        [InlineKeyboardButton(f"Punishment 💥", callback_data=f"cpt_set_punishment_{chat_id}"), InlineKeyboardButton("Customize Message 🎨🖌️", callback_data=f"customize_captcha_message_{chat_id}")],
        [InlineKeyboardButton(f"{no_cpt_for_added_users_str}", callback_data=f"toggle_cpt_status_for_add_users_{chat_id}")],
        [InlineKeyboardButton(f"{captcha_status_text}", callback_data=f"toggle_captcha_status_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"grd_back_to_primary_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        query.edit_message_text(f"🛡️ Captcha Verify System for your <code>{chat.title}</code> group\n\n<i>Protection from spammers and trojan bots</i>\n\n⚡ Feature Status: <code>{cpt_status_text}</code>\n\n<i>Captcha Mode</i>: {cpt_mode}\n<i>Topic ID</i>: {topic_id}\n<i>Captcha Message</i>: {cpt_message}\n<i>Captcha Message Media</i>: {cpt_media}\n<i>Captcha Message Buttons</i>: {cpt_button_info}\n<i>Captcha Punishment</i>: {cpt_punishment}\n<i>Punishment Time</i>: {cpt_punishment_time}\n<i>Captcha for Invited Users</i>: {no_cpt_for_added_users}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        need_to_edit_msg_id = context.user_data['need_to_edit_msg_id_cpt']
        context.bot.edit_message_text(chat_id=update.message.chat_id, text=f"🛡️ Captcha Verify System for your <code>{chat.title}</code> group\n\n<i>Protection from spammers and trojan bots</i>\n\n⚡ Feature Status: <code>{cpt_status_text}</code>\n\n<i>Captcha Mode</i>: {cpt_mode}\n<i>Topic ID</i>: {topic_id}\n<i>Captcha Message</i>: {cpt_message}\n<i>Captcha Message Media</i>: {cpt_media}\n<i>Captcha Message Buttons</i>: {cpt_button_info}\n<i>Captcha Punishment</i>: {cpt_punishment}\n<i>Punishment Time</i>: {cpt_punishment_time}\n<i>Captcha for Invited Users</i>: {no_cpt_for_added_users}", reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg_id)

    context.user_data.pop('cpt_expecting_topic_link', None)
    context.user_data.pop('cpt_chat_info', None)
    context.user_data.pop('need_to_edit_msg_id_cpt', None)

def has_required_permissions(member):
    if member.status == 'creator':
        return True
    required_permissions = ['can_change_info', 'can_delete_messages', 'can_restrict_members', 'can_invite_users']
    return all(getattr(member, perm, False) for perm in required_permissions)

def captcha_toggle_mode_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    collection = db[str(chat_id)]

    group_details = collection.find_one({'identifier': 'captcha'})
    current_mode = group_details.get('captcha_mode', 'not_set') if group_details else 'not_set'

    if current_mode == "rule_accept":
        current_mode = "rule-accept"

    mode_labels = {
        'button': 'Button',
        'math': 'Math',
        'rule-accept': 'Rule Acceptation',
        'recaptcha': 'Recaptcha',
        'quiz': 'Quiz'
    }

    buttons = []
    row = []
    for index, (mode_key, mode_label) in enumerate(mode_labels.items()):
        label = mode_label
        if mode_key == current_mode:
            label += " [✅]"
        data = f"captcha_{mode_key}_{chat_id}"
        row.append(InlineKeyboardButton(label, callback_data=data))
        if (index + 1) % 2 == 0 or index == len(mode_labels) - 1:
            buttons.append(row)
            row = []

    row.append(InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_menu_{chat_id}"))
    buttons.append(row)
    reply_markup = InlineKeyboardMarkup(buttons)
    selected_mode = mode_labels.get(current_mode, 'Not Setup').capitalize() if current_mode != 'not_set' else "Not Setup"
    query.edit_message_text(
        f"⭕ Currently Engaging on: <code>{chat.title}</code>\n\n🎲 Choose a method to activate Captcha for your chat:\n\n<b><i>Captcha Mode</i></b>: <code>{selected_mode}</code>",
        reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )

def update_captcha_setting(chat_id, selected_mode):
    collection = db[str(chat_id)]
    if selected_mode == "rule-accept":
        selected_mode = "rule_accept"
        
    collection.update_one(
        {'identifier': 'captcha'},
        {'$set': {'captcha_mode': selected_mode}},
        upsert=True
    )
    logger.info(f"'{selected_mode}' Saved as Captcha Mode for [{chat_id}]")

def captcha_mode_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    mode, chat_id = query.data.split('_')[1], query.data.split('_')[-1]
    collection = db[str(chat_id)]
    group_details = collection.find_one({'identifier': 'captcha'})
    chat = context.bot.get_chat(chat_id)
    button_text_mapping = {
        "button": "Button",
        "math": "Math",
        "rule-accept": "Rule Acceptation",
        "recaptcha": "Recaptcha",
        "quiz": "Quiz"
    }
    
    selected_mode = button_text_mapping.get(mode)
    if selected_mode:
        mode_for_compare = 'rule_accept' if mode == 'rule-accept' else mode
        if group_details and group_details.get('captcha_mode', None) == mode_for_compare:
            query.answer(f"{selected_mode.upper()} Captcha Already Activated! ✔️", show_alert=True)
            return
        else:
            update_captcha_setting(chat_id, mode)
            
        if mode == 'button':
            query.answer(f"Button Captcha Activated!\n\n🔴 Difficulty Level: Very Low 🍃🍂", show_alert=True)
        elif mode == 'rule-accept': 
            query.answer(f"Rule Acceptation Captcha Activated!\n\n🔴 Difficulty Level: Low 🪶", show_alert=True)
        elif mode == 'math': 
            query.answer(f"Math Captcha Activated!\n\n🔴 Difficulty Level: Low to Medium ⚖️", show_alert=True)
        elif mode == 'recaptcha':
            query.answer(f"ReCaptcha Activated!\n\n🔴 Difficulty Level: Medium to Very High 🌶", show_alert=True)
        elif mode == 'quiz':
            query.answer(f"Quiz Captcha Activated!\n\n🔴 Difficulty Level: Medium to High 🔥", show_alert=True)
        
        keyboard = [
            [InlineKeyboardButton("Button [✅]" if mode == "button" else "Button", callback_data=f"captcha_button_{chat_id}"),
             InlineKeyboardButton("Math [✅]" if mode == "math" else "Math", callback_data=f"captcha_math_{chat_id}")],
            [InlineKeyboardButton("Rule Acceptation [✅]" if mode == "rule-accept" else "Rule Acceptation", callback_data=f"captcha_rule-accept_{chat_id}"),
             InlineKeyboardButton("Recaptcha [✅]" if mode == "recaptcha" else "Recaptcha", callback_data=f"captcha_recaptcha_{chat_id}")],
            [InlineKeyboardButton("Quiz [✅]" if mode == "quiz" else "Quiz", callback_data=f"captcha_quiz_{chat_id}")],
            [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_menu_{chat_id}")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(f"⭕ Currently Engaging on: <code>{chat.title}</code>\n\n🎲 Choose a method to activate Captcha for your chat:\n\n<b><i>Captcha Mode</i></b>: <code>{selected_mode}</code>",
                                reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def toggle_captcha_status(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]

    group_details = collection.find_one({'identifier': 'captcha'})
    if group_details:
        current_status = group_details.get('captcha_stats', False) if group_details else False
    else:
        current_status = False
        
    new_status = not current_status

    collection.update_one(
        {'identifier': 'captcha'},
        {'$set': {'captcha_stats': new_status}},
        upsert=True
    )

    stats_lable = "Activated" if new_status else "Deactivated"
    logger.info(f"Captcha {stats_lable} for [{chat_id}]")
    query.answer(f"Captcha {stats_lable} ✅", show_alert=True)
    captcha_menu_callback(update, context)

def toggle_captcha_status_for_invited_users(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]

    group_details = collection.find_one({'identifier': 'captcha'})
    
    if group_details:
        current_status_for_invited_users = group_details.get('no_cpt_for_added_users', True)
    else:
        current_status_for_invited_users = True
        
    new_status_for_invited_users = not current_status_for_invited_users

    if new_status_for_invited_users:
        query.answer(f"Now, invited users (those who are added to the group by existing members) will not have to face the captcha challenge ✅", show_alert=True)
    else:
        query.answer(f"Now, invited users (those who are added to the group by existing members) will have to face the captcha challenge ✅", show_alert=True)

    collection.update_one(
        {'identifier': 'captcha'},
        {'$set': {'no_cpt_for_added_users': new_status_for_invited_users}},
        upsert=True
    )

    stats_lable = "Activated" if new_status_for_invited_users else "Deactivated"
    logger.info(f"Captcha Status for Invited Users {stats_lable} for [{chat_id}]")
    captcha_menu_callback(update, context)

def setup_topic_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    
    context.user_data['cpt_expecting_topic_link'] = True
    context.user_data['cpt_chat_info'] = chat

    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    if doc:
        topic_id = doc.get('topic_id', 'Not Set')
    else:
        topic_id = 'Not Set'
    
    msg = query.edit_message_text(
        text=f"⭕ Currently Engaging on: <code>{chat.title}</code>\n\nSend a Topic link of your <code>{chat.title}</code> to send captcha message to specific topic.\n\n<code>This setting is optional. If your group didn't activate topics, no need to setup this</code>\n\n<i>Current Topic ID</i>: <code>{topic_id}</code>",
        parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )
    context.user_data['need_to_edit_msg_id_cpt'] = msg.message_id

def message_handler(update: Update, context: CallbackContext):
    message = update.message
    if 'cpt_chat_info' in context.user_data and context.user_data.get('cpt_expecting_topic_link'):
        chat = context.user_data.get('cpt_chat_info')
        chat_name = chat.title
        chat_id = chat.id
        link = message.text
        pattern = r"https://t.me/(c/)?([\w-]+)/(\d+)"
        match = re.match(pattern, link)
        
        if match:
            if match.group(1) == 'c/':
                if str(chat_id) == f"-100{match.group(2)}":
                    store_topic_id(context, chat_id, match.group(3))
                    
                    try:
                        update.message.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete message: {e}")
                    
                    captcha_menu_callback(update, context)
                else:
                    message.reply_text(f"Mismatched Chat ID With Your <code>{chat_name}</code>. Please check the link and try again.", parse_mode=ParseMode.HTML)
            else:
                if chat.username == match.group(2):
                    store_topic_id(context, chat_id, match.group(3))

                    try:
                        update.message.delete()
                    except Exception as e:
                        logger.error(f"Failed to delete message: {e}")
                    
                    captcha_menu_callback(update, context)
                else:
                    message.reply_text(f"Mismatched Group Username With Your <code>{chat_name}</code>. Please check the link and try again.", parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Invalid link format. Please send a valid topic link.")

    elif 'cpt_chat_info' in context.user_data and context.user_data.get('expecting_captcha_text'):
        chat = context.user_data.get('cpt_chat_info')
        chat_id = chat.id
        collection = db[str(chat_id)]
        custom_text = message.text
        collection.update_one({'identifier': 'captcha'}, {'$set': {'captcha_message': custom_text}}, upsert=True)
        logger.info(f"Captcha Message Text info updated in [{chat_id}]")
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        customize_captcha_message_callback(update, context)

    elif 'cpt_chat_info' in context.user_data and context.user_data.get('expecting_captcha_media'):
        chat = context.user_data.get('cpt_chat_info')
        chat_id = chat.id
        collection = db[str(chat_id)]
        media_type, file_id = None, None
        if message.photo:
            media_type = 'photo'
            file_id = message.photo[-1].file_id
        elif message.video:
            media_type = 'video'
            file_id = message.video.file_id
        elif message.document:
            media_type = 'document'
            file_id = message.document.file_id
        elif message.audio:
            media_type = 'audio'
            file_id = message.audio.file_id

        if file_id:
            collection.update_one({'identifier': 'captcha'}, {'$set': {'captcha_media_id': file_id, 'captcha_media_type': media_type}}, upsert=True)
            logger.info(f"Captcha Message Media info updated in [{chat_id}]")
            try:
                update.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
            customize_captcha_message_callback(update, context)
        else:
            message.reply_text("Please send a supported media type (photo, video, document, audio).")

    elif 'cpt_chat_info' in context.user_data and context.user_data.get('expecting_captcha_buttons'):
        chat = context.user_data.get('cpt_chat_info')
        chat_id = chat.id
        collection = db[str(chat_id)]
        buttons_info = message.text
        collection.update_one({'identifier': 'captcha'}, {'$set': {'captcha_buttons_info': buttons_info}}, upsert=True)
        logger.info(f"Captcha Message Button info updated in [{chat_id}]")
        try:
            update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        customize_captcha_message_callback(update, context)

def store_topic_id(context, chat_id, topic_id):
    collection = db[str(chat_id)]
    collection.update_one(
        {'identifier': 'captcha'},
        {'$set': {'topic_id': topic_id}},
        upsert=True
    )
    logger.info(f"New Captcha Topic ID Saved for [{chat_id}]")

def customize_captcha_message_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        chat_id = query.data.split('_')[-1]
        chat = context.bot.get_chat(chat_id)
        cpt_second_rply_msg_id = context.user_data.get('cpt_second_rply_msg_id', None)
        user_id = context.user_data.get('cpt_user_id_need_for_del', None)
    else:
        chat = context.user_data.get('cpt_chat_info')
        chat_id = chat.id
        cpt_second_rply_msg_id = context.user_data.get('cpt_second_rply_msg_id', None)
        user_id = context.user_data.get('cpt_user_id_need_for_del', None)
        
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})

    if doc:
        cpt_message = "✅" if doc.get('captcha_message', False) else "❌"
        cpt_media = "✅" if doc.get('captcha_media_id', False) else "❌"
        cpt_buttons = "✅" if doc.get('captcha_buttons_info', False) else "❌"
    else:
        cpt_message = "❌"
        cpt_media = "❌"
        cpt_buttons = "❌"

    keyboard = [
        [InlineKeyboardButton("Text 📝", callback_data=f"set_captcha_text_{chat_id}")],
        [InlineKeyboardButton("Media 🖼️", callback_data=f"set_captcha_media_{chat_id}")],
        [InlineKeyboardButton("Buttons 🔘", callback_data=f"set_captcha_buttons_{chat_id}")],
        [InlineKeyboardButton("♻️ Delete", callback_data=f"delete_captcha_message_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        query.edit_message_text(f"🌀 Setup Custom Captcha Message for <code>{chat.title}</code>\n\n<i>Captcha Message</i>: {cpt_message}\n<i>Captcha Media</i>: {cpt_media}\n<i>Captcha Message Buttons</i>: {cpt_buttons}", reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        need_to_edit_msg_id = context.user_data['need_to_edit_msg_id_cpt']
        context.bot.edit_message_text(chat_id=update.message.chat_id, text=f"🌀 Setup Custom Captcha Message for <code>{chat.title}</code>\n\n<i>Captcha Message</i>: {cpt_message}\n<i>Captcha Media</i>: {cpt_media}\n<i>Captcha Message Buttons</i>: {cpt_buttons}", reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_id=need_to_edit_msg_id)
    
    if cpt_second_rply_msg_id is not None and user_id is not None:
        context.bot.delete_message(chat_id=user_id, message_id=cpt_second_rply_msg_id)
    
    context.user_data.pop('cpt_chat_info', None)
    context.user_data.pop('need_to_edit_msg_id_cpt', None)
    context.user_data.pop('expecting_captcha_text', None)
    context.user_data.pop('expecting_captcha_media', None)
    context.user_data.pop('expecting_captcha_buttons', None)
    context.user_data.pop('cpt_second_rply_msg_id', None)
    context.user_data.pop('cpt_user_id_need_for_del', None)

def delete_captcha_msg_entry(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]

    collection = db[str(chat_id)]
    keys_to_delete = ['captcha_message', 'captcha_media_id', 'captcha_media_type', 'captcha_buttons_info']
    update_action = {'$unset': {key: 1 for key in keys_to_delete}}

    collection.update_one({'identifier': 'captcha'}, update_action)
    logger.info(f"Captcha Message is deleted in [{chat_id}]")
    query.answer(f"Captcha Message Deleted ♻️", show_alert=True)
    customize_captcha_message_callback(update, context)

def set_captcha_text_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    context.user_data['cpt_chat_info'] = chat
    context.user_data['expecting_captcha_text'] = True
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    captcha_msg = doc.get('captcha_message', "Not Set") if doc else "Not Set"

    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_c_message_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = query.edit_message_text(
        text=f"""⭕ Currently Engaging on: <code>{chat.title}</code>.\n\n📝 Now Send a custom text for your group captcha message\n\nYou can use below custom handlers:\n\n<code>[id]\n[first_name]\n[second_name]\n[mention]\n[username]\n[time(timezone)]\n[date(timezone)]\n[group_name]\n[group_id]\n[admin_count]</code>\n\n<i>Also you can use HTML tags for formatting the message</i>\n\n<code>(&lt;b&gt, &lt;i&gt, &lt;u&gt, &lt;code&gt, &lt;tg-spoiler&gt)</code>\n\n<i>Hyper Links are also support too;</i>\nExample: <code>&lt;a href="https://www.example.com"&gt;Visit Example Website&lt;/a&gt;</code>\n\n<i>🌀 Current Message</i>: <code>{captcha_msg}</code>""",
        parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )
    context.user_data['need_to_edit_msg_id_cpt'] = msg.message_id

def set_captcha_media_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    context.user_data['cpt_chat_info'] = chat
    context.user_data['expecting_captcha_media'] = True
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    second_rply_msg_id = None
    if doc and 'captcha_media_id' in doc and 'captcha_media_type' in doc:
        file_id = doc['captcha_media_id']
        media_type = doc['captcha_media_type']

        if media_type == 'photo': 
            msg = context.bot.send_photo(chat_id=user_id, photo=file_id, caption="🛡️ Here's the current welcome media that send along with captcha message.")
        elif media_type == 'video':
            msg = context.bot.send_video(chat_id=user_id, video=file_id, caption="🛡️ Here's the current welcome media that send along with captcha message.")
        elif media_type == 'audio':
            msg = context.bot.send_audio(chat_id=user_id, audio=file_id, caption="🛡️ Here's the current welcome media that send along with captcha message.")
        else:  
            msg = context.bot.send_document(chat_id=user_id, document=file_id, caption="🛡️ Here's the current welcome media that send along with captcha message")  
    
        second_rply_msg_id = msg.message_id
        context.user_data['cpt_second_rply_msg_id'] = msg.message_id
        context.user_data['cpt_user_id_need_for_del'] = user_id
        
    keyboard = [
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_c_message_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = context.bot.send_message(
        text=f"⭕ Currently Engaging on: <code>{chat.title}</code>.\n\n📸 Now send me a media file to send along with the welcome message. <i>It can be anything; Video, Photo, Audio, Document</i>",
        chat_id=user_id, parse_mode=ParseMode.HTML, reply_markup=reply_markup, reply_to_message_id=second_rply_msg_id
    )
    query.delete_message() 
    context.user_data['need_to_edit_msg_id_cpt'] = msg.message_id

def set_captcha_buttons_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    context.user_data['cpt_chat_info'] = chat
    context.user_data['expecting_captcha_buttons'] = True
    button_text = "Not Set"
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    keyboard = []
    
    if doc and 'captcha_buttons_info' in doc:
        button_text = doc['captcha_buttons_info']

        rows = button_text.split('\n') 
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

    keyboard.append([InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_c_message_{chat_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = query.edit_message_text(
        text=f"""⭕ Currently Engaging on: <code>{chat.title}</code>.\n\n<i>🚀 Create Your Custom URL Button List for Captcha Messages. You can customize your captcha messages by adding URL buttons that link to various resources. Here's how you can format your button lists to make your messages more interactive and user-friendly:</i>

<i>Format Guide:</i>

<b>Use " - " to separate the button label and the URL link.
Use " | " to place multiple buttons on the same row.
Start a new line for each row of buttons you want to create.</b>

<i>Special Handlers</i> - <code>rules</code>(create a rules button that shows rules message if previously set)
Put special handlers in your button text. but remember to separate them with "|" if the raw has other buttons

<i>Example:</i>

<b>Button1 Label - https://link1.com | Button2 Label - https://link2.com
Button3 Label - https://link3.com | rules</b>

<i>This format will generate three buttons in total:

Two buttons on the top row.
One button on the bottom row.
You can add as many buttons as you need using this format to enhance your welcome messages and guide users effectively. 🌟</i>\n\n<i>Current Button Set</i>: <code>{button_text}</code>""",
        parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True
    )
    context.user_data['need_to_edit_msg_id_cpt'] = msg.message_id

def set_punishment_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    current_punishment = doc.get('punishment', "Not Set") if doc else "Not Set"

    keyboard = [
        [InlineKeyboardButton(f"Mute 🔇 {'[✅]' if current_punishment == 'Mute' else ''}", callback_data=f"punish_mute_{chat_id}"),
         InlineKeyboardButton(f"Kick 💨 {'[✅]' if current_punishment == 'Kick' else ''}", callback_data=f"punish_kick_{chat_id}")],
        [InlineKeyboardButton(f"Ban 🚫 {'[✅]' if current_punishment == 'Ban' else ''}", callback_data=f"punish_ban_{chat_id}"),
         InlineKeyboardButton(f"Nothing 🤷‍♂️ {'[✅]' if current_punishment == 'Nothing' else ''}", callback_data=f"punish_nothing_{chat_id}")],
        [InlineKeyboardButton("⪢ Select time to Solve ⌛ ⪡", callback_data=f"select_solve_time_{chat_id}")],
        [InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_captcha_menu_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=f"⭕ Currently Engaging on: <code>{chat.title}</code>.\n\n<b>Set a Punishment for those who failed to complete captcha within selected time in your group</b>\n\n<i>Current punishment</i>: <code>{current_punishment}</code>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def punish_mute_callback(update: Update, context: CallbackContext):
    process_punishment(update, context, "Mute")

def punish_kick_callback(update: Update, context: CallbackContext):
    process_punishment(update, context, "Kick")

def punish_ban_callback(update: Update, context: CallbackContext):
    process_punishment(update, context, "Ban")

def punish_nothing_callback(update: Update, context: CallbackContext):
    process_punishment(update, context, "Nothing")

def process_punishment(update: Update, context: CallbackContext, punishment_type):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    if doc:
        punishment = doc.get('punishment', "Do nothing") if doc else "Do nothing"
    else:
        punishment = None
    if punishment == punishment_type:
        query.answer(f"Punishment already set to {punishment_type}", show_alert=True)
    else:
        collection.update_one({'identifier': 'captcha'}, {'$set': {'punishment': punishment_type}}, upsert=True)
        logger.info(f"Captcha Punishment Changed to {punishment_type} in [{chat_id}]")
        query.answer(f"Punishment set to {punishment_type}", show_alert=True)
        set_punishment_callback(update, context)

def select_solve_time_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    chat = context.bot.get_chat(chat_id)
    doc = db[str(chat_id)].find_one({'identifier': 'captcha'})
    punishment = doc.get('punishment', "Do nothing") if doc else "Do nothing"
    current_time = doc.get('punishment_time', None)

    time_buttons = {
        5: "5 min",
        10: "10 min",
        30: "30 min",
        60: "1 h",
        120: "2 h",
        1440: "24 h",
        2880: "2 d"
    }

    keyboard = []
    temp_row = []

    for idx, (time, label) in enumerate(time_buttons.items()):
        check_mark = " [✅]" if current_time == time else ""
        button = InlineKeyboardButton(f"{label}{check_mark}", callback_data=f"set_time_{time}_{chat_id}")
        temp_row.append(button)
        if idx % 2 == 1 or idx == len(time_buttons) - 1:
            keyboard.append(temp_row)
            temp_row = []

    keyboard.append([InlineKeyboardButton("🔙 Back 🔙", callback_data=f"back_to_punishment_{chat_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=f"⭕ Currently Engaging on: <code>{chat.title}</code>.\n\n<b>Select a time for users to solve the captcha in your group</b>\n\n<i>Those who fail to solve the captcha will </i><code>{punishment}</code>.\n\n<i>Current set time</i>: <code>{current_time if current_time else 'Not Set'}</code>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def set_punishment_time_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    time_minutes = int(query.data.split('_')[-2])
    collection = db[str(chat_id)]
    doc = collection.find_one({'identifier': 'captcha'})
    time_for_pun = doc.get('punishment_time', "Not Set") if doc else "Not Set"

    if time_for_pun == time_minutes:
        query.answer(f"Punishment time already set to {time_minutes} minutes ⚠️", show_alert=True)
    else:
        collection.update_one(
            {'identifier': 'captcha'},
            {'$set': {'punishment_time': time_minutes}},
            upsert=True
        )
        logger.info(f"Captcha Complete Time Changed to {time_minutes} min in [{chat_id}]")
        query.answer(f"Punishment time set to {time_minutes} minutes ✅", show_alert=True)
        select_solve_time_callback(update, context)

def setup_captcha(dp):
    dp.add_handler(CallbackQueryHandler(captcha_menu_callback, pattern=r"^set_captcha_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(captcha_toggle_mode_callback, pattern=r"^toggle_captcha_mode_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(captcha_mode_callback, pattern=r"^captcha_.*_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(toggle_captcha_status, pattern=r"^toggle_captcha_status_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(toggle_captcha_status_for_invited_users, pattern=r"^toggle_cpt_status_for_add_users_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(captcha_menu_callback, pattern=r"^back_to_captcha_menu_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(setup_topic_callback, pattern=r"^cpth_setup_topic_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(customize_captcha_message_callback, pattern=r"^customize_captcha_message_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_captcha_text_callback, pattern=r"^set_captcha_text_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_captcha_media_callback, pattern=r"^set_captcha_media_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_captcha_buttons_callback, pattern=r"^set_captcha_buttons_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(customize_captcha_message_callback, pattern=r"^back_to_captcha_c_message_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_punishment_callback, pattern=r"^cpt_set_punishment_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(punish_mute_callback, pattern=r"^punish_mute_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(punish_kick_callback, pattern=r"^punish_kick_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(punish_ban_callback, pattern=r"^punish_ban_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(punish_nothing_callback, pattern=r"^punish_nothing_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(select_solve_time_callback, pattern=r"^select_solve_time_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_punishment_time_callback, pattern=r"^set_time_.*_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_punishment_callback, pattern=r"^back_to_punishment_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(delete_captcha_msg_entry, pattern=r"^delete_captcha_message_-(\d+)$"))
    dp.add_handler(MessageHandler(Filters.all & Filters.chat_type.private & ~Filters.command, message_handler), group=22)
    setup_captcha_logic_handlers(dp)
