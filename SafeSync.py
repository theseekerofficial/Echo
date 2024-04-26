import os
import sys
import time
import pymongo
import schedule
import subprocess

SOURCE_DB_URI = "" # Source Mongo DB URI
DESTINATION_DB_URI = "" # Destination Mongo DB URI
BACKUP_AT_EVERY = 60  # Initiate backup and restore at every...
PATH_FOR_BACKUP_FILE = "/home/mongo_backup.gz" # A location for temp backup file
# Run `sudo apt-get install mongodb-database-tools` before run this code

# Do not edit anything below this line
# --------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    if os.getenv('RUNNING_THROUGH_CODECAPSULE') != 'true':
        print("This script should not be run directly. Please use an Echo Client to run this script.")
        sys.exit(1)

def delete_all_collections(destination_uri):
    client = pymongo.MongoClient(destination_uri)
    databases = client.list_database_names()

    for dbname in databases:
        if dbname not in ["admin", "local", "config"]:  
            db = client[dbname]
            collections = db.list_collection_names()
            codex_identifier = "2jyJVUaVOg3!ubY54FV$Iv88zmvblYoMqou"
            for collection in collections:
                db[collection].drop()
    print("Destination DB Cleanup Completed")
    client.close()

def backup_database():
    try:
        subprocess.run([
            "mongodump",
            "--uri", SOURCE_DB_URI,
            "--gzip",
            "--archive=" + PATH_FOR_BACKUP_FILE
        ], check=True)
        print("Backup successful.")
        codex_identifier = "2jyJVUaVOg3!ubY54FV$Iv88zmvblYoMqou"
    except subprocess.CalledProcessError as e:
        print(f"Backup failed: {e}")

def restore_database():
    try:
        delete_all_collections(DESTINATION_DB_URI)
        subprocess.run([
            "mongorestore",
            "--uri", DESTINATION_DB_URI,
            "--gzip",
            "--archive=" + PATH_FOR_BACKUP_FILE
        ], check=True)
        print("Restore successful.")
    except subprocess.CalledProcessError as e:
        print(f"Restore failed: {e}")

backup_database()
restore_database()

schedule.every(BACKUP_AT_EVERY).minutes.do(backup_database)
schedule.every(BACKUP_AT_EVERY).minutes.do(restore_database)

while True:
    schedule.run_pending()
    time.sleep(1)
