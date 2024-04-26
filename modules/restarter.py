import os
import sys
import shutil
import logging
import subprocess
from datetime import datetime
from pymongo import MongoClient
from modules.configurator import get_env_var_from_db

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mongo_client():
    return MongoClient(os.getenv("MONGODB_URI"))

def get_repo_root_path(start_path):
    if os.path.isdir(os.path.join(start_path, '.git')):
        return start_path
    parent_dir = os.path.dirname(start_path)
    if parent_dir == start_path:  # Reached the filesystem root
        raise Exception("Failed to find .git directory. Are you sure this script is inside a git repository?")
    return get_repo_root_path(parent_dir)

def fetch_latest_commit(repo_url):
    try:
        latest_remote_commit = subprocess.check_output(["git", "ls-remote", repo_url, "HEAD"], text=True).split()[0]
        return latest_remote_commit
    except Exception as e:
        logger.error(f"Error fetching latest commit: {str(e)}")
        return None

def get_current_commit():
    try:
        current_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        return current_commit
    except Exception as e:
        logger.error(f"Error getting current commit: {str(e)}")
        return None
def check_for_updates(repo_url):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        repo_root_dir = get_repo_root_path(script_dir)
        os.chdir(repo_root_dir)
        logger.info(f"Changed working directory to repository root: {repo_root_dir}")

        config_env_path = os.path.join(repo_root_dir, 'config.env')
        config_env_backup_path = os.path.join(repo_root_dir, 'config.env.backup')

        latest_remote_commit = fetch_latest_commit(repo_url)
        current_commit = get_current_commit()

        if latest_remote_commit and current_commit and latest_remote_commit != current_commit:
            # Backup config.env if it exists
            if os.path.exists(config_env_path):
                try:
                    shutil.copy(config_env_path, config_env_backup_path)
                    logger.info("config.env backed up successfully.")
                except Exception as e:
                    logger.error(f"Failed to backup config.env: {e}")

            subprocess.run(["git", "fetch", repo_url])
            subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"])

            # Restore config.env from backup if it was backed up
            if os.path.exists(config_env_backup_path):
                try:
                    shutil.move(config_env_backup_path, config_env_path)
                    logger.info("config.env restored from backup successfully.")
                except Exception as e:
                    logger.error(f"Failed to restore config.env from backup: {e}")

            commit_message = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
            commit_author = subprocess.check_output(["git", "log", "-1", "--pretty=%an"], text=True).strip()

            status_message = f"Successfully Updated and Restarted!\n\nLatest Commit: {commit_message}\nAuthor: {commit_author}"
            write_update_status_to_mongo(status_message)

            logger.info(status_message)
            return True, commit_message, commit_author
        else:
            status_message = "🔁No New Updates, Just Restarted!"
            write_update_status_to_mongo(status_message)
            logger.info(status_message)
            return False, None, None
    except Exception as e:
        logger.error(f"Error during update check: {str(e)}")
        status_message = "Error occurred during update check."
        write_update_status_to_mongo(status_message)
        return False, None, None
        
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

def check_and_restart_auto(context):
    try:
        restart_at_every = int(get_env_var_from_db("RESTART_AT_EVERY"))
    except (TypeError, ValueError):
        restart_at_every = 86400  
    
    if restart_at_every == 0:
        logger.info("Auto-restart is disabled. 🛡️")
        return

    try:
        client = get_mongo_client()
        db = client.get_database("Echo")
        bot_info_collection = db['bot_info']
        bot_start_time_doc = bot_info_collection.find_one({'_id': 'bot_start_time'})

        if not bot_start_time_doc:
            logger.info("Bot start time is not set in MongoDB. Skipping auto restart check.")
            return

        start_time = bot_start_time_doc['start_time']
        uptime_seconds = (datetime.utcnow() - start_time).total_seconds()

        if uptime_seconds >= restart_at_every:
            logger.info("Uptime threshold reached. Initiating automatic restart. 🚀")
            write_update_status_to_mongo("Auto-Restart Triggered based on Uptime. ♾️")
            restart_bot()
        else:
            logger.info(f"Auto-restart check passed. Uptime: {uptime_seconds} seconds. Threshold: {restart_at_every} seconds.")
    except Exception as e:
        logger.error(f"Error during auto-restart check: {str(e)}")


