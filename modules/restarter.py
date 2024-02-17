import os
import sys
import shutil
import logging
import subprocess
from pymongo import MongoClient

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

def check_for_updates(repo_url):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        repo_root_dir = get_repo_root_path(script_dir)
        os.chdir(repo_root_dir)
        logger.info(f"Changed working directory to repository root: {repo_root_dir}")

        config_env_path = os.path.join(repo_root_dir, 'config.env')
        config_env_backup_path = os.path.join(repo_root_dir, 'config.env.backup')

        # Backup config.env if it exists
        if os.path.exists(config_env_path):
            shutil.copy(config_env_path, config_env_backup_path)
            logger.info("config.env backed up.")

        # Fetch changes from the remote repository
        fetch_result = subprocess.run(['git', 'fetch', repo_url], capture_output=True, text=True, timeout=10)
        if fetch_result.returncode != 0:
            logger.info("Failed to fetch updates from remote. Preparing for restart.")
            logger.info(f"Fetch failed: {fetch_result.stderr}")
            return "fetch_failed"

        # Reset the local state to match that of the fetched remote branch
        reset_result = subprocess.run(['git', 'reset', '--hard', 'FETCH_HEAD'], capture_output=True, text=True, timeout=10)
        if reset_result.returncode != 0:
            logger.info("Failed to reset local changes. Preparing for restart.")
            logger.info(f"Reset failed: {reset_result.stderr}")
            return "reset_failed"

        # Restore config.env from backup if it was backed up
        if os.path.exists(config_env_backup_path):
            shutil.move(config_env_backup_path, config_env_path)
            logger.info("config.env restored from backup.")

        logger.info("✅ Successfully synchronized local repository with remote.")
        return True

    except Exception as e:
        logging.info(f"Error during update check: {str(e)}. Preparing for restart.")
        return "error"
        
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