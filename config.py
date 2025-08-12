# config.py
import os
from dotenv import load_dotenv

# .env file se environment variables load karne ke liye
load_dotenv()

# --- Bot Secrets & IDs ---
# Apne BotFather se mila hua NAYA token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Apni Telegram User ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0)) # Default 0 to prevent crash

# Apne private storage channel ka ID
STORAGE_CHANNEL_ID = int(os.environ.get("STORAGE_CHANNEL_ID", 0)) # Default 0 to prevent crash


# --- MongoDB Settings ---
# Apne MongoDB database ka naam
DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_bot_db")
# Apne MongoDB database ka connection URI
MONGO_URI = os.environ.get("MONGO_URI")


# --- Webhook Settings (Render.com ke liye) ---
# Inhe Render.com apne aap set kar deta hai
WEBHOOK_PORT = int(os.environ.get('PORT', 8443))
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')
