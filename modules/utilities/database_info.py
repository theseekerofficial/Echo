# modules/utilities/database_info.py
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), 'config.env')
load_dotenv(dotenv_path)

# Assuming you have already loaded environment variables
def fetch_db_stats():
    client = MongoClient(os.getenv("MONGODB_URI"))
    
    # Starting the message with bold style
    message = "*🗄 Database Information:*\n"
    
    for db_name in ["Echo", "Echo_Doc_Spotter"]:
        db = client[db_name]
        db_stats = db.command("dbstats")
        document_counts = sum(db[col].count_documents({}) for col in db.list_collection_names())
        index_count = sum(len(db[col].index_information()) for col in db.list_collection_names())
        
        # Adding database names in bold and other stats with emojis for clarity
        message += (
            f"\n*📂 {db_name} Stats:*\n"
            f"    💾 *Storage Usage:* `{db_stats['dataSize'] / (1024 * 1024):.2f}MB`\n"
            f"    📄 *Document Counts:* `{document_counts}`\n"
            f"    📊 *Index Usage:* `{index_count}`\n"
        )

    # Ensure the entire message uses Markdown formatting
    return message

def database_command(update, context):
    try:
        stats_message = fetch_db_stats()
        update.message.reply_text(stats_message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Failed to fetch database stats: {e}")
        update.message.reply_text("Failed to fetch database stats. Please try again later.")

