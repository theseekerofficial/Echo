# super_plugins/guardian/captcha/captcha_logic.py 
import os
import re
import time
import pytz
import random
import string
from gtts import gTTS
from loguru import logger
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from telegram.ext import CallbackContext, Filters, CallbackQueryHandler, JobQueue
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, InputMediaPhoto

from super_plugins.guardian.logger.logger_executor import log_captcha_process_stats
from super_plugins.guardian.captcha.captcha_quize_dictionary import QUIZ_QUESTIONS

FONT_DIR = 'plugins/logo_gen/fonts'
FONTS = [
    'Angelina.ttf', 'BlackDestroy.ttf', 'Estonia-Regular.ttf',
    'MoiraiOne-Regular.ttf', 'Pacifico-Regular.ttf', 'RubikMicrobe-Regular.ttf', 'Scripto.ttf', 
    'SingleDay.ttf', 'Sixtyfour-Regular-VariableFont.ttf', 'Stylish-Regular.ttf'
]

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']
db2 = client['Echo']
cpt_punisment_data_collection = db['CPT_Punishment_data']
user_and_chat_data_collection = db2['user_and_chat_data']

def start_captcha_process(update: Update, context: CallbackContext, new_user, chat_id, invt_link_info, inviter_user_info):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    new_member = new_user
    context.user_data['invite_link_info'] = invt_link_info
    collection_for_second_check = db[str(chat_id)]
    cpt_doc_for_invtd_user = collection_for_second_check.find_one({'identifier': 'captcha'})
    inviter_mode = context.user_data.get('inviter_mode_activated', False)

    if inviter_user_info is not None and invt_link_info is None and inviter_mode:
        if cpt_doc_for_invtd_user:
            is_need_to_do_captcha = cpt_doc_for_invtd_user.get('no_cpt_for_added_users', True)
            if is_need_to_do_captcha and inviter_mode:
                welcome_new_member(chat_id, new_member, inviter_user_info, update, context)
                context.user_data.pop('inviter_mode_activated', None)
                return
            else:
                context.user_data.pop('inviter_mode_activated', None)
        else:
            welcome_new_member(chat_id, new_member, inviter_user_info, update, context)
            context.user_data.pop('inviter_mode_activated', None)
            return

    try:
        context.bot.restrict_chat_member(
            chat_id,
            new_member.id,
            permissions=ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False, can_change_info=False, can_invite_users=True, can_pin_messages=False),
            until_date=None
        )
        info_text = f"⏬#New_User_Join\n\nUser Joined to [<code>{chat_id}</code>] chat. User is Muted and about to face captcha challenge 🤜🤛"
        chat_info_for_log = context.bot.get_chat(chat_id)
        log_captcha_process_stats(new_member, chat_info_for_log, info_text, context)
        collection = db[str(chat_id)]
        doc = collection.find_one({'identifier': 'captcha'})
        if doc and 'punishment_time' in doc:
            punishment_time = doc.get('punishment_time')
            due_time = datetime.now() + timedelta(minutes=punishment_time)
            cpt_punisment_data_collection.update_one({'user_id': new_user.id, 'chat_id': chat_id}, {'$set': {'time_have_to_complete': due_time}}, upsert=True)
        logger.info(f"[{new_member.id}] Restricted in [{chat_id}] and Captcha Process Started ⚙️")
        send_captcha_message(update, context, chat_id, new_member.id, invt_link_info)
        
    except Exception as e:
        cpt_unmute_user(chat_id, new_member.id, context)
        welcome_new_member(chat_id, new_member, invt_link_info, update, context)
        info_text = f"❗#Fail_to_Challenge_User\n\nFaild to execute captcha for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
        chat_info_for_log = context.bot.get_chat(chat_id)
        log_captcha_process_stats(new_member, chat_info_for_log, info_text, context)
        user_id_for_del = int(new_member.id)
        cpt_punisment_data_collection.delete_many({"user_id": user_id_for_del, "chat_id": int(chat_id)})
        logger.error(f"Failed to mute or challenge new member: {e} | Sending Welcome message...")

def send_captcha_message(update, context, chat_id, user_id, invt_link_info):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    collection = db[str(chat_id)]
    group_details = collection.find_one({'identifier': 'captcha'})
    context.user_data['invite_link_info'] = invt_link_info
    user_info = context.bot.get_chat(user_id)
    chat_info = context.bot.get_chat(chat_id)
    admin_count = len(context.bot.get_chat_administrators(chat_id))
    context.user_data['invite_link_info'] = invt_link_info
    
    if group_details and 'topic_id' in group_details:
        message_thread_id = group_details.get('topic_id', None)
    else:
        message_thread_id = None
        
    if 'punishment_time' in group_details:
        have_time = str(group_details.get('punishment_time')) + ' minutes'
    else:
        have_time = 'unlimited minutes'

    if group_details and group_details.get('captcha_stats', False):
        if 'captcha_mode' in group_details and group_details.get('captcha_mode') == 'button':
            user_link = f"<a href='tg://user?id={user_id}'>{user_info.first_name}</a>"
            message_text = group_details.get('captcha_message', f'{user_link}, Please verify you are human.')
            captcha_buttons = group_details.get('captcha_buttons_info', None)

            message_text = replace_placeholders(message_text, user_info, chat_info, admin_count, context)
            reply_markup = parse_buttons(captcha_buttons, chat_info, user_info, context)

            if 'captcha_media_id' in group_details:
                file_id = group_details['captcha_media_id']
                media_type = group_details.get('captcha_media_type', 'photo')

                if len(message_text) > 1023:
                    rules_msg = message_text[:1015] + "..."
                
                try:
                    if media_type == 'photo':
                        context.bot.send_photo(chat_id, photo=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'video':
                        context.bot.send_video(chat_id, video=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'document':
                        context.bot.send_document(chat_id, document=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'audio':
                        context.bot.send_audio(chat_id, audio=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                except Exception as e:
                    logger.error(f"There was an error during sending captcha media message: {e}")
                    cpt_unmute_user(chat_id, user_id, context)
                    cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
                    welcome_new_member(chat_id, user_info, invt_link_info, update, context)
                    info_text = f"❗#Fail_to_Send_Captcha_Message\n\nFaild to send captcha challenge message for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
            else:
                context.bot.send_message(chat_id, text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)

        elif 'captcha_mode' in group_details and group_details.get('captcha_mode') == 'math':
            captcha_question = generate_math_captcha(user_id, chat_id, context)
            user_link = f"<a href='tg://user?id={user_id}'>{user_info.first_name}</a>"
            message_text = f"🛡️ {user_link}, <i>Please solve this math problem to complete the captcha process and unmute yourself in</i> <code>{chat_info.title}</code> <i>group.</i>\n\n🌀<i>You will have</i> <u>{have_time}</u> <i>to complete this challenge</i>\n\nWhat is the answer for <code>{captcha_question}</code> ?"
            reply_markup = generate_numeric_keypad(user_id, chat_id)

            if 'captcha_media_id' in group_details:
                file_id = group_details['captcha_media_id']
                media_type = group_details.get('captcha_media_type', 'photo')
                
                try:
                    if media_type == 'photo':
                        context.bot.send_photo(chat_id, photo=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'video':
                        context.bot.send_video(chat_id, video=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'document':
                        context.bot.send_document(chat_id, document=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    elif media_type == 'audio':
                        context.bot.send_audio(chat_id, audio=file_id, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                except Exception as e:
                    logger.error(f"There was an error during sending captcha media message: {e}")
                    cpt_unmute_user(chat_id, user_id, context)
                    cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
                    welcome_new_member(chat_id, user_info, invt_link_info, update, context)
                    info_text = f"❗#Fail_to_Send_Captcha_Message\n\nFaild to send captcha challenge message for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
            else:
                context.bot.send_message(chat_id, text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)

        elif 'captcha_mode' in group_details and group_details.get('captcha_mode') == 'rule_accept':
            user_link = f"<a href='tg://user?id={user_id}'>{user_info.first_name}</a>"
            rules_doc = collection.find_one({'identifier': 'rules'})
            
            if rules_doc and 'rules_buttons' in rules_doc:
                rules_buttons = rules_doc.get('rules_buttons', None)
                reply_markup = parse_buttons_for_ra(rules_buttons, chat_info, user_info, context)
            else:
                keyboard = [InlineKeyboardButton("I Accept 🤝", callback_data=f"g_cpt_ra_i_yes_accept_rules_{chat_id}_{user_id}"), InlineKeyboardButton("I don't Accept ❌", callback_data=f"g_cpt_ra_i_no_accept_rules_{chat_id}_{user_id}")]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
            if rules_doc and 'rules_msg' in rules_doc or 'media_id' in rules_doc:
                rules_msg = rules_doc.get('rules_msg', f"""{user_link} Do you accept this rules? 

1. Respect and Politeness:
   - Communicate respectfully and courteously.
   - No hate speech, harassment, or discrimination.

2. No Spam or Self-Promotion:
   - Avoid irrelevant content and self-promotion.
   - No advertisements, affiliate links, or spam.

3. Stay On Topic:
   - Keep discussions relevant to the group's purpose.
   - Avoid off-topic conversations.

4. No NSFW Content:
   - No explicit, obscene, or NSFW material.
   - No inappropriate images, videos, or links.

5. No Illegal Activities:
   - Do not engage in or promote illegal activities.
   - This includes piracy, hacking, or illicit substance use.

6. No Personal Attacks:
   - Disagreements are fine, but no personal attacks or insults.
   - Respectful communication is expected.

7. Respect Privacy:
   - Do not share personal or sensitive information without consent.
   - This includes private messages or contact details.

8. English Preferred (If Applicable):
   - Use English for better understanding and inclusivity.
   - Adapt language based on group preferences.

9. No Trolling or Disruptive Behavior:
   - Avoid trolling, flaming, or disruptive actions.
   - Maintain a positive and constructive atmosphere.

10. Listen to Admins and Moderators:
    - Follow instructions from group admins and moderators.
    - Failure to comply may result in warnings or removal.
""")
                rules_msg = replace_placeholders(rules_msg, user_info, chat_info, admin_count, context)

                if 'media_id' in rules_doc:
                    file_id = rules_doc['media_id']
                    media_type = rules_doc.get('media_type', 'photo')

                    if len(rules_msg) > 1023:
                        rules_msg = rules_msg[:1015] + "..."
                    
                    try:
                        if media_type == 'photo':
                            context.bot.send_photo(chat_id, photo=file_id, caption=rules_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                        elif media_type == 'video':
                            context.bot.send_video(chat_id, video=file_id, caption=rules_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                        elif media_type == 'document':
                            context.bot.send_document(chat_id, document=file_id, caption=rules_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                        elif media_type == 'audio':
                            context.bot.send_audio(chat_id, audio=file_id, caption=rules_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
                    except Exception as e:
                        logger.error(f"There was an error during sending captcha media message: {e}")
                        cpt_unmute_user(chat_id, user_id, context)
                        cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
                        welcome_new_member(chat_id, user_info, invt_link_info, update, context)
                        info_text = f"❗#Fail_to_Send_Captcha_Message\n\nFaild to send captcha challenge message for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
                        log_captcha_process_stats(user_info, chat_info, info_text, context)
                else:
                    context.bot.send_message(chat_id, text=rules_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)

        elif 'captcha_mode' in group_details and group_details.get('captcha_mode') == 'recaptcha':
            captcha_text, captcha_image, filename = generate_recaptcha_image(user_id, chat_id, context)
            user_link = f"<a href='tg://user?id={user_id}'>{user_info.first_name}</a>"
            message_text = f"🛡️ {user_link}, <i>Please solve this CAPTCHA to unmute yourself in</i> <code>{chat_info.title}</code> <i>group.</i>\n\n🌀<i>You will have</i> <u>{have_time}</u> <i>to complete this challenge</i>\n\nUse 'Regenerate' to get new image for captcha. Type what you see in the above image from left to right:"
            context.user_data[f'recaptcha_input_{user_id}'] = ''
            context.user_data[f'recaptcha_shift_{user_id}'] = False
            reply_markup = generate_recaptcha_keypad(user_id, chat_id)

            try:
                context.bot.send_photo(chat_id, photo=captcha_image, caption=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
            except Exception as e:
                logger.error(f"Failed to send recaptcha image: {e}")
                cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
                cpt_unmute_user(chat_id, user_id, context)
                welcome_new_member(chat_id, user_info, invt_link_info, update, context)
                info_text = f"❗#Fail_to_Send_ReCaptcha_Message\n\nFailed to send captcha challenge message for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
                log_captcha_process_stats(user_info, chat_info, info_text, context)
                context.user_data.pop(f'recaptcha_answer_{user_id}', None)
            finally:
                captcha_image.close()
                os.remove(filename)

        elif 'captcha_mode' in group_details and group_details.get('captcha_mode') == 'quiz':
            question = generate_quiz_captcha(user_id, chat_id, context)
            user_link = f"<a href='tg://user?id={user_id}'>{user_info.first_name}</a>"
            message_text = f"🛡️ {user_link}, <i>Answer this question to unmute yourself in</i> <code>{chat_info.title}</code> <i>group.</i>\n\n🌀<i>You will have</i> <u>{have_time}</u> <i>to complete this challenge. Click 'Hint' to get a Hint about your question. Click 'Change Question' to get another question.</i>\n\n<code>{question}</code>"
            reply_markup = generate_quiz_keypad(user_id, chat_id)

            try:
                context.bot.send_message(chat_id, text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, message_thread_id=message_thread_id)
            except Exception as e:
                logger.error(f"Failed to send quiz question: {e}")
                cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
                cpt_unmute_user(chat_id, user_id, context)
                welcome_new_member(chat_id, user_info, invt_link_info, update, context)
                info_text = f"❗#Fail_to_Send_Quiz_Message\n\nFailed to send quiz challenge message for user in [<code>{chat_id}</code>] due to: <code>{e}</code>"
                log_captcha_process_stats(user_info, chat_info, info_text, context)
                context.user_data.pop(f'quiz_answer_{user_id}', None)

        else:
            cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
            cpt_unmute_user(chat_id, user_id, context)
            welcome_new_member(chat_id, user_info, invt_link_info, update, context)
            info_text = f"⚠️#Not_Set_a_Captcha_Mode\n\nUser unmuted in [<code>{chat_id}</code>], because captcha mode not set up by it's admins"
            log_captcha_process_stats(user_info, chat_info, info_text, context)
            logger.error(f"Look Like Captcha Enabled but admins did not set up a Captcha Mode. So User is Unmuted in [{chat_id}]...")

def verify_rule_accept_captcha_callback(update: Update, context: CallbackContext):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    query = update.callback_query
    chat_id = query.data.split('_')[-2]
    user_id = query.data.split('_')[-1]
    user_choice = query.data.split('_')[-5]
    c_user_id = int(user_id)
    invt_link_info = context.user_data.get('invite_link_info', None)
    user = context.bot.get_chat(user_id)
    chat_info_for_log = context.bot.get_chat(chat_id)

    if c_user_id != query.from_user.id:
        query.answer(f"{query.from_user.first_name}, do not touch this❗", show_alert=True)
        return
    else:
        if user_choice == 'yes':
            query.answer(f"{query.from_user.first_name}, Thank You for accepting rules. Enjoy the group❕", show_alert=True)

    if user_choice == 'yes':
        try:
            cpt_unmute_user(chat_id, user_id, context)
            logger.info(f"[{user_id}] Successfully Verified himself in [{chat_id}] 🥷")
            query.delete_message()
            welcome_new_member(chat_id, user, invt_link_info, update, context)
            info_text = f"✅ #User_Completed_Captcha\n\nUser Successfully Unmute himself in [<code>{chat_id}</code>]\nChallenge: <code>Rules Acception Captcha</code>"
            log_captcha_process_stats(user, chat_info_for_log, info_text, context)
            context.user_data.pop('invite_link_info', None)
        except Exception as e:
            info_text = f"❌ #Failed_to_Unmute_User\n\nUnable to Unmute User in [<code>{chat_id}</code>] due to: <code>{e}</code>"
            query.delete_message()
            log_captcha_process_stats(user, chat_info_for_log, info_text, context)
            context.bot.send_message(chat_id, text=f"Faild to Unmute <code>{user_info.first_name}</code> in this chat. Please Contact Group Administration for resolve this problem", parse_mode=ParseMode.HTML)
            logger.error(f"Failed to unmute user: {e}")
            
    elif user_choice == 'no': 
        try:
            context.bot.ban_chat_member(chat_id, user_id)
            context.bot.unban_chat_member(chat_id, user_id)
            logger.info(f"[{user_id}] Kicked out from [{chat_id}] due to not accepting rules of the chat 📤")
            query.delete_message()
            info_text = f"❕ #User_Kicked_Out\n\nUser Kicked Out from [<code>{chat_id}</code>] due to not accepting rules of the chat 📤"
            log_captcha_process_stats(user, chat_info_for_log, info_text, context)
            context.user_data.pop('invite_link_info', None)
        except Exception as e:
            info_text = f"❌ #Failed_to_Kick_User\n\nUnable to Kick User in [<code>{chat_id}</code>] due to: <code>{e}</code>"
            query.delete_message()
            log_captcha_process_stats(user, chat_info_for_log, info_text, context)
            logger.error(f"Failed to ban user: {e}")

    cpt_punisment_data_collection.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

def verify_captcha_callback(update: Update, context: CallbackContext):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    query = update.callback_query
    chat_id = query.data.split('_')[-2]
    user_id = query.data.split('_')[-1]
    c_user_id = int(user_id)
    invt_link_info = context.user_data.get('invite_link_info', None)

    if c_user_id != query.from_user.id:
        query.answer(f"{query.from_user.first_name}, do not touch this❗", show_alert=True)
        return
    else:
        query.answer(f"Good Job {query.from_user.first_name}, You completed Verification successfully ✅", show_alert=True)

    try:
        cpt_unmute_user(chat_id, user_id, context)
        cpt_punisment_data_collection.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})
        logger.info(f"[{user_id}] Successfully Verified himself in [{chat_id}] 🥷")
        user = context.bot.get_chat(user_id)
        query.delete_message()
        welcome_new_member(chat_id, user, invt_link_info, update, context)
        info_text = f"✅ #User_Completed_Captcha\n\nUser Successfully Unmute himself in [<code>{chat_id}</code>]\nChallenge: <code>Button Captcha</code>"
        chat_info_for_log = context.bot.get_chat(chat_id)
        log_captcha_process_stats(user, chat_info_for_log, info_text, context)
        context.user_data.pop('invite_link_info', None)
    except Exception as e:
        user_info = context.bot.get_chat(user_id)
        cpt_punisment_data_collection.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})
        info_text = f"❌ #Failed_to_Unmute_User\n\nUnable to Unmute User in [<code>{chat_id}</code>] due to: <code>{e}</code>"
        chat_info_for_log = context.bot.get_chat(chat_id)
        log_captcha_process_stats(user_info, chat_info_for_log, info_text, context)
        context.bot.send_message(chat_id, text=f"Faild to Unmute <code>{user_info.first_name}</code> in this chat. Please Contact Group Administration for resolve this problem", parse_mode=ParseMode.HTML)
        logger.error(f"Failed to unmute user: {e}")

def replace_placeholders(captcha_msg, user, chat, admin_count, context):
    def get_time_in_tz(time_str):
        try:
            timezone = pytz.timezone(time_str)
            return datetime.now(timezone).strftime('%H:%M:%S')
        except pytz.exceptions.UnknownTimeZoneError:
            return datetime.utcnow().strftime('%H:%M:%S')

    def get_date_in_tz(date_str):
        try:
            timezone = pytz.timezone(date_str)
            return datetime.now(timezone).strftime('%Y-%m-%d')
        except pytz.exceptions.UnknownTimeZoneError:
            return datetime.utcnow().strftime('%Y-%m-%d')

    try:
        mention_text = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    except Exception as e:
        logger.info(f"An Error Occurred: {e}")
        mention_text = user.first_name 

    placeholders = {
        '[id]': str(user.id),
        '[first_name]': user.first_name,
        '[second_name]': user.last_name or '',
        '[username]': f"@{user.username}" if user.username else 'No username',
        '[group_name]': chat.title,
        '[group_id]': str(chat.id),
        '[admin_count]': str(admin_count),
        '[mention]': mention_text 
    }

    captcha_msg = re.sub(r'\[time\((.*?)\)\]', lambda m: get_time_in_tz(m.group(1)), captcha_msg)
    captcha_msg = re.sub(r'\[date\((.*?)\)\]', lambda m: get_date_in_tz(m.group(1)), captcha_msg)
    captcha_msg = re.sub(r'\[time\]', datetime.utcnow().strftime('%H:%M:%S'), captcha_msg)
    captcha_msg = re.sub(r'\[date\]', datetime.utcnow().strftime('%Y-%m-%d'), captcha_msg)
    
    for placeholder, value in placeholders.items():
        captcha_msg = captcha_msg.replace(placeholder, value)

    return captcha_msg

def parse_buttons(buttons_str, chat, user, context):
    if buttons_str is None:
        buttons_str = ''
    button_rows = buttons_str.strip().split('\n')
    keyboard = []
    for row in button_rows:
        row_buttons = row.split('|')
        keyboard_row = []
        for button in row_buttons:
            parts = button.strip().split('-')
            if len(parts) == 2:
                button_text, button_url = parts[0].strip(), parts[1].strip()
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
            elif button.strip().lower() == 'rules':
                button_text = "⚜️Rules ⚜️"
                button_url = f"https://t.me/{context.bot.username}?start=show_rules_{chat.id}"
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
        if keyboard_row:
            keyboard.append(keyboard_row)
            
    keyboard.append([InlineKeyboardButton("🛡️ Click to Verify 🛡️", callback_data=f"verify_captcha_{chat.id}_{user.id}")])    
    return InlineKeyboardMarkup(keyboard)

def parse_buttons_for_ra(buttons_str, chat, user, context):
    chat_id = chat.id
    user_id = user.id
    if buttons_str is None:
        buttons_str = ''
    button_rows = buttons_str.strip().split('\n')
    keyboard = []
    for row in button_rows:
        row_buttons = row.split('|')
        keyboard_row = []
        for button in row_buttons:
            parts = button.strip().split('-')
            if len(parts) == 2:
                button_text, button_url = parts[0].strip(), parts[1].strip()
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
            elif button.strip().lower() == 'rules':
                button_text = "⚜️Rules ⚜️"
                button_url = f"https://t.me/{context.bot.username}?start=show_rules_{chat.id}"
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
            elif button.strip().lower() == 'invite_link':
                try:
                    chat_for_link = context.bot.get_chat(chat.id)
                    invite_link = chat_for_link.invite_link
                    if not invite_link:
                        invite_link = context.bot.export_chat_invite_link(chat.id)
                    button_text = f"{chat.title}"
                    button_url = invite_link
                except Exception as e:
                    logger.error(f"Failed to create invite link for chat {chat.id}. Error: {e}")
                    continue
                keyboard_row.append(InlineKeyboardButton(button_text, url=button_url))
        if keyboard_row:
            keyboard.append(keyboard_row)

    keyboard.append([InlineKeyboardButton("I Accept 🤝", callback_data=f"g_cpt_ra_i_yes_accept_rules_{chat_id}_{user_id}"), InlineKeyboardButton("I don't Accept ❌", callback_data=f"g_cpt_ra_i_no_accept_rules_{chat_id}_{user_id}")]) 
    
    return InlineKeyboardMarkup(keyboard)

def execute_punishment(context):
    current_time = datetime.now()
    punishment_data = db['CPT_Punishment_data']

    overdue_users = punishment_data.find({})

    for user_data in overdue_users:
        chat_id = user_data['chat_id']
        user_id = user_data['user_id']
        chat_info = context.bot.get_chat(chat_id)
        user_info = context.bot.get_chat(user_id)
        time_have_to_complete = user_data.get('time_have_to_complete', None)
        
        chat_collection = db[str(chat_id)]
        captcha_config = chat_collection.find_one({'identifier': 'captcha'})
        
        if time_have_to_complete is None:
            punishment_data.delete_many({"user_id": user_id, "chat_id": chat_id})
            continue
        
        punishment_action = captcha_config.get('punishment', None)
        captcha_type = captcha_config.get('captcha_mode', None)
        
        if current_time >= time_have_to_complete:
            try:
                if punishment_action == 'Kick':
                    context.bot.ban_chat_member(chat_id, user_id)
                    context.bot.unban_chat_member(chat_id, user_id)
                    info_text = f"❗#Captcha_Punishment\n\nUser <code>Kicked</code> from [<code>{chat_id}</code>] due to not completing <code>{captcha_type} captcha</code>"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
                    logger.info(f"User [{user_id}] kicked from [{chat_id}] for failing to complete captcha.")
                elif punishment_action == 'Ban':
                    context.bot.ban_chat_member(chat_id, user_id)
                    info_text = f"❗#Captcha_Punishment\n\nUser <code>Banned</code> from [<code>{chat_id}</code>] due to not completing <code>{captcha_type} captcha</code>"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
                    logger.info(f"User [{user_id}] banned from [{chat_id}] for failing to complete captcha.")
                elif punishment_action == 'Mute':
                    context.bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    permissions=ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False, can_change_info=False, can_invite_users=False, can_pin_messages=False),
                    until_date=None
                    )
                    info_text = f"❗#Captcha_Punishment\n\nUser <code>Muted Permanently</code> in [<code>{chat_id}</code>] due to not completing <code>{captcha_type} captcha</code>"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
                    logger.info(f"User [{user_id}] muted from [{chat_id}] for failing to complete captcha.")
                elif punishment_action == 'Nothing':
                    cpt_unmute_user(chat_id, user_id, context)
                    info_text = f"❗#Captcha_Punishment\n\n<code>Nothing</code> did to the user in [<code>{chat_id}</code>] because punishment settings set to 'Nothing'. User is now unmuted and can send messages to group"
                    log_captcha_process_stats(user_info, chat_info, info_text, context)
                    logger.info(f"Nothing did to User [{user_id}] in [{chat_id}] but he failed to complete captcha.")
                
                punishment_data.delete_many({"user_id": user_id, "chat_id": chat_id})
                logger.info(f"User {user_id} captcha data deleted from CPT_Punishment_data collection.")

            except Exception as e:
                info_text = f"⚠️ #Captcha_Punishment_Fail\n\nFaild to execute captcha punishment [<code>{punishment_action}</code>] in [<code>{chat_id}</code>] for [<code>{user_id}</code>] due to: <code>{e}</code>. Take necessary actions immediately"
                log_captcha_process_stats(user_info, chat_info, info_text, context)
                punishment_data.delete_many({"user_id": user_id, "chat_id": chat_id})
                logger.error(f"Failed to execute punishment for user {user_id} in chat {chat_id}: {e}")

def generate_math_captcha(user_id, chat_id, context):
    num1 = random.randint(10, 99)
    num2 = random.randint(10, 99)
    operation = random.choice(['+', '-'])

    if operation == '-':
        num1, num2 = max(num1, num2), min(num1, num2)

    question = f"{num1} {operation} {num2}"
    answer = eval(question)
    context.user_data['cpt_math_expected_answer'] = answer
    return question


def generate_numeric_keypad(user_id, chat_id):
    keypad = [
        [InlineKeyboardButton(str(i), callback_data=f"g_cpt_num_{i}_{chat_id}_{user_id}") for i in range(1, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"g_cpt_num_{i}_{chat_id}_{user_id}") for i in range(4, 7)],
        [InlineKeyboardButton(str(i), callback_data=f"g_cpt_num_{i}_{chat_id}_{user_id}") for i in range(7, 10)],
        [InlineKeyboardButton("Backspace ⌫", callback_data=f"g_cpt_backspace_0_{chat_id}_{user_id}"),
         InlineKeyboardButton("0", callback_data=f"g_cpt_num_0_{chat_id}_{user_id}"),
         InlineKeyboardButton("Enter ✅", callback_data=f"g_cpt_enter_1_{chat_id}_{user_id}")]
    ]
    return InlineKeyboardMarkup(keypad)

def verify_math_captcha_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split('_')

    if data[-4] in ['num', 'backspace', 'enter']:
        handle_math_input(query, data, context, update)
        return

def handle_math_input(query, data, context, update):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    user_id = int(data[-1])
    chat_id = int(data[-2])
    chat_name = context.bot.get_chat(chat_id).title
    action = data[-4]
    user_input = context.user_data.get(f'math_input_{user_id}', '')
    invt_link_info = context.user_data.get('invite_link_info', None)

    if user_id != query.from_user.id:
        query.answer(f"{query.from_user.first_name}, Do not touch this❗", show_alert=True)
        return

    if action == 'enter':
        stored_answer = int(context.user_data['cpt_math_expected_answer'])
        if int(user_input) == stored_answer:
            query.answer(f"Correct Answer! You are now unmuted in {chat_name}. ✅", show_alert=True)
            cpt_unmute_user(chat_id, user_id, context)
            logger.info(f"[{user_id}] Successfully Verified himself in [{chat_id}] 🥷")
            user = context.bot.get_chat(user_id)
            query.delete_message()
            invt_link_info = context.user_data.get('invite_link_info', None)
            cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
            welcome_new_member(chat_id, user, invt_link_info, update, context)
            info_text = f"✅ #User_Completed_Captcha\n\nUser Successfully Unmute himself in [<code>{chat_id}</code>]\nChallenge: <code>Math Captcha</code>"
            user_info_for_log = context.bot.get_chat(user_id)
            chat_info_for_log = context.bot.get_chat(chat_id)
            log_captcha_process_stats(user_info_for_log, chat_info_for_log, info_text, context)
            context.user_data.pop(f'math_input_{user_id}', None)
            context.user_data.pop(f'invite_link_info', None)
            context.user_data.pop(f'cpt_math_expected_answer', None)
        else:
            query.answer("Invalid Answer. Try again! ❌", show_alert=True)
            context.user_data[f'math_input_{user_id}'] = ''
    elif action == 'backspace':
        context.user_data[f'math_input_{user_id}'] = user_input[:-1]
        display = context.user_data[f'math_input_{user_id}']
        query.answer(f"{display}")
    else:
        number = data[3]
        context.user_data[f'math_input_{user_id}'] = user_input + number
        display = context.user_data[f'math_input_{user_id}']
        query.answer(f"{display}")

def cpt_unmute_user(chat_id, user_id, context):
    context.bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
    )

def generate_recaptcha_image(user_id, chat_id, context):
    captcha_text = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    context.user_data[f'recaptcha_answer_{user_id}'] = captcha_text

    width, height = 300, 100
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    num_fonts = random.choice([3, 4])
    selected_fonts = random.sample(FONTS, num_fonts)

    def get_font(font_name, size):
        return ImageFont.truetype(os.path.join(FONT_DIR, font_name), size)

    char_info = []
    for char in captcha_text:
        font = get_font(random.choice(selected_fonts), random.randint(45, 55))
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        char_height = bbox[3] - bbox[1]
        char_info.append((char, font, char_width, char_height))

    total_text_width = sum([info[2] for info in char_info]) + 10 * (len(captcha_text) - 1)
    x = max(10, (width - total_text_width) // 2)

    for char, font, char_width, char_height in char_info:
        y = random.randint(0, height - 60)
        draw.text((x, y), char, font=font, fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        x += char_width + 10

    for _ in range(10):
        draw.line(
            [(random.randint(0, width), random.randint(0, height)), (random.randint(0, width), random.randint(0, height))],
            fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
            width=2
        )
    for _ in range(100):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        )

    image = image.filter(ImageFilter.GaussianBlur(0.5))

    filename = f"recaptcha_{chat_id}_{user_id}.png"
    image.save(filename)

    return captcha_text, open(filename, 'rb'), filename

def generate_tts_voice_clip(text, filename):
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    return filename

def send_voice_clip_to_user(user_id, text, bot, chat_id):
    filename = f"recaptcha_audio_{user_id}.mp3"
    try:
        generated_file = generate_tts_voice_clip(text, filename)
        with open(generated_file, 'rb') as captcha_audio:
            bot.send_audio(user_id, audio=captcha_audio, title=f"reCAPTCHA Voice Output for {user_id}", caption=f"reCAPTCHA Voice Output for <code>{bot.get_chat(user_id).first_name}</code> in <code>{bot.get_chat(chat_id).title}</code>", parse_mode=ParseMode.HTML)
            logger.info(f"reCAPTCHA Audio Output send to [{user_id}]. Chat ID: [{chat_id}]")
    except Exception as e:
        logger.error(f"Failed to send audio message to {user_id}: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def spell_out_text(text):
    def spell_char(char):
        if char.isupper():
            return f"capital {char}"
        elif char.islower():
            return f"simple {char}"
        elif char.isdigit():
            return f"{char}"
        return char

    return "  ".join(spell_char(char) for char in text)

def generate_recaptcha_keypad(user_id, chat_id, shift=False):
    letters = string.ascii_uppercase if shift else string.ascii_lowercase
    digits = string.digits
    keypad = [[InlineKeyboardButton(char, callback_data=f"recpt_num_{char}_{chat_id}_{user_id}") for char in letters[i:i + 6]] for i in range(0, len(letters), 6)]
    keypad.append([InlineKeyboardButton(char, callback_data=f"recpt_num_{char}_{chat_id}_{user_id}") for char in digits[:5]])
    keypad.append([InlineKeyboardButton(char, callback_data=f"recpt_num_{char}_{chat_id}_{user_id}") for char in digits[5:]])
    keypad.append([InlineKeyboardButton("Regenerate ♻️", callback_data=f"recpt_regen_s_{chat_id}_{user_id}"), InlineKeyboardButton("Get Voice Output 🎤", callback_data=f"recpt_voice_s_{chat_id}_{user_id}")]),
    keypad.append([InlineKeyboardButton("Shift ⬆️", callback_data=f"recpt_shift_s_{chat_id}_{user_id}"),
                   InlineKeyboardButton("Backspace ⌫", callback_data=f"recpt_backspace_s_{chat_id}_{user_id}"),
                   InlineKeyboardButton("Enter ✅", callback_data=f"recpt_enter_s_{chat_id}_{user_id}")])
    return InlineKeyboardMarkup(keypad)

def verify_recaptcha_callback(update: Update, context: CallbackContext):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    query = update.callback_query
    data = query.data.split('_')

    action = data[1]
    chat_id = int(data[-2])
    user_id = int(data[-1])
    chat_info = context.bot.get_chat(chat_id)
    collection = db[str(chat_id)]
    group_details = collection.find_one({'identifier': 'captcha'})
    invt_link_info = context.user_data.get('invite_link_info', None)

    if 'punishment_time' in group_details:
        have_time = str(group_details.get('punishment_time')) + ' minutes'
    else:
        have_time = 'unlimited minutes'
    
    input_field = f"recaptcha_input_{user_id}"
    answer_field = f"recaptcha_answer_{user_id}"
    shift_field = f"recaptcha_shift_{user_id}"

    if user_id != query.from_user.id:
        query.answer("This CAPTCHA isn't for you!", show_alert=True)
        return

    if action == 'num':
        char = data[2]
        context.user_data[input_field] = context.user_data.get(input_field, '') + char
        query.answer(context.user_data[input_field])
    elif action == 'shift':
        shift = context.user_data.get(shift_field, False)
        context.user_data[shift_field] = not shift
        reply_markup = generate_recaptcha_keypad(user_id, chat_id, shift=not shift)
        query.edit_message_reply_markup(reply_markup=reply_markup)
    elif action == 'backspace':
        context.user_data[input_field] = context.user_data.get(input_field, '')[:-1]
        query.answer(context.user_data[input_field])
    elif action == 'enter':
        expected_answer = context.user_data.get(answer_field, '')
        user_input = context.user_data.get(input_field, '')

        if user_input == expected_answer:
            query.answer(f"Bravo! You are now unmuted in {chat_info.title}. ✅", show_alert=True)
            cpt_unmute_user(chat_id, user_id, context)
            query.delete_message()
            user = context.bot.get_chat(user_id)
            welcome_new_member(chat_id, user, invt_link_info, update, context)
            cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
            logger.info(f"[{user_id}] Successfully verified in [{chat_id}] 🥷")
            info_text = f"✅ #User_Completed_Captcha\n\nUser Successfully Unmute himself in [<code>{chat_id}</code>]\nChallenge: <code>ReCaptcha</code>"
            user_info_for_log = context.bot.get_chat(user_id)
            chat_info_for_log = context.bot.get_chat(chat_id)
            log_captcha_process_stats(user_info_for_log, chat_info_for_log, info_text, context)
            context.user_data.pop(f'invite_link_info', None)
        else:
            context.user_data[input_field] = ''
            query.answer("Wrong answer! Try again.", show_alert=True)
    elif action == 'regen':
        captcha_text, captcha_image, filename = generate_recaptcha_image(user_id, chat_id, context)
        context.user_data[input_field] = ''
        context.user_data[f'recaptcha_answer_{user_id}'] = captcha_text
        shift = context.user_data.get(shift_field, False)
        reply_markup = generate_recaptcha_keypad(user_id, chat_id, shift=shift)
        try:
            query.edit_message_media(
                media=InputMediaPhoto(captcha_image),
                reply_markup=reply_markup
            )
        finally:
            captcha_image.close()
            os.remove(filename) 
    elif action == 'voice':
        user_data = user_and_chat_data_collection.find_one({"user_id": user_id})
        if user_data:
            try:
                answer_text = spell_out_text(context.user_data[f'recaptcha_answer_{user_id}'])
                voice_text = f"Please type the following characters in button keyboard. {answer_text}"
                send_voice_clip_to_user(user_id, voice_text, context.bot, chat_id)
                query.answer("Check your private messages for the voice output. 🎤", show_alert=True)
            except Exception as e:
                logger.error(f"Failed to send voice output: {e}")
                query.answer("Couldn't send voice output. Try again later.", show_alert=True)
        else:
            query.answer(f"First start @{context.bot.username} in PM, then try again.", show_alert=True)
    else:
        query.answer("Unknown action", show_alert=True)

def generate_quiz_captcha(user_id, chat_id, context):
    question, data = random.choice(list(QUIZ_QUESTIONS.items()))
    answer = data['answer']
    hint = data['hint']
    context.user_data[f'quiz_answer_{user_id}'] = answer.lower()
    context.user_data[f'quiz_hint_{user_id}'] = hint
    context.user_data[f'quiz_input_{user_id}'] = ''
    context.user_data[f'quiz_shift_{user_id}'] = False
    return question

def generate_quiz_keypad(user_id, chat_id, shift=False):
    letters = string.ascii_uppercase if shift else string.ascii_lowercase
    digits = string.digits
    keypad = [[InlineKeyboardButton(char, callback_data=f"quiz_num_{char}_{chat_id}_{user_id}") for char in letters[i:i + 6]] for i in range(0, len(letters), 6)]
    keypad.append([InlineKeyboardButton(char, callback_data=f"quiz_num_{char}_{chat_id}_{user_id}") for char in digits[:5]])
    keypad.append([InlineKeyboardButton(char, callback_data=f"quiz_num_{char}_{chat_id}_{user_id}") for char in digits[5:]])
    keypad.append([InlineKeyboardButton("Hint 💡", callback_data=f"quiz_hint_s_{chat_id}_{user_id}"),
                   InlineKeyboardButton("Change Question ♻️", callback_data=f"quiz_change_s_{chat_id}_{user_id}")])
    keypad.append([InlineKeyboardButton("Shift ⬆️", callback_data=f"quiz_shift_s_{chat_id}_{user_id}"), InlineKeyboardButton("Space 🛣️", callback_data=f"quiz_space_s_{chat_id}_{user_id}")]),
    keypad.append([InlineKeyboardButton("Backspace ⌫", callback_data=f"quiz_backspace_s_{chat_id}_{user_id}"),
                   InlineKeyboardButton("Enter ✅", callback_data=f"quiz_enter_s_{chat_id}_{user_id}")])
    return InlineKeyboardMarkup(keypad)


def verify_quiz_captcha_callback(update: Update, context: CallbackContext):
    from super_plugins.guardian.welcomer.welcomer_logic import welcome_new_member
    query = update.callback_query
    data = query.data.split('_')

    action = data[1]
    chat_id = int(data[-2])
    user_id = int(data[-1])
    user = context.bot.get_chat(user_id)
    chat_info = context.bot.get_chat(chat_id)
    collection = db[str(chat_id)]
    group_details = collection.find_one({'identifier': 'captcha'})
    invt_link_info = context.user_data.get('invite_link_info', None)

    input_field = f'quiz_input_{user_id}'
    answer_field = f'quiz_answer_{user_id}'
    hint_field = f'quiz_hint_{user_id}'
    shift_field = f'quiz_shift_{user_id}'

    if user_id != query.from_user.id:
        query.answer("This quiz isn't for you!", show_alert=True)
        return

    if action == 'num':
        char = data[2]
        context.user_data[input_field] = context.user_data.get(input_field, '') + char
        query.answer(context.user_data[input_field])
    elif action == 'shift':
        shift = context.user_data.get(shift_field, False)
        context.user_data[shift_field] = not shift
        reply_markup = generate_quiz_keypad(user_id, chat_id, shift=not shift)
        query.edit_message_reply_markup(reply_markup=reply_markup)
    elif action == 'backspace':
        context.user_data[input_field] = context.user_data.get(input_field, '')[:-1]
        query.answer(context.user_data[input_field])
    elif action == 'enter':
        expected_answer = context.user_data.get(answer_field, '').lower()
        user_input = context.user_data.get(input_field, '').lower()

        if user_input == expected_answer:
            query.answer(f"Bravo! You are now unmuted in {chat_info.title}. ✅", show_alert=True)
            cpt_unmute_user(chat_id, user_id, context)
            query.delete_message()
            user = context.bot.get_chat(user_id)
            welcome_new_member(chat_id, user, invt_link_info, update, context)
            cpt_punisment_data_collection.delete_many({"user_id": user_id, "chat_id": chat_id})
            logger.info(f"[{user_id}] Successfully verified in [{chat_id}] 🥷")
            info_text = f"✅ #User_Completed_Captcha\n\nUser Successfully Unmute himself in [<code>{chat_id}</code>]\nChallenge: <code>Quiz</code>"
            user_info_for_log = context.bot.get_chat(user_id)
            chat_info_for_log = context.bot.get_chat(chat_id)
            log_captcha_process_stats(user_info_for_log, chat_info_for_log, info_text, context)
            context.user_data.pop(f'invite_link_info', None)
        else:
            query.answer("Wrong answer! Try again.", show_alert=True)
            context.user_data[input_field] = ''
    elif action == 'hint':
        hint = context.user_data.get(hint_field, '')
        query.answer(f"Hint: {hint}", show_alert=True)
    elif action == 'change':
        question = generate_quiz_captcha(user_id, chat_id, context)
        user_link = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
        message_text = f"🛡️ {user_link}, <i>Answer this question to unmute yourself in</i> <code>{chat_info.title}</code> <i>group.</i>\n\n🌀<i>You will have</i> <u>{str(group_details.get('punishment_time', 'unlimited')) + ' minutes'}</u> <i>to complete this challenge. Click 'Hint' to get a Hint about your question. Click 'Change Question' to get another question.</i>\n\n<code>{question}</code>"
        shift = context.user_data.get(shift_field, False)
        reply_markup = generate_quiz_keypad(user_id, chat_id, shift=shift)
        query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    elif action == 'space':
        context.user_data[input_field] = context.user_data.get(input_field, '') + ' '
        query.answer(context.user_data[input_field])
    else:
        query.answer("Unknown action", show_alert=True)

def setup_captcha_logic_handlers(dp):
    dp.add_handler(CallbackQueryHandler(verify_captcha_callback, pattern=r"^verify_captcha_-(\d+)_\d+$"))
    dp.add_handler(CallbackQueryHandler(verify_math_captcha_callback, pattern=r"^g_cpt_(num_|backspace_|enter_)\d+_-(\d+)_\d+$"))
    dp.add_handler(CallbackQueryHandler(verify_rule_accept_captcha_callback, pattern=r"^g_cpt_ra_i_(yes|no)_accept_rules_-(\d+)_\d+$"))
    dp.add_handler(CallbackQueryHandler(verify_recaptcha_callback, pattern=r"^recpt_(num_|shift_|backspace_|enter_|regen_|voice_)([a-zA-Z0-9])_-(\d+)_\d+$"))
    dp.add_handler(CallbackQueryHandler(verify_quiz_captcha_callback, pattern=r"^quiz_(num_|shift_|backspace_|enter_|hint_|change_|space_)([a-zA-Z0-9])_-(\d+)_\d+$"))
    dp.job_queue.run_repeating(execute_punishment, interval=60, first=10, context=CallbackContext.from_update)
