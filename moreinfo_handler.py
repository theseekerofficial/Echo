# moreinfo_handler.py
from telegram import Update
from bot import creator_credits
from telegram.ext import CallbackContext
from modules.encrypted_data import encrypted_creator_info, decrypt

def more_info(update, context):
    user_id = update.message.from_user.id
    update.message.reply_text("""🤖 Bot Information;

🔰 Bot Name: Echo
🔰 Bot Description: A personal AI assistant on Telegram, designed to enhance your productivity with various range of features!

✍️ Language & Libraries Used:

🔰 Programming Language: Python
🔰 Version: 3.10.0
🔰 Libraries/Frameworks:
  1. python-telegram-bot (Telegram Bot API wrapper)
  2. pymongo (MongoDB driver for Python)
  3. Flask (Web framework for handling ping requests)
  4. threading 
  5. datetime (Python module for working with dates and times)
  6. pytz (Python timezone library)
  7. pycryptodome
  8. python-dateutil
  9. pyrogram
 10. TgCrypto
 11. telethon
 12. google-generativeai
 13. asteval
 14. gunicorn
 15. pillow
 16. IMDbPY
 17. psutil
 18. distro

🔗 Repo Link: https://github.com/theseekerofficial/Echo""")
    decrypted_creator_info = decrypt(encrypted_creator_info)

    if decrypted_creator_info is not None and creator_credits in decrypted_creator_info:
        update.message.reply_text(decrypted_creator_info)
    else:
        # Handle the case where decryption fails
        print("Respect to the Creator. Decryption verification failed.")
