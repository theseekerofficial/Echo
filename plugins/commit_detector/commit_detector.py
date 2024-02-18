# commit_detector.py
import os
import logging
import requests
from pytz import utc
from dotenv import load_dotenv
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
GH_CD_PAT = os.getenv("GH_CD_PAT")

# New validation for GH_CD_URLS and GH_CD_CHANNEL_IDS
GH_CD_URLS = os.getenv("GH_CD_URLS", "").split(',') if os.getenv("GH_CD_URLS") else []
GH_CD_CHANNEL_IDS = [int(cid) for cid in os.getenv("GH_CD_CHANNEL_IDS").split(',')] if os.getenv("GH_CD_CHANNEL_IDS") else []

# Validate that both or neither GH_CD_URLS and GH_CD_CHANNEL_IDS are provided
if bool(GH_CD_URLS) != bool(GH_CD_CHANNEL_IDS):
    logger.error("❌ Both GH_CD_URLS and GH_CD_CHANNEL_IDS must be provided if one is provided. Exiting.")
    exit(1)

# Proceed if both are provided or both are empty
if not GH_CD_URLS:
    logger.info("ℹ️ No GitHub repositories and Telegram channels configured for commit detection. Feature disabled.")
else:
    client = MongoClient(MONGODB_URI)
    db = client.get_database("Echo")
    commit_collection = db["GH_Commit_Detector"]

def fetch_latest_commit(repo_url):
    api_url = f"https://api.github.com/repos/{repo_url}/commits?per_page=1"
    headers = {"Accept": "application/vnd.github.v3+json"}
    # Use PAT for authenticated requests if available
    if GH_CD_PAT:
        headers["Authorization"] = f"token {GH_CD_PAT}"
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        latest_commit = response.json()[0]
        return latest_commit
    else:
        logger.error(f"❌ Failed to fetch latest commit for {repo_url}. Status code: {response.status_code}")
        return None

def check_and_update_commits(bot):
    for repo_url in GH_CD_URLS:
        latest_commit = fetch_latest_commit(repo_url)
        if latest_commit:
            stored_commit = commit_collection.find_one({"repo_url": repo_url})
            if not stored_commit or stored_commit['commit_sha'] != latest_commit['sha']:
                commit_collection.update_one({"repo_url": repo_url},
                                             {"$set": {"repo_url": repo_url, "commit_sha": latest_commit['sha']}},
                                             upsert=True)
                send_commit_update(bot, repo_url, latest_commit)

def escape_markdown_v2(text):
    """Escape MarkdownV2 special characters in the given text."""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def send_commit_update(bot, repo_url, commit):
    repo_url_escaped = escape_markdown_v2(repo_url)
    commit_message_escaped = escape_markdown_v2(commit['commit']['message'])
    author_name_escaped = escape_markdown_v2(commit['commit']['author']['name'])
    
    message = (
        f"\\#Repo\\_Update\n🔔 *New Commit* 🔔\n\n"
        f"🪃 *Repository*: *{repo_url_escaped}*\n\n"
        f"📌 *Commit*: [{commit['sha'][:7]}]({commit['html_url']})\n"
        f"✍️ *Message*: _{commit_message_escaped}_\n"
        f"👤 *Author*: `{author_name_escaped}`\n"
        f"🕒 *Date*: `{commit['commit']['author']['date']}`\n\n"
        f"[🔍 View Commit]({commit['html_url']})"
    )
    for channel_id in GH_CD_CHANNEL_IDS:
        try:
            bot.send_message(chat_id=channel_id, text=message, parse_mode='MarkdownV2', disable_web_page_preview=True)
            logger.info(f"✅ Successfully sent commit update for {repo_url} to channel {channel_id}.")
        except Exception as e:
            logger.error(f"❌ Error sending to channel {channel_id}: {e}")

def setup_commit_detector(updater, interval_minutes=None):
    from apscheduler.schedulers.background import BackgroundScheduler
    # Ensure the scheduler only starts if there are URLs to monitor
    if GH_CD_URLS:
        scheduler = BackgroundScheduler(timezone=utc)
        if interval_minutes is None:
            # Calculate interval based on the number of URLs
            interval_minutes = max(10, len(GH_CD_URLS))
        scheduler.add_job(check_and_update_commits, 'interval', minutes=interval_minutes, args=[updater.bot])
        scheduler.start()
    else:
        logger.info("ℹ️ Commit Detector scheduler not started due to no URLs configured.")
