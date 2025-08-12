# database.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import sys

# Apne config file se MongoDB variables import karein
from config import MONGO_URI, DATABASE_NAME

# --- Database Connection ---
try:
    # MongoDB se connection banayein
    client = MongoClient(MONGO_URI)
    # Ping karke connection check karein
    client.admin.command('ping')
    print("✅ MongoDB se connection safaltapurvak ho gaya!")
except ConnectionFailure as e:
    print(f"❌ MongoDB se connect nahi ho paya: {e}")
    # Connection fail hone par bot ko exit kar dein
    sys.exit("Database connection zaroori hai. Bot band ho raha hai.")
except Exception as e:
    print(f"Ek anjaan error aayi: {e}")
    sys.exit("Bot band ho raha hai.")


# Database aur collection ko select karein
db = client[DATABASE_NAME]
files_collection = db["files"]


# --- Database Functions ---

def add_file(link_id, user_id, file_name, permanent_file_id):
    """Ek nayi file ki metadata ko MongoDB mein add karta hai."""
    document = {
        "_id": link_id,  # link_id ko primary key banayein
        "user_id": user_id,
        "file_name": file_name,
        "permanent_file_id": permanent_file_id
    }
    files_collection.insert_one(document)

def get_file_data(link_id):
    """Link ID ka istemaal karke file ka data MongoDB se retrieve karta hai."""
    return files_collection.find_one({"_id": link_id})

def get_user_files(user_id):
    """Ek specific user dwara upload ki gayi sabhi files ko laata hai."""
    # Cursor ko list mein convert karke return karein
    return list(files_collection.find({"user_id": user_id}))

def get_all_files():
    """Admin ke liye sabhi users ki saari files laata hai."""
    return list(files_collection.find({}))

def delete_file(link_id):
    """Database se file ki metadata delete karta hai."""
    result = files_collection.delete_one({"_id": link_id})
    # Agar ek document delete hua to True return karein
    return result.deleted_count > 0

def clear_all_files():
    """Database se sabhi file data ko clear karta hai."""
    files_collection.delete_many({})
