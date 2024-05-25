from loguru import logger
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

from super_plugins.__int__ import db
from super_plugins.guardian.logger.logger_executor import log_linkgen_process_stats

def link_command(update: Update, context: CallbackContext):
    query = update.callback_query

    if not query:
        chat_type = update.message.chat.type
        if chat_type != "group" and chat_type != "supergroup":
            update.message.reply_text("This command can only be used in group chats. ‼️")
            return

        user_id = update.message.from_user.id
        chat_id = update.message.chat.id

        if not is_user_admin(context.bot, user_id, chat_id):
            need_to_rply_msg_id = update.message.message_id
            collection = db[str(chat_id)]
            link_data = collection.find_one({'identifier': 'invite_link'})
            if link_data and 'member_invite_link' in link_data:
                chat_name = update.message.chat.title
                context.bot.send_message(chat_id=chat_id, text=f"⚡ The Public Invite link for <code>{chat_name}</code>:\n\n<code>{link_data['member_invite_link']}</code>", reply_to_message_id=need_to_rply_msg_id, parse_mode=ParseMode.HTML)
            else:
                context.bot.send_message(chat_id=chat_id, text="⚠️ No public invite link has been set for this group.", reply_to_message_id=need_to_rply_msg_id)
            return

        chat_member = context.bot.get_chat_member(chat_id, user_id)
        if not chat_member.can_invite_users and chat_member.status != 'creator':
            update.message.reply_text("You do not have permission to invite users via links. ‼️")
            return

        bot_member = context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_invite_users:
            update.message.reply_text("The bot does not have permission to invite users via links. Please grant the necessary permissions and try again. ‼️")
            return

    else:
        user_id = context.user_data['link_gen_admin_id']
        chat_id = context.user_data['link_gen_chat_id']

    keyboard = [
        [InlineKeyboardButton("Set User Limit 👥", callback_data=f"link_gen_set_user_limit_{user_id}_{chat_id}"), InlineKeyboardButton("Set Expiry Date ⏳", callback_data=f"link_gen_set_expiry_date_{user_id}_{chat_id}")],
        [InlineKeyboardButton("Approval Mode ⛔", callback_data=f"link_gen_approval_mode_{user_id}_{chat_id}"), InlineKeyboardButton("Set a link for members 🫂", callback_data=f"link_gen_set_member_link_{user_id}_{chat_id}")],
        [InlineKeyboardButton("Create Link ✅", callback_data=f"link_gen_create_link_{user_id}_{chat_id}")],
        [InlineKeyboardButton("Close ❌", callback_data="link_gen_close_dashboard")]
    ]
    text = "🔗 Invite Link Generate Dashboard:\n"
    if 'user_limit' in context.user_data and context.user_data['user_limit']:
        text += f"\n<i>User Limit</i>: <code>{context.user_data['user_limit']}</code>"
    if 'expiry_time' in context.user_data and context.user_data['expiry_time']:
        text += f"\n<i>Expiry Time</i>: <code>{context.user_data['expiry_time']} seconds</code>"
    if 'link_gen_apr_mode' in context.user_data and context.user_data['link_gen_apr_mode']:
        text += f"\n<i>Approval Mode</i>: <code>ON</code>"
    else:
        text += f"\n<i>Approval Mode</i>: <code>OFF</code>"
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if 'link_gen_need_to_edit_id' in context.user_data:
        message_id = context.user_data['link_gen_need_to_edit_id']
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        context.user_data.pop('link_gen_need_to_edit_id', None)
    elif query:
        query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        context.user_data.pop('link_gen_admin_id', None)
        context.user_data.pop('link_gen_chat_id', None)
    else:
        update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def handle_user_limit(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("Back ↩️", callback_data=f"link_gen_back_to_dashboard_{autho_user_id}_{chat_id}")]
    ]
    msg = query.edit_message_text("Send a user limit for the invite link. After you provided count users join via the link, the link will expire. Range should be 1 to 99999", reply_markup=InlineKeyboardMarkup(keyboard))
    message_id_to_edit = msg.message_id
    context.user_data['link_gen_need_to_edit_id'] = message_id_to_edit
    context.user_data['awaiting_user_limit'] = True

def user_limit_received(update: Update, context: CallbackContext):
    if 'awaiting_user_limit' in context.user_data and context.user_data['awaiting_user_limit']:
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        if int(update.message.text) > 99999 and int(update.message.text) < 1:
            update.message.reply_text(text="⚠️ Number must be in 1 to 99999 range!")
            return
            
        user_limit = int(update.message.text)
        context.user_data['user_limit'] = user_limit
        
        if 'link_gen_apr_mode' in context.user_data:
            context.user_data.pop('link_gen_apr_mode', None)
        
        context.user_data.pop('awaiting_user_limit', None)
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        link_command(update, context)

def handle_set_expiry_date(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("5m", callback_data=f"link_gen_expiry_300_{autho_user_id}_{chat_id}"), InlineKeyboardButton("30m", callback_data=f"link_gen_expiry_1800_{autho_user_id}_{chat_id}"), InlineKeyboardButton("1h", callback_data=f"link_gen_expiry_3600_{autho_user_id}_{chat_id}"), InlineKeyboardButton("2h", callback_data=f"link_gen_expiry_7200_{autho_user_id}_{chat_id}")],
        [InlineKeyboardButton("5h", callback_data=f"link_gen_expiry_18000_{autho_user_id}_{chat_id}"), InlineKeyboardButton("10h", callback_data=f"link_gen_expiry_36000_{autho_user_id}_{chat_id}"), InlineKeyboardButton("24h", callback_data=f"link_gen_expiry_86400_{autho_user_id}_{chat_id}"), InlineKeyboardButton("1w", callback_data=f"link_gen_expiry_604800_{autho_user_id}_{chat_id}")],
        [InlineKeyboardButton("2w", callback_data=f"link_gen_expiry_1209600_{autho_user_id}_{chat_id}"), InlineKeyboardButton("1M", callback_data=f"link_gen_expiry_2592000_{autho_user_id}_{chat_id}"), InlineKeyboardButton("2M", callback_data=f"link_gen_expiry_5184000_{autho_user_id}_{chat_id}"), InlineKeyboardButton("6M", callback_data=f"link_gen_expiry_15552000_{autho_user_id}_{chat_id}")],
        [InlineKeyboardButton("Back ↩️", callback_data=f"link_gen_back_to_dashboard_{autho_user_id}_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("Set a time to expire the link:", reply_markup=reply_markup)

def set_expiry_time(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    user_id = query.from_user.id
    expiry_time = int(query.data.split('_')[-3])

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return
    
    context.user_data['expiry_time'] = expiry_time
    context.user_data['link_gen_admin_id'] = autho_user_id
    context.user_data['link_gen_chat_id'] = chat_id
    query.answer(f"Expiry time set to {expiry_time} seconds.")
    link_command(update, context)

def handle_approval_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return
    
    if 'user_limit' in context.user_data:
        context.user_data.pop('user_limit', None)
    current_state = context.user_data.get('link_gen_apr_mode', False)
    context.user_data['link_gen_apr_mode'] = not current_state
    
    context.user_data['link_gen_admin_id'] = autho_user_id
    context.user_data['link_gen_chat_id'] = chat_id
    
    link_command(update, context)

def handle_create_link(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split('_')[-1])
    autho_user_id = int(query.data.split('_')[-2])
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    params = {}
    if 'user_limit' in context.user_data:
        params['member_limit'] = context.user_data['user_limit']
    if 'expiry_time' in context.user_data:
        params['expire_date'] = int((datetime.now() + timedelta(seconds=context.user_data['expiry_time'])).timestamp())
    if 'link_gen_apr_mode' in context.user_data and context.user_data['link_gen_apr_mode']:
        params['creates_join_request'] = True

    invite_link = context.bot.create_chat_invite_link(chat_id=chat_id, name=f"{user_name}'s link", **params)
    user_for_log = context.bot.get_chat(autho_user_id)
    chat_for_log = context.bot.get_chat(chat_id)
    info_text = f"✅#New_Link_Generated\n\nA New Invite Link ({invite_link.invite_link[:-4]}...) generated for [<code>{chat_id}</code>] chat by [<code>{autho_user_id}</code>]"
    log_linkgen_process_stats(user_for_log, chat_for_log, info_text, context)
    invite_link_part = invite_link.invite_link.split("https://t.me/")[-1]

    try:
        revoke_button = InlineKeyboardButton("Revoke This Link ❌", callback_data=f"rlz_{autho_user_id}_{chat_id}_{invite_link_part}")
        set_public_button = InlineKeyboardButton("Set This Link as Public Link", callback_data=f"set_public_{autho_user_id}_{chat_id}_{invite_link_part}")
        reply_markup = InlineKeyboardMarkup([[revoke_button], [set_public_button]])

        context.bot.send_message(chat_id=user_id, text=f"Here is your invite link: {invite_link.invite_link}", disable_web_page_preview=True, reply_markup=reply_markup)
        logger.info(f"New Invite Link Created by [{autho_user_id}] for [{chat_id}] and received in PM🔗")
        query.answer("Get Link in Echo PM 📭", show_alert=True)
        query.message.delete()
    except Exception as e:
        revoke_button = InlineKeyboardButton("Revoke This Link ❌", callback_data=f"rlz_{autho_user_id}_{chat_id}_{invite_link_part}")
        set_public_button = InlineKeyboardButton("Set This Link as Public Link", callback_data=f"set_public_{autho_user_id}_{chat_id}_{invite_link_part}")
        reply_markup = InlineKeyboardMarkup([[revoke_button], [set_public_button]])

        query.edit_message_text(f"Here is your invite link: <tg-spoiler>{invite_link.invite_link}</tg-spoiler>", parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
        logger.info(f"New Invite Link Created by [{autho_user_id}] for [{chat_id}] and received in group chat 🔗")
        query.answer(f"Failed to send DM to the user. Error: {e}")

def handle_revoke_link(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    chat_id = int(data[2])
    autho_user_id = int(query.data.split('_')[1])
    invite_link_part = "_".join(data[3:])
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    invite_link = f"https://t.me/{invite_link_part}"

    try:
        context.bot.revoke_chat_invite_link(chat_id=chat_id, invite_link=invite_link)
        logger.info(f"[{autho_user_id}] revoked [{chat_id}] chat's ({invite_link[:-4]}...) link ❌")
        
        info_text = f"❌#Invite_Link_Revoked\n\n({invite_link[:-4]}...) Invite link of [<code>{chat_id}</code>] chat revoked by [<code>{autho_user_id}</code>]"
        
        collection = db[str(chat_id)]
        link_data = collection.find_one({'identifier': 'invite_link'})
        if link_data and link_data.get('member_invite_link') == invite_link:
            collection.update_one(
                {'identifier': 'invite_link'},
                {'$unset': {'member_invite_link': ""}}
            )
            info_text += f" | Since this link was also set as the public link for this chat, it has been deleted from the database."
            logger.info(f"Public Invite Link ({invite_link[:-4]}...) for [{chat_id}] deleted from the database ❌")
        
        user_for_log = context.bot.get_chat(autho_user_id)
        chat_for_log = context.bot.get_chat(chat_id)
        log_linkgen_process_stats(user_for_log, chat_for_log, info_text, context)
        
        query.answer("The invite link has been revoked successfully.", show_alert=True)
        query.edit_message_text("The invite link has been revoked successfully.")
    except Exception as e:
        logger.error(f"Failed to revoke the invite link: {e}")
        query.answer("Failed to revoke the invite link. Please try again.", show_alert=True)

def is_user_admin(bot, user_id, chat_id):
    chat_member = bot.get_chat_member(chat_id, user_id)
    return chat_member.status in ['administrator', 'creator']

def handle_set_member_link(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("Back ↩️", callback_data=f"link_gen_back_to_dashboard_{autho_user_id}_{chat_id}")]
    ]
    msg = query.edit_message_text("Send a valid invite link. This link will show when group members send /link command.", reply_markup=InlineKeyboardMarkup(keyboard))
    message_id_to_edit = msg.message_id
    context.user_data['link_gen_need_to_edit_id'] = message_id_to_edit
    context.user_data['awaiting_member_link'] = chat_id
    context.user_data['awaiting_member_link_user_id'] = autho_user_id

def member_link_received(update: Update, context: CallbackContext):
    if 'awaiting_member_link' in context.user_data:
        chat_id = context.user_data['awaiting_member_link']
        autho_user_id = context.user_data['awaiting_member_link_user_id']
        message_id = update.message.message_id
        invite_link = update.message.text

        if not invite_link.startswith("https://t.me/"):
            update.message.reply_text("⚠️ Please send a valid Telegram invite link starting with https://t.me/")
            return

        collection = db[str(chat_id)]
        collection.update_one(
            {'identifier': 'invite_link'},
            {'$set': {'member_invite_link': invite_link}},
            upsert=True
        )
        logger.info(f"Public Invite Link set for [{chat_id}] by [{update.message.from_user.id}] ✅")

        user_for_log = context.bot.get_chat(autho_user_id)
        chat_for_log = context.bot.get_chat(chat_id)
        info_text = f"🫂#Public_Invite_Link\n\n({invite_link[:-4]}...) Invite Link set as Public Link for [<code>{chat_id}</code>] chat by [<code>{autho_user_id}</code>]"
        log_linkgen_process_stats(user_for_log, chat_for_log, info_text, context)
        
        context.user_data.pop('awaiting_member_link', None)
        context.user_data.pop('awaiting_member_link_user_id', None)
        context.bot.delete_message(chat_id=update.message.chat_id, message_id=message_id)
        link_command(update, context)

def handle_set_public_link(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')
    autho_user_id = int(data[2])
    chat_id = int(data[3])
    invite_link_part = "_".join(data[4:])
    user_id = query.from_user.id

    if str(autho_user_id) != str(user_id):
        query.answer("Do not touch this!", show_alert=True)
        return

    invite_link = f"https://t.me/{invite_link_part}"

    try:
        collection = db[str(chat_id)]
        collection.update_one(
            {'identifier': 'invite_link'},
            {'$set': {'member_invite_link': invite_link}},
            upsert=True
        )
        logger.info(f"Public Invite Link set for [{chat_id}] by [{autho_user_id}] ✅")

        user_for_log = context.bot.get_chat(autho_user_id)
        chat_for_log = context.bot.get_chat(chat_id)
        info_text = f"🫂#Public_Invite_Link\n\n({invite_link[:-4]}...) Invite Link set as Public Link for [<code>{chat_id}</code>] chat by [<code>{autho_user_id}</code>]"
        log_linkgen_process_stats(user_for_log, chat_for_log, info_text, context)

        revoke_button = InlineKeyboardButton("Revoke This Link ❌", callback_data=f"rlz_{autho_user_id}_{chat_id}_{invite_link_part}")
        reply_markup = InlineKeyboardMarkup([[revoke_button]])
        
        query.answer("Public invite link has been set successfully.", show_alert=True)
        query.edit_message_text(text=f"Here is your invite link: {invite_link}", disable_web_page_preview=True, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to set the public invite link: {e}")
        query.answer("Failed to set the public invite link. Please try again.", show_alert=True)

def handle_back_to_dashboard(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.data.split('_')[-1]
    autho_user_id = query.data.split('_')[-2]
    
    context.user_data['link_gen_admin_id'] = autho_user_id
    context.user_data['link_gen_chat_id'] = chat_id
    
    link_command(update, context)

def handle_close_dashboard(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data.clear()
    query.message.delete()

def setup_link_gen(dp):
    dp.add_handler(CommandHandler("link", link_command))
    dp.add_handler(CallbackQueryHandler(handle_user_limit, pattern=r"^link_gen_set_user_limit_\d+_-(\d+)$"))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups & ~Filters.command, user_limit_received), group=23)
    dp.add_handler(CallbackQueryHandler(handle_set_expiry_date, pattern=r"^link_gen_set_expiry_date_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(set_expiry_time, pattern=r"^link_gen_expiry_\d+_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_approval_mode, pattern=r"^link_gen_approval_mode_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_create_link, pattern=r"^link_gen_create_link_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_revoke_link, pattern=r"^rlz_\d+_-(\d+)_.+$"))
    dp.add_handler(CallbackQueryHandler(handle_set_member_link, pattern=r"^link_gen_set_member_link_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_set_public_link, pattern=r"^set_public_\d+_-(\d+)_.+$"))
    dp.add_handler(CallbackQueryHandler(handle_back_to_dashboard, pattern=r"^link_gen_back_to_dashboard_\d+_-(\d+)$"))
    dp.add_handler(CallbackQueryHandler(handle_close_dashboard, pattern=r"^link_gen_close_dashboard$"))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups & ~Filters.command, member_link_received), group=24)
