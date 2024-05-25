import os
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGODB_URI"))
db = client['Echo_Guardian']
