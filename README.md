# ECHO v1.2.0 MAI2 #IM #NF #SP (Improvements/New Features/Supporter Plugins)

<p align="center">
    <a href="https://github.com/theseekerofficial/Echo">
        <kbd>
            <img width="450" src="https://telegra.ph/file/a73a7d59d4a139df59c16.jpg" alt="Echo">
        </kbd>
    </a>

<div align=center>

----

[![](https://img.shields.io/github/repo-size/theseekerofficial/Echo?color=blue&label=Repo%20Size&labelColor=333333)](#) [![](https://img.shields.io/github/commit-activity/m/theseekerofficial/Echo?logo=github&labelColor=333333&label=Github%20Commits&color=red)](#) [![](https://img.shields.io/github/license/theseekerofficial/Echo?style=flat&label=License&labelColor=333333&color=yellow)](#)|[![](https://img.shields.io/github/issues-raw/theseekerofficial/Echo?style=flat&label=Open%20Issues&labelColor=333333&color=purple)](#) [![](https://img.shields.io/github/issues-closed-raw/theseekerofficial/Echo?style=flat&label=Closed%20Issues&labelColor=333333&color=orange)](#) [![](https://img.shields.io/github/issues-pr-raw/theseekerofficial/Echo?style=flat&label=Open%20Pull%20Requests&labelColor=333333&color=lightgrey)](#) [![](https://img.shields.io/github/issues-pr-closed-raw/theseekerofficial/Echo?style=flat&label=Closed%20Pull%20Requests&labelColor=333333&color=green)](#)
:---:|:---:|
[![](https://img.shields.io/github/languages/count/theseekerofficial/Echo?style=flat&label=Total%20Languages&labelColor=333333&color=teal)](#) [![](https://img.shields.io/github/languages/top/theseekerofficial/Echo?style=flat&logo=python&labelColor=333333&color=lightblue)](#) [![](https://img.shields.io/github/last-commit/theseekerofficial/Echo?style=flat&label=Last%20Commit&labelColor=333333&color=9cf)](#) [![](https://badgen.net/github/branches/theseekerofficial/Echo?label=Total%20Branches&labelColor=333333&color=violet)](#)|[![](https://img.shields.io/github/forks/theseekerofficial/Echo?style=flat&logo=github&label=Forks&labelColor=333333&color=ff69b4)](#) [![](https://img.shields.io/github/stars/theseekerofficial/Echo?style=flat&logo=github&label=Stars&labelColor=333333&color=yellowgreen)](#)
[![](https://img.shields.io/badge/ECHO%20Updates%20Channel-Join-9cf?style=for-the-badge&logo=telegram&logoColor=blue&style=flat&labelColor=333333)](https://t.me/Echo_AIO) |[![](https://img.shields.io/badge/ECHO%20Support%20Unit-Join-9cf?style=for-the-badge&logo=telegram&logoColor=blue&style=flat&labelColor=333333)](https://t.me/ECHO_Support_Unit) |

</div>

---

## Readme Contents

# Introduction

❓ **Supporter Plugins** are auxiliary scripts that work in conjunction with the main Echo Environment, designed to enhance the functionality of the primary plugins used by an Echo bot. These plugins are separate codes that do not run directly within the main Echo Environment but are managed through it. Here’s a bit more detail about how they operate and the available plugins

❓ Supporter Plugins utilize the codecapsule.py module within the Echo client, ensuring seamless integration and control from the main Echo Environment.

❓ They use Linux screen sessions to remain active and operational, ensuring they can continue running independently without requiring constant user intervention.


# Available Supporter Plugins 

1. **TeleFileDex.py** ⬇️
   - Related Main Plugin - Doc Spotter
   - Since the main Doc Spotter Plugin can handle real-time indexing. this plugin for indexing the history of a chat (Channel or Group)
   - Only have access to pre-authorized users only
   - Can not run directly, only should run via an Echo Client

2. **TeleCloner.py** 💽
   - Related Main Plugin - Clonegram
   - Since the main Clonegram Plugin can handle real-time Cloning. this plugin for clone the history of a chat (Channel or Group)
   - Support multiple destination chats
   - Only have access to pre-authorized users only
   - Can not run directly, only should run via an Echo Client

      
3. **SafeSync.py** 🔁
   - Related Main Plugin - Not specific. Important for Echo Client
   - Automatically backup source database for the pre-setup period
   - Can not run directly, only should run via an Echo Client

## *Difference between non_us_version (Non-User Session Version) vs normal version*
### non_us_version
   - Not Using user session strings. So no risking losing your telegram account
   - Both Bots must be an admins of the source channel.
   - Can work at high speed. Recommended: 3 files for 1 sec
   - ⚠️ Remove 1st line comment (# Rename this file as....) and remove "_non_us_version" prefix from the file name before send it to Echo Client 

### Normal Version
   - Uses User Sessions, have some risk about losing user account
   - User account is no need to be an admin in the channel. Simply join your user account and start indexing files from any channel.
   - Can work at normal speed. To reduce flood wait and account bans. Recommended: 1 file for 1 sec 

# Commands

## TeleFileDex.py
   - `/start` - Start the bot
   - `/help` - Get help message
   - `/index` - Initiate a Index Task | Example usage: /index {chat_id} {msg_id} --> /index -100123456789 123 

## TeleCloner.py
   - `/start` - Start the bot
   - `/help` - Get help message
   - `/clone` - Initiate a Clone Task | Example usage: /clone {chat_id} {msg_id} --> /clone -100123456789 123 

## SafeSync.py
   - No cmd for this plugin

# Configure Suporter Plugins

## TeleFileDex.py
![telefiledex1](https://telegra.ph/file/82c495384777eaf00cd5b.jpg)

1) `MONGODB_URI` - Enter Your Echo Client's Mongodb URI
2) `api_id` - Entry your API ID here. you can get your id from https://my.telegram.org/
3) `api_hash` - Entry your API Hash here. you can get your hash from https://my.telegram.org/
4) `bot_token` - Enter a Bot Token. ⚠️ Remember, do not enter your Echo Client Bot Token here. Enter a new bot token here
5) `user_session_string` - Enter your `Pyrogram` user session string here.
6) `small_sleep_interval` - Sleep time between every two indexing in seconds. (Flood control and rate limit control system). Recommended Value - `1` | Change according to your requirement
7) `large_sleep_interval` - Sleep time between every 150 files in seconds. (Flood control and rate limit control system). Recommended Value - `300` to `7200` | Change according to your requirement
8) `controller_ids` - User IDs of the users who can use this supporter plugin

## TeleCloner.py
![telecloner1](https://telegra.ph/file/59af0e74ce65015e18988.jpg)

1) `api_id` - Entry your API ID here. you can get your id from https://my.telegram.org/
2) `api_hash` - Entry your API Hash here. you can get your hash from https://my.telegram.org/
3) `bot_token` - Enter a Bot Token. ⚠️ Remember, do not enter your Echo Client Bot Token here. Enter a new bot token here
4) `user_session_string` - Enter your `Pyrogram` user session string here.
5) `destination_chats` - Comma-separated destination chat IDs list
6) `do_forward` - Set True if you want to forward messages. Set False if you want to send messages instead of forwarding (Recommended: True)
7) `small_sleep_interval` - Sleep time between every two indexing in seconds. (Flood control and rate limit control system). Recommended Value - `1` | Change according to your requirement
8) `large_sleep_interval` - Sleep time between every 150 files in seconds. (Flood control and rate limit control system). Recommended Value - `300` to `7200` | Change according to your requirement
9) `controller_ids` - User IDs of the users who can use this supporter plugin
10) `clone_text | clone_photos | clone_videos | clone_documents | clone_audio | clone_stickers` - Select media types for cloning

## SafeSync.py
![safesync1](https://telegra.ph/file/6fdf0df22fb764dc843a1.jpg)

1) `SOURCE_DB_URI` - Enter Your Source Mongo DB URI
2) `DESTINATION_DB_URI` - Entry your Destination Mongo DB URI
3) `BACKUP_AT_EVERY` - Initiate backup and restore at every... (Enter in minutes)
4) `PATH_FOR_BACKUP_FILE` - A location for temp backup file

# Deployment

### ⚠️ Supporter plugins can only run on an Echo Client hosted on a VPS.

~Pre-Requiremtnts
 - Make sure to install Python 3.10 installed in your Ubuntu system. If you only have a version like Python 3.8, Install Python 3.10 too

### Run in an Echo Client
-------------------------------------------------------------------------------------

~Deploying Steps
1. Give a Star to `https://github.com/theseekerofficial/Echo` 😉
2. Fork the Repo
3. Fill in the configurations as mentioned above and save the Supporter Plugin `.py` file
4. Send /codecapsule command in your Echo bot client
5. Click "`Run a Supporter Plugin`" button and send you saved `.py` file to bot
6. Wait few seconds and your supporter plugin is up!
7. To stop the plugin user Stop button provided by the Echo or go to "Active Supporter Plugin(s)" menu to terminate sessions. 
   
# Creator Details

Crafted🔨 with 🖤 by 𝓣𝓱𝓮 𝓢𝓮𝓮𝓴𝓮𝓻

- **Name:** 𝓣𝓱𝓮 𝓢𝓮𝓮𝓴𝓮𝓻
- **Telegram:** [@MrUnknown114](https://t.me/MrUnknown114)
- **GitHub:** [GitHub Profile](https://github.com/theseekerofficial)

![LICENSE](https://www.gnu.org/graphics/gplv3-127x51.png) 

Proofreaded by, [@The_Seeker_116](https://t.me/The_Seeker_116) 📖✔️

Enhanced by,

    - OpenAI's GPT3.5 & GPT-4 🪄
    - Google Gemini ✨
    - Codeium 🦾

Feel free to connect with the creator for inquiries or support related to Echo in [ECHO Support Unit](https://t.me/ECHO_Support_Unit).
Enjoy using Echo and stay organized!

#ECHO #EchoAIO #Made_From_Scratch
