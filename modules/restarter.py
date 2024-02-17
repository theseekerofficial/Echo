import os
import sys
import logging
import subprocess
from pymongo import MongoClient

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mongo_client():
    return MongoClient(os.getenv("MONGODB_URI"))

def check_for_updates(repo_url):
    try:
        # Check the current state
        current_state = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()

        # Try to pull the latest changes from the repository
        pull_result = subprocess.run(['git', 'pull', repo_url], capture_output=True, text=True, timeout=10)

        # If pull command failed (e.g., private repo, wrong URL), handle it
        if pull_result.returncode != 0:
            logging.info("🔒 Repository inaccessible or private. Preparing for restart.")
            raise Exception("Repository inaccessible or private")

        # Check the state after pulling
        new_state = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()

        # Return True if new updates were applied, False otherwise
        is_updated = current_state != new_state
        if is_updated:
            logging.info("✅ Successfully pulled new updates.")
        else:
            logging.info("🔄 No new updates available. Preparing for restart.")

        return is_updated

    except Exception as e:
        logging.info("🔒 Repo is private or inaccessible. Preparing for restart.")
        return "private_repo"
        
def write_update_status_to_mongo(status):
    client = get_mongo_client()
    db = client.get_database("Echo")
    db.update_status.replace_one({'_id': 'restart_status'}, {'_id': 'restart_status', 'status': status}, upsert=True)

def restart_bot():
    from bot import stop_http_server
    # Stop the HTTP server
    stop_http_server()

    # Restart the bot
    current_script = os.path.abspath(sys.argv[0])
    os.execv(sys.executable, [sys.executable, current_script] + sys.argv[1:])
