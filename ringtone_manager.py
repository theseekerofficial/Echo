import os
from telegram import Update
from telegram.ext import CallbackContext

# Function to handle the /ringtone command
def send_ringtones(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    ringtone_files = ["ringtone1.mp3", "ringtone2.mp3", "ringtone3.mp3", "ringtone4.mp3"]

    if update.effective_chat.type == 'private':
        for ringtone_file in ringtone_files:
            ringtone_path = os.path.join("ringtones", ringtone_file)
            with open(ringtone_path, "rb") as file:
                context.bot.send_audio(chat_id=user_id, audio=file)

        # Send a text message after sending ringtones
        context.bot.send_message(chat_id=user_id, text="""✨Just follow these simple steps to set a custom ringtone for Echo;\n\n🎶For custom ringtones, you can use either Echo's default ringtone provided above or any other audio file you want. However, make sure to save/download them to your device before setting up them as custom ringtone.\n\n♾️Tap that menu button (the three dots in the top right). ⋮\n♾️Hit "Mute," then unleash your inner audiophile with "Customize"\n♾️Scroll down to "General" and tap on "Sound"\n♾️Now is the fun part! Pick a ringtone that will make your ears perk up. Do not settle for the usual suspects, explore the uncommon realm!🪄\n\n💥Boom!  Your reminders just got a serious upgrade. No more snoozing through generic beeps, now they will be an auditory adventure! Ready to conquer forgetfulness with style? Let's do this!""")

    elif update.effective_chat.type in ['group', 'supergroup']:
        for ringtone_file in ringtone_files:
            ringtone_path = os.path.join("ringtones", ringtone_file)
            with open(ringtone_path, "rb") as file:
                context.bot.send_audio(chat_id=chat_id, audio=file)

        # Send a text message after sending ringtones
        context.bot.send_message(chat_id=chat_id, text="""✨Just follow these simple steps to set a custom ringtone for Echo;\n\n🎶For custom ringtones, you can use either Echo's default ringtone provided above or any other audio file you want. However, make sure to save/download them to your device before setting up them as custom ringtone.\n\n♾️Tap that menu button (the three dots in the top right). ⋮\n♾️Hit "Mute," then unleash your inner audiophile with "Customize"\n♾️Scroll down to "General" and tap on "Sound"\n♾️Now is the fun part! Pick a ringtone that will make your ears perk up. Do not settle for the usual suspects, explore the uncommon realm!🪄\n\n💥Boom!  Your reminders just got a serious upgrade. No more snoozing through generic beeps, now they will be an auditory adventure! Ready to conquer forgetfulness with style? Let's do this!""")
