import os
import sys
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate, MessageIdInvalid
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# Bot and User Session Configuration
api_id = ''  # Your api_id
api_hash = ''  # Your api_hash
bot_token = ''  # Your bot token. ⚠️ Remember, do not enter your Echo Client Bot Token here. Enter a new bot token here
user_session_string = ''  # Your user session string
destination_chats = ''  # Comma-separated destination chat IDs
do_forward = True # Set True if you want to forward messages. Set False if you want to send messages instead of forwarding (Recommended: True)

# Set True or False to clone desired media types
clone_text = True
clone_photos = True
clone_videos = True
clone_documents = True
clone_audio = True
clone_stickers = True

# Rate Limit Control System
small_sleep_interval = 1  # Time in seconds to sleep between every two files (Adjust as needed | Remember about TG Rate Limits)
large_sleep_interval = 300  # Time in seconds to sleep after every 150 files indexed (Adjust as needed | Remember about TG Rate Limits)

# Allowed controller user IDs
controller_ids = {}  # Set User IDs, who can use TeleFileDex Supporter Plugin | Separate Multiple by comma (e.g. 123456789,987654321,192837465)

# Do not edit anything below this line
#----------------------------------------------------------------------------------------------------------------------------------------------------

# Target message ID to stop at (Do Not Edit This Value!)
target_message_id = None
# Progress status variable (Do Not Edit These values!)
indexing_active = False
start_time = None
# Pause State Controller (Do Not Edit This value!)
is_paused = False

bot = Client("bot", api_id, api_hash, bot_token=bot_token)
user_client = Client("session_name", api_id=api_id, api_hash=api_hash, session_string=user_session_string)

if __name__ == "__main__":
    if os.getenv('RUNNING_THROUGH_CODECAPSULE') != 'true':
        print("This script should not be run directly. Please use an Echo Client to run this script.")
        sys.exit(1)

async def fetch_and_send_content(channel_id, starting_message_id, user_id, end_message_id=None, progress_message=None, user_name=''):
    global indexing_active, start_time, is_paused
    async with user_client:
        current_message_id = starting_message_id
        total_messages = abs(end_message_id - starting_message_id) if end_message_id else starting_message_id
        file_count = 0
        deleted_messages = 0  

        progress_data = {
            "last_message_id": current_message_id,
            "indexing_active": True,
            "deleted_messages": deleted_messages  
        }

        progress_task = asyncio.create_task(
            update_progress(progress_message, starting_message_id, progress_data, user_id, user_name, total_messages)
        )
        
        destination_ids = [int(cid) for cid in destination_chats.split(",")]

        try:
            while indexing_active and (end_message_id is None or current_message_id >= end_message_id):
                if is_paused:
                    await asyncio.sleep(1)  
                    continue
                try:
                    message = await bot.get_messages(channel_id, current_message_id)
                    client_to_use = bot
                except (ChannelInvalid, ChannelPrivate) as e:
                    print(f"Bot cannot access channel. Trying with user client. - {e}")
                    message = await user_client.get_messages(channel_id, current_message_id)
                    client_to_use = user_client
                except MessageIdInvalid:
                    print(f"Message ID {current_message_id} is invalid (possibly deleted). Skipping...")
                    deleted_messages += 1
                    progress_data["deleted_messages"] = deleted_messages
                    current_message_id -= 1
                    continue

                await send_message_to_destinations(client_to_use, message, destination_ids, channel_id, current_message_id, progress_data)
                print(f"Sent message ID {current_message_id} to {destination_ids}")

                file_count += 1

                if file_count % 1500 == 0:
                    await asyncio.sleep(large_sleep_interval)
                else:
                    await asyncio.sleep(small_sleep_interval)

                if message.id == 1 or (end_message_id is not None and current_message_id <= end_message_id):
                    print("Reached the end or the target of the channel.")
                    break

                current_message_id -= 1
                progress_data["last_message_id"] = current_message_id

        except FloodWait as e:
            print(f"Rate limit exceeded. Sleeping for {e.value + 900} seconds")
            await asyncio.sleep(e.value + 900)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            indexing_active = False
            progress_data["indexing_active"] = False
            progress_task.cancel()  
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            
            elapsed_time = int(time.time() - start_time)
            del_msg_count_for_summery = progress_data["deleted_messages"]

            summary_text = (
                f"**Cloning Complete**\n"
                f"❒ Total Processed Messages: {file_count}\n"
                f"❒ Total Deleted Messages: {del_msg_count_for_summery}\n"
                f"❒ Total Time: {elapsed_time // 60}m {elapsed_time % 60}s\n"
                f"❒ Cloning from Channel: {channel_id}\n"
                f"❒ Processed to Chats: {', '.join(map(str, destination_ids))}\n"
                f"❒ User: {user_name} | ID: {user_id}"
            )
            await progress_message.edit_text("Cloning has been completed or stopped.")
            await bot.send_message(user_id, summary_text)

async def send_message_to_destinations(client, message, destination_ids, channel_id, current_message_id, progress_data):
    if do_forward:
        should_forward = (
            (clone_text and message.text) or 
            (clone_photos and message.photo) or 
            (clone_videos and message.video) or 
            (clone_documents and message.document) or 
            (clone_audio and message.audio) or 
            (clone_stickers and message.sticker)
        )

        if should_forward:
            for dest_id in destination_ids:
                try:
                    await client.forward_messages(chat_id=dest_id, from_chat_id=channel_id, message_ids=current_message_id)
                except MessageIdInvalid:
                    print(f"Cannot forward message ID {current_message_id} as it might have been deleted.")
                    progress_data["deleted_messages"] += 1
                    continue
    else:
        for dest_id in destination_ids:
            try:
                if message.text and clone_text:
                    await client.send_message(chat_id=dest_id, text=message.text)
                if message.photo and clone_photos:
                    await client.send_photo(chat_id=dest_id, photo=message.photo.file_id, caption=message.caption)
                if message.video and clone_videos:
                    await client.send_video(chat_id=dest_id, video=message.video.file_id, caption=message.caption)
                if message.document and clone_documents:
                    await client.send_document(chat_id=dest_id, document=message.document.file_id, caption=message.caption)
                if message.audio and clone_audio:
                    await client.send_audio(chat_id=dest_id, audio=message.audio.file_id, caption=message.caption)
                if message.sticker and clone_stickers:
                    await client.send_sticker(chat_id=dest_id, sticker=message.sticker.file_id)
            except MessageIdInvalid:
                print(f"Cannot send message ID {current_message_id} as it might have been deleted.")
                progress_data["deleted_messages"] += 1
                continue

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(
        "Welcome to the TeleCloner, A Supporter Plugin for Echo! Use /help for more info",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Repo 🔮", url="https://github.com/theseekerofficial/Echo")],
            [InlineKeyboardButton("Updates 📢", url="https://t.me/Echo_AIO")],
            [InlineKeyboardButton("Support Unit 💁‍♂️", url="https://t.me/ECHO_Support_Unit")]
        ])
    )

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    help_text = """
    **TeleCloner Help Guide**

    Here's how to use this bot:
    - Use `/gountil (message_id)` to set a specific end message ID for Cloning. | To get (message_id), consider this link in a channel (https://t.me/c/1842486073/692097) in this message (message_id) is 692097
    - **How Start**
        - Use /clone cmd as /clone {chat id} {message id} | Example - /clone -100123456789 123
                OR
        - Forward a message from any channel to start cloning.
    - Click "Stop Cloning 🚫" anytime to halt the cloning process.

    ⚠️ Your User session must be an member or an admin (Not nesessory to be an admin) in source channel to start the index process.
    """
    await message.reply(help_text)

@bot.on_message(filters.forwarded & filters.private)
async def message_handler(client, message: Message):
    global indexing_active, start_time
    if message.from_user.id in controller_ids:
        if message.forward_from_chat:
            if indexing_active:
                await message.reply("Another Cloning process is currently active. Please wait until it finishes.")
                return
            
            indexing_active = True
            start_time = time.time()

            channel_id = message.forward_from_chat.id
            original_message_id = message.forward_from_message_id
            user_id = message.from_user.id
            user_name = message.from_user.first_name or message.from_user.username

            end_message_id = target_message_id if target_message_id and original_message_id > target_message_id else None

            progress_message = await message.reply(
                "Initializing Cloning...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Stop Cloning 🚫", callback_data="stop_indexing")]
                ])
            )
            last_message_id = await fetch_and_send_content(channel_id, original_message_id, user_id, end_message_id, progress_message, user_name)
            indexing_active = False
    else:
        print("Ignored message from unauthorized user.")

@bot.on_message(filters.command("clone") & filters.private)
async def clone_command(client, message: Message):
    global indexing_active, start_time
    if message.from_user.id in controller_ids:
        args = message.command[1:]
        if len(args) < 2:
            await message.reply("Please provide both a chat ID and a starting message ID. Usage: /clone <chat_id> <message_id>")
            return

        try:
            chat_id = int(args[0])
            start_message_id = int(args[1])
        except ValueError:
            await message.reply("Invalid chat ID or message ID. Please ensure both are numeric.")
            return

        if indexing_active:
            await message.reply("Another Cloning process is currently active. Please wait until it finishes.")
            return

        indexing_active = True
        start_time = time.time()

        user_id = message.from_user.id
        user_name = message.from_user.first_name or message.from_user.username
        end_message_id = target_message_id if target_message_id and start_message_id > target_message_id else None
        codex_identifier = "C@K$y1vRpB@^nT*8wsrK!1hUGpTsf6UdpNN"

        progress_message = await message.reply(
            "Initializing Cloning...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Stop Cloning 🚫", callback_data="stop_indexing")]
            ])
        )

        await fetch_and_send_content(chat_id, start_message_id, user_id, end_message_id, progress_message, user_name)
        indexing_active = False
    else:
        await message.reply("You are not authorized to use this command.")

@bot.on_message(filters.command("gountil") & filters.private)
async def set_target_message(client, message: Message):
    if message.from_user.id in controller_ids:
        global target_message_id
        try:
            target_message_id = int(message.command[1])
            await message.reply(f"Will Clone until message ID {target_message_id}.")
        except IndexError:
            await message.reply("Please provide a valid message ID. Usage: /gountil <message_id>")
        except ValueError:
            await message.reply("Invalid number format. Please provide a valid message ID.")
    else:
        await message.reply("You are not authorized to set the target message ID.")

async def update_progress(message, start_message_id, progress_data, user_id, user_name, total_messages):
    global indexing_active, start_time, is_paused
    while progress_data["indexing_active"]:
        if is_paused:
            await asyncio.sleep(1)
            continue
        elapsed_time = int(time.time() - start_time)
        last_message_id = progress_data["last_message_id"]
        processed_messages = abs(last_message_id - start_message_id)
        deleted_messages = progress_data["deleted_messages"]
        percentage = (processed_messages / total_messages) * 100 if total_messages else 0
        
        eta = ((total_messages - processed_messages) * (small_sleep_interval + large_sleep_interval / 1500)) if total_messages else 0
        progress_bar = '■' * int(percentage // 10) + '□' * (10 - int(percentage // 10))
        
        progress_text = (
            f"❒ [{progress_bar}] {percentage:.2f}%\n"
            f"❒ Processed: {processed_messages} of {total_messages}\n"
            f"❒ Deleted Messages: {deleted_messages}\n"
            f"❒ ETA: {int(eta // 60)}m {int(eta % 60)}s\n"
            f"❒ Elapsed: {elapsed_time // 60}m {elapsed_time % 60}s\n"
            f"❒ S Plugin: TeleCloner\n"
            f"❒ Mode: #Cloning\n"
            f"❒ User: {user_name} | ID: {user_id}"
        )
        
        if not is_paused:
            await message.edit_text(progress_text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Pause Cloning ⏸️", callback_data="pause_cloning")],
                [InlineKeyboardButton("Stop Cloning 🚫", callback_data="stop_indexing")]
            ]))
        await asyncio.sleep(5)

@bot.on_callback_query(filters.regex("^stop_indexing$"))
async def stop_indexing_callback(client, callback_query):
    global indexing_active
    if callback_query.from_user.id in controller_ids:
        indexing_active = False
        await callback_query.answer("Cloning stopped by user.")
        await callback_query.message.edit_text("Cloning has been stopped by the user.")
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_callback_query(filters.regex("^pause_cloning$"))
async def pause_cloning_callback(client, callback_query):
    global is_paused
    if callback_query.from_user.id in controller_ids:
        is_paused = True
        await callback_query.answer("Cloning paused by user.")
        await callback_query.message.edit_text("Cloning has been paused. Press 'Resume' to continue.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Resume Cloning ▶️", callback_data="resume_cloning")]
        ]))
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_callback_query(filters.regex("^resume_cloning$"))
async def resume_cloning_callback(client, callback_query):
    global is_paused
    if callback_query.from_user.id in controller_ids:
        is_paused = False
        await callback_query.answer("Cloning resumed by user.")
        await callback_query.message.edit_text("Cloning has been resumed.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Pause Cloning ⏸️", callback_data="pause_cloning")],
            [InlineKeyboardButton("Stop Cloning 🚫", callback_data="stop_indexing")]
        ]))
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_message(filters.command("setcmds") & filters.user(list(controller_ids)))
async def set_bot_commands(client, message):
    commands = [
        ("start", "Start the bot"),
        ("help", "Get help with the bot"),
        ("gountil", "Set the target message ID for Cloning"),
        ("clone", "Start cloning from a specified chat and message ID")
    ]
    await client.set_bot_commands(commands)
    await message.reply("Bot commands have been set.")

# Run the bot
bot.run()
