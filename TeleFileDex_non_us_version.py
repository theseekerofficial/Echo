# ------------------------------------------------- Rename this file as TeleFileDex.py and remove this line before send to Echo Client -------------------------------------------------
import os
import sys
import time
import asyncio
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# Database setup
MONGODB_URI = "" # Enter Your Echo Client's Mongodb URI
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['Echo_Doc_Spotter'] # Do not change

# Bot and User Session Configuration
api_id = ''  # Your api_id
api_hash = ''  # Your api_hash
bot_token = ''  # Your bot token. ⚠️ Remember, do not enter your Echo Client Bot Token here. Enter a new bot token here
worker_bot_token = ''  # Enter another new bot token

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
# Pause State Controller (Do Not Edit These values!)
is_paused = False

bot = Client("bot", api_id, api_hash, bot_token=bot_token)
worker_bot = Client("session_name", api_id, api_hash, bot_token=worker_bot_token)

if __name__ == "__main__":
    if os.getenv('RUNNING_THROUGH_CODECAPSULE') != 'true':
        print("This script should not be run directly. Please use an Echo Client to run this script.")
        sys.exit(1)

async def fetch_and_store_file_info(channel_id, starting_message_id, user_id, end_message_id=None, progress_message=None, user_name=''):
    global indexing_active, start_time, is_paused
    async with worker_bot:
        current_message_id = starting_message_id
        total_messages = abs(end_message_id - starting_message_id) if end_message_id else starting_message_id
        file_count = 0
        deleted_messages = 0

        user_collection = db[f"DS_collection_{user_id}"]

        progress_data = {
            "last_message_id": current_message_id,
            "indexing_active": True
        }

        progress_task = asyncio.create_task(
            update_progress(progress_message, starting_message_id, progress_data, user_id, user_name, total_messages)
        )

        try:
            while indexing_active and (end_message_id is None or current_message_id >= end_message_id):
                if is_paused:
                    await asyncio.sleep(1)
                    continue

                message = None
                try:
                    message = await bot.get_messages(channel_id, current_message_id)
                except (ChannelInvalid, ChannelPrivate):
                    try:
                        print("Can not access message using main bot client, try using worker bot client")
                        message = await worker_bot.get_messages(channel_id, current_message_id)
                    except Exception as e:
                        print(f"Failed to fetch with worker bot client: {e}")
                        break

                if message:
                    file_info = {}
                    is_media_message = False

                    if message.document:
                        file_info = {
                            "file_id": message.document.file_id,
                            "file_name": message.document.file_name,
                            "file_size": message.document.file_size,
                            "file_type": "document",
                            "mime_type": message.document.mime_type,
                            "caption": message.caption
                        }
                        is_media_message = True
                    elif message.video:
                        file_info = {
                            "file_id": message.video.file_id,
                            "file_name": message.video.file_name,
                            "file_size": message.video.file_size,
                            "file_type": "video",
                            "mime_type": message.video.mime_type,
                            "caption": message.caption
                        }
                        is_media_message = True
                    elif message.photo:
                        file_info = {
                            "file_id": message.photo.file_id,
                            "file_name": message.caption if message.caption else "Unknown",
                            "file_size": message.photo.file_size,
                            "file_type": "photo",
                            "mime_type": "image/jpeg",
                            "caption": message.caption
                        }
                        is_media_message = True
                    elif message.audio:
                        file_info = {
                          "file_id": message.audio.file_id,
                          "file_name": message.audio.file_name,
                          "file_size": message.audio.file_size,
                          "file_type": "audio",
                          "mime_type": message.audio.mime_type,
                          "caption": message.caption
                        }
                        is_media_message = True

                    if is_media_message:
                        user_collection.insert_one(file_info)
                        print(f"Stored info: {file_info}")
                        file_count += 1

                else:
                    deleted_messages += 1
                
                if file_count % 150 == 0:
                    await asyncio.sleep(large_sleep_interval)
                else:
                    await asyncio.sleep(small_sleep_interval)

                if message and (message.id == 1 or (end_message_id is not None and current_message_id <= end_message_id)):
                    print("Reached the end or the target of the channel.")
                    break

                current_message_id -= 1
                progress_data["last_message_id"] = current_message_id

        except FloodWait as e:
            print(f"Rate limit exceeded. Sleeping for {e.value + 900} seconds")
            await asyncio.sleep(e.value + 900)
        finally:
            indexing_active = False
            codex_identifier = "k$#jCojZ8siWWEdEy1^lu%2YsmA1cH5y0LG"
            progress_data["indexing_active"] = False
            progress_task.cancel()  
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
                
            elapsed_time = int(time.time() - start_time)
            summary_text = (
                f"**Indexing Complete (or stopped.)**\n"
                f"❒ Total Processed Messages: {file_count}\n"
                f"❒ Total Deleted Messages: {deleted_messages}\n"
                f"❒ Total Time: {elapsed_time // 60}m {elapsed_time % 60}s\n"
                f"❒ Indexing from Channel: {channel_id}\n"
                f"❒ User: {user_name} | ID: {user_id}"
            )
            await progress_message.edit_text(summary_text)

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(
        "Welcome to the TeleFileDex, A Supporter Plugin for Echo! Use /help for more info",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Repo 🔮", url="https://github.com/theseekerofficial/Echo")],
            [InlineKeyboardButton("Updates 📢", url="https://t.me/Echo_AIO")],
            [InlineKeyboardButton("Support Unit 💁‍♂️", url="https://t.me/ECHO_Support_Unit")]
        ])
    )

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    help_text = """
    **TeleFileDex Help Guide**

    Here's how to use this bot:
    - Use `/gountil (message_id)` to set a specific end message ID for indexing. | To get (message_id), consider this link in a channel (https://t.me/c/1842486073/692097) in this message (message_id) is 692097
    - How to initiate a index task!
        - Forward a message from any channel to start indexing.
        OR
        - send a chat ID and message ID using /index cmd (e.g. `/index {chat_id} {msg_id}` | `/index -100123456789 123`)
    - Click "Stop Indexing 🚫" anytime to halt the indexing process.

    ⚠️ Both Your bots must be an admin in the source channel to start the indexing process.
    """
    await message.reply(help_text)

@bot.on_message(filters.forwarded & filters.private)
async def message_handler(client, message: Message):
    global indexing_active, start_time
    if message.from_user.id in controller_ids:
        if message.forward_from_chat:
            if indexing_active:
                await message.reply("Another indexing process is currently active. Please wait until it finishes.")
                return
            
            indexing_active = True
            start_time = time.time()

            channel_id = message.forward_from_chat.id
            original_message_id = message.forward_from_message_id
            user_id = message.from_user.id
            user_name = message.from_user.first_name or message.from_user.username

            end_message_id = target_message_id if target_message_id and original_message_id > target_message_id else None

            progress_message = await message.reply(
                "Initializing indexing...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Stop Indexing 🚫", callback_data="stop_indexing")]
                ])
            )
            last_message_id = await fetch_and_store_file_info(channel_id, original_message_id, user_id, end_message_id, progress_message, user_name)
            indexing_active = False
    else:
        print("Ignored message from unauthorized user.")

@bot.on_message(filters.command("index") & filters.private)
async def index_command(client, message: Message):
    global indexing_active, start_time
    if message.from_user.id in controller_ids:
        try:
            _, chat_id, msg_id = message.text.split()
            chat_id = int(chat_id) 
            msg_id = int(msg_id) 

            if indexing_active:
                await message.reply("Another indexing process is currently active. Please wait until it finishes.")
                return

            indexing_active = True
            start_time = time.time()

            user_id = message.from_user.id
            user_name = message.from_user.first_name or message.from_user.username

            end_message_id = target_message_id if target_message_id and msg_id > target_message_id else None

            progress_message = await message.reply(
                "Initializing indexing...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Stop Indexing 🚫", callback_data="stop_indexing")]
                ])
            )

            await fetch_and_store_file_info(chat_id, msg_id, user_id, end_message_id, progress_message, user_name)
            indexing_active = False

        except ValueError:
            await message.reply("Invalid format. Usage: /index <chat_id> <msg_id>")
        except IndexError:
            await message.reply("Please provide both chat_id and msg_id. Usage: /index <chat_id> <msg_id>")
    else:
        await message.reply("You are not authorized to initiate the indexing process.")

@bot.on_message(filters.command("gountil") & filters.private)
async def set_target_message(client, message: Message):
    if message.from_user.id in controller_ids:
        global target_message_id
        try:
            target_message_id = int(message.command[1])
            await message.reply(f"Will index until message ID {target_message_id}.")
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
        percentage = (processed_messages / total_messages) * 100 if total_messages else 0
        
        eta = ((total_messages - processed_messages) * (small_sleep_interval + large_sleep_interval / 150)) if total_messages else 0
        progress_bar = '■' * int(percentage // 10) + '□' * (10 - int(percentage // 10))
        
        progress_text = (
            f"❒ [{progress_bar}] {percentage:.2f}%\n"
            f"❒ Processed: {processed_messages} of {total_messages}\n"
            f"❒ ETA: {int(eta // 60)}m {int(eta % 60)}s\n"
            f"❒ Elapsed: {elapsed_time // 60}m {elapsed_time % 60}s\n"
            f"❒ S Plugin: TeleFileDex\n"
            f"❒ Mode: #Indexing\n"
            f"❒ User: {user_name} | ID: {user_id}"
        )
        
        if not is_paused:
            await message.edit_text(progress_text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Pause Indexing ⏸️", callback_data="pause_indexing")],
                [InlineKeyboardButton("Stop Indexing 🚫", callback_data="stop_indexing")]
            ]))
        await asyncio.sleep(5)

@bot.on_callback_query(filters.regex("^pause_indexing$"))
async def pause_indexing_callback(client, callback_query):
    global is_paused
    if callback_query.from_user.id in controller_ids:
        is_paused = True
        await callback_query.answer("Indexing paused by user.")
        await callback_query.message.edit_text("Indexing has been paused. Press 'Resume' to continue.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Resume Indexing ▶️", callback_data="resume_indexing")]
        ]))
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_callback_query(filters.regex("^resume_indexing$"))
async def resume_indexing_callback(client, callback_query):
    global is_paused
    if callback_query.from_user.id in controller_ids:
        is_paused = False
        await callback_query.answer("Indexing resumed by user.")
        await callback_query.message.edit_text("Indexing has been resumed.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Pause Indexing ⏸️", callback_data="pause_indexing")],
            [InlineKeyboardButton("Stop Indexing 🚫", callback_data="stop_indexing")]
        ]))
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_callback_query(filters.regex("^stop_indexing$"))
async def stop_indexing_callback(client, callback_query):
    global indexing_active
    if callback_query.from_user.id in controller_ids:
        indexing_active = False
        await callback_query.answer("Indexing stopped by user.")
        await callback_query.message.edit_text("Indexing has been stopped by the user.")
    else:
        await callback_query.answer("Do not touch this button!", show_alert=True)

@bot.on_message(filters.command("setcmds") & filters.user(list(controller_ids)))
async def set_bot_commands(client, message):
    commands = [
        ("start", "Start the bot"),
        ("help", "Get help with the bot"),
        ("gountil", "Set the target message ID for indexing")
    ]
    await client.set_bot_commands(commands)
    await message.reply("Bot commands have been set.")

# Run the bot
bot.run()
