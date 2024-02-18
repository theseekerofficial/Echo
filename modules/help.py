from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CallbackContext

def help_command(update, context: CallbackContext) -> None:
    # Send the photo with the inline keyboard
    photo_path = 'assets/help.jpg' 
    caption = """Ah! The help menu, my fav! Select Help Category to Proceed:
    
_Echo the Multifunctional User assistant has arrived to save your schedule and make your life easier! Let's unlock your full memory potential with these magical features_✨"""

    keyboard = [
        [
            InlineKeyboardButton("Basic Commands", callback_data='basic'),
            InlineKeyboardButton("Reminder Commands", callback_data='reminder'),
        ],
        [
            InlineKeyboardButton("Gemini AI Commands", callback_data='gemini'),
            InlineKeyboardButton("Broad/Schedu cast Commands", callback_data='brsc'),
        ],
        [
            InlineKeyboardButton("ChatBot Commands", callback_data='chatbot_help'),
            InlineKeyboardButton("Calculator Commands", callback_data='calculator_help'),
        ],
        [
            InlineKeyboardButton("Telegraph Commands", callback_data='tgphup'),
            InlineKeyboardButton("Logo Gen Commands", callback_data='logogen_help'),
        ],
        [
            InlineKeyboardButton("DocSpotter Commands", callback_data='doc_spotter_help'),
            InlineKeyboardButton("Info Commands", callback_data='info_help'),
        ],
        [
            InlineKeyboardButton("Commit Detector Commands", callback_data='commit_detector_help'),
            InlineKeyboardButton("Misc Commands", callback_data='misc'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the photo with caption and the inline keyboard
    message = update.message.reply_photo(
        photo=open(photo_path, 'rb'),
        caption=caption,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )

    # Save the message ID and an empty stack in user data to edit it later
    context.user_data['help_message_id'] = message.message_id
    context.user_data['category_stack'] = []

def handle_help_button_click(update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data

    # Define the messages for each button
    messages = {
           'basic': "*Basic Commands to Start Echo and manege it⚙️*\n\n"
                 "/start - Press this button to get this party started and receive a warm welcome!💫\n"
                 "/help - Feeling a bit lost? I'm always here to lend a helping hand!  Just ask, and I'll guide you through my powers.💁\n"
                 "/bsettings - Config Echo!⚙️ (OWNER Only)\n"
                 "/restart - Start Fresh Again. Restart Echo and Get Latest Updates from [Official Repo](https://github.com/theseekerofficial/Echo) (OWNER Only)🔁\n\n[Echo-Verse♾️](https://t.me/Echo_AIO)",
        'reminder': "*Welcome to Echo's Reminder Function Related Commands for your reminder manage⚙️*\n\n"
                    "_⭐Reminder Tip: Ready to ditch the default dings and bongs? Turn your reminders into sonic experiences with Echo's custom ringtone magic! Type /ringtones for more info_\n\n"
                    "_Recurring Reminder Support available for various time periods in /setreminder command_\n\n"
                    "/setreminder - Set a reminder for yourself using the modern method.🧬\n"
                    "/sr - Set a reminder for yourself using the traditional method.⏰\n"
                    "/myreminders - Show your existing reminders.📃\n"
                    "/delreminder - Delete a specific reminder.🗑️\n"
                    "/settimezone - Set your time zone.🌎\n"
                    "/editreminders - Edit your existing reminders.✂️\n\n🌟Easily find your timezone using [this link](https://telegra.ph/Choose-your-timezone-02-16)\n\n[Echo-Verse♾️](https://t.me/Echo_AIO)",
            'misc': "*Welcome to Echo's other misc comands⚙️*\n\n"
                "/ringtones - Explore sample ringtones.🎵\n"
                "/id - See User/Chat info 📜\n"
                "/database - See my mongoDB database stats📊\n"
                "/moreinfo - Get more information about the bot.📚\n\n[Echo-Verse♾️](https://t.me/Echo_AIO)",
            'brsc': """*Welcome to Echo's Announcement modules⚙️*\n\n"""
                 "/broadcast - Initiate a instant broadcast📢\n"
                 "/scheducast - Scheduled a broadcast for the future!🔮\n"
                 "/scd - The cmd used for capture schducast date and time. Use /scheducast to get this step🪜\n"
                 "/scm - The cmd used for capture schducast message. Use /scheducast to get this step🪜\n\n[Echo-Verse♾️](https://t.me/Echo_AIO)",
          'gemini': """*Welcome to Echo's Gemini AI Plugin*\n\n"""
                 """⚠️This feature might be currently unavailable.
Because the person (Not the Creator) who deployed the bot can disable certain plugins as needed.
🔒 Your privacy and user experience are our top priorities! 🔒\n\n"""
                 "/gemini - Start chat with gemini AI💬\n"
                 "/mygapi - Get your Google Gemini API from [this link](https://aistudio.google.com/app/apikey) and send it to bot using (/mygapi yourapikey) format✅\n"
                 "/analyze4to - Start analyze your image using Gemini-Pro-Vision📸\n"
                 "/showmygapi - To see you current API stored in database🔗\n"
                 "/delmygapi - Delete your Google API🚮\n\n"
                 "[Echo-Verse♾️](https://t.me/Echo_AIO)",
 'calculator_help': """*Welcome to Echo's Calculator Plugin🧩*\n\n"""
                 "/calculator - To get calculator menu 🧮\n"
                 "/cal - Short cmd for /calculator cmd🔮\n\n"
                 "Most of the calculators in Echo use Telegram Inline buttons for gathering inputs. However, there are only /calculator and /cal commands available for this plugin.✅\n"
                 "You can find more informative help note in each calculator.🚀\n\n"
                 "[Echo-Verse♾️](https://t.me/Echo_AIO)",
          'tgphup': """*Welcome to Echo's Telegraph Upload Plugin🧩*\n\n"""
                 "Here is the command list for this plugin\n"
                 "/uptotgph - Reply to any Image as /uptotgph to initiate upload process🔮\n\n"
                 "Telegraph Upload Plugin is a simple plugin in the Echo. So currently it's only available /uptotgph command only, For now!.🚀✅\n\n"
                 "[Echo-Verse♾️](https://t.me/Echo_AIO)",
    'logogen_help': """*Welcome to Echo's Logo Gen Plugin🧩*\n\n"""
                 "⚠️ This plugin is still under development, and more improvements are yet to come.\n\n"
                 "/logogen - Start Crafting Your Logo🎨🖌️\n\n"
                 """🔰Describe how you want to create your logo. For an example let's think you want to get a logo for Echo in Red font in Black Background. Then you need to send cmd as `/logogen Red Echo in Black Background`\n\n"""
                 """🔰After You send cmd, the bot will show the "Select a Font for logo Generate" menu with Font Buttons. Choose your desired font for your logo📝\n"""
                 """🔰After, the bot will ask you about the "Graphics category", "Graphics pattern", "Font Size" and "Frame Selection". Choose your favorite options for creating your logo.🪄\n\n"""
                 "⚜️Explore all fonts, Graphics, Patterns, Font Sizes, and Frames to uncover the perfect match that reflects your style and uniqueness.✨\n"
                 "⚜️Refer Echo's [Official Repo wiki](https://github.com/theseekerofficial/Echo/wiki) to learn how to add your own Fonts, Graphics and Frame Templates!✨\n\n"
                 "[Echo-Verse♾️](https://t.me/Echo_AIO)",
'doc_spotter_help': """🚀 *Echo's Doc Spotter Comprehensive Guide*

*Admins:*
1. *Setup*: Add Echo bot as admin in your channel/group.
2. *Activate*: Send the unique channel/group ID to Echo.
3. *Command*: Main cmd is /docspotter

*Users:*
*Search*: Just type any document/media name or keywords in the configured group.
*Results*: Echo lists all matching files.
*Access*: Click on your desired document from Echo’s list to get it in PM.
*F-Sub Requirement?*: Follow Echo's prompt to join necessary chats.

*Features:*
🗂 *Robust Indexing*: Echo smartly indexes files for quick retrieval.
🔍 *Effortless Searching*: Find exactly what you need with simple keywords.
📥 *Instant Access*: Receive files directly in PM for privacy.
🎥 *IMDb Insights*: For movie and TV files, Echo fetches IMDb details.
⚙️ *Inline Management*: Admins can easily manage indexing settings via inline buttons.
🔄 *Pagination*: Navigate through search results with 'Prev' and 'Next'.

[Echo-Verse♾️](https://t.me/Echo_AIO)""",
       'info_help': """📘 *The `/info` command can be used in several ways to retrieve information about users,bots and chats within Telegram:*

1️⃣ *Get Your Info*
Simply send `/info` in a private chat with the bot, and it will return your Telegram information, including your user ID, username (if any), and other relevant details.

2️⃣ *Get Info of Another User, Bot or chat*
Forward a user,bot or chat message to Echo's PM. Reply to it with `/info`. The bot will provide information about the user, bot or chat you replied to, including their ID, username, and more.

3️⃣ *Fetch Information Using Username or User ID*
You can also use `/info` followed by a username (e.g., `/info @username`) or a Telegram user ID (e.g., `/info 123456789`) to get information about that particular user or chat.

🔍 *More*
Maybe some chat's info not available due to privacy settings.

🤖 *Echo and Privacy*
Remember, Echo respects user privacy and Telegram's API limitations. Some information might not be retrievable in certain contexts due to these restrictions.

[Echo-Verse♾️](https://t.me/Echo_AIO)
""",
   'chatbot_help' : """🤖 *Welcome to Echo Chatbot!* 🗨️

_How to Use:_🪄

1. *Activate Chatbot:*
   - Use `/chatbot` to enable or disable the chatbot feature. 💬

2. *Chatting with the Bot:*
   - Once the chatbot is activated, start sending messages like you would in any chat.
   - The bot will respond to your messages using AI-generated content. 🤖

3. *API Key Setup:*
   - If you didn't setup and API key, use `/mygapi` command to configure your API key. 🔑
   - To get one go to [this link](https://aistudio.google.com/app/apikey).
   - After that click "Create API Key" button and copy your api
   - Now Send it along with /mygapi cmd. (E.g. `/mygapi 094t3h8g43209nhgvf4098t3gnhv8598gbnhe`)

4. *Getting Help:*
   - If you encounter any issues or need assistance, type `/help` to get guidance. ℹ️

5. *Enjoy Conversations:*
   - Have fun chatting with Echo Chatbot! Engage in conversations and explore its capabilities. 🎉

You can always deactivate the chatbot feature when you want. Just use `/chatbot` command again.

*Remember, Echo's Chat bot can reply to anything you send. I mean ANYTHING!*😉

[Echo-Verse♾️](https://t.me/Echo_AIO)
""",
   'commit_detector_help' : """*Commit Detector Feature Overview* 🔄

The *Commit Detector* is an exclusive feature tailored for the Echo's deployment owners, offering real-time monitoring of GitHub repositories for new commits.

🛠️ *Setup & Configuration:*
- `GH_CD_URLS`: A comma-separated list of GitHub repository URLs. Format - `theseekerofficial/Echo`
- `GH_CD_CHANNEL_IDS`: Telegram channel IDs where updates are sent, also comma-separated.
- `GH_CD_PAT`: Optional Personal Access Token for GitHub to boost your API rate limit and use authenticated requests.

🔄 *Operational Workflow:*
1. *Fetching Commits*: The bot periodically checks for the latest commits in the specified repositories.
2. *Commit Detection*: It detects new commits by comparing SHAs with the stored ones in the MongoDB `GH_Commit_Detector` collection.
3. *Notification*: For any new commit found, it sends a detailed update to the specified Telegram channels.

This feature is a powerful tool for staying updated with GitHub repository changes directly within Telegram

[Echo-Verse♾️](https://t.me/Echo_AIO)
"""
    }

    # Get the message for the clicked button
    message_text = messages.get(data, "Sorry, no information available for this category.")

    # Add a "Back" button to go back to the main menu
    keyboard = [[InlineKeyboardButton("Back", callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the detailed help message with the "Back" button
    query.edit_message_caption(
        caption=message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )

    # Save the current category in user data for "Back" button handling
    context.user_data['category_stack'].append(data)

def handle_back_button_click(update, context: CallbackContext) -> None:
    # Get the current category stack from user data
    category_stack = context.user_data.get('category_stack', [])

    if category_stack:
        # Pop the previous category from the stack
        previous_category = category_stack.pop()

        # Get the inline keyboard for the previous category
        previous_keyboard = get_inline_keyboard_for_category(previous_category)

        # Edit the message back to the original caption with the inline keyboard
        update.callback_query.edit_message_caption(
            caption="""Ah! The help menu, my fav! Select Help Category to Proceed:
    
Echo the Multifunctional User assistant has arrived to save your schedule and make your life easier! Let's unlock your full memory potential with these magical commands✨""",
            reply_markup=previous_keyboard
        )
    else:
        # If the stack is empty, edit back to the main menu
        update.callback_query.edit_message_caption(
            caption="""Ah! The help menu, my fav! Select Help Category to Proceed:
    
Echo the Multifunctional User assistant has arrived to save your schedule and make your life easier! Let's unlock your full memory potential with these magical commands✨""",
            reply_markup=get_inline_keyboard_for_category(None)
        )

    # Update the category stack in user data
    context.user_data['category_stack'] = category_stack

# Helper function to get the inline keyboard for a specific category
def get_inline_keyboard_for_category(category):
    keyboard = [
        [
            InlineKeyboardButton("Basic Commands", callback_data='basic'),
            InlineKeyboardButton("Reminder Commands", callback_data='reminder'),
        ],
        [
            InlineKeyboardButton("Gemini AI Commands", callback_data='gemini'),
            InlineKeyboardButton("Broad/Schedu cast Commands", callback_data='brsc'),
        ],
        [
            InlineKeyboardButton("ChatBot Commands", callback_data='chatbot_help'),
            InlineKeyboardButton("Calculator Commands", callback_data='calculator_help'),
        ],
        [
            InlineKeyboardButton("Telegraph Commands", callback_data='tgphup'),
            InlineKeyboardButton("Logo Gen Commands", callback_data='logogen_help'),
        ],
        [
            InlineKeyboardButton("DocSpotter Commands", callback_data='doc_spotter_help'),
            InlineKeyboardButton("Info Commands", callback_data='info_help'),
        ],
        [
            InlineKeyboardButton("Commit Detector Commands", callback_data='commit_detector_help'),
            InlineKeyboardButton("Misc Commands", callback_data='misc'),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)
