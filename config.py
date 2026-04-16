import os
from dotenv import load_dotenv

# Auto-load .env for local dev (silent fail if no .env)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', os.path.join(os.path.dirname(__file__), 'downloads'))
PROXY = os.getenv('PROXY', None)

if not BOT_TOKEN:
    print("⚠️  BOT_TOKEN missing. Create .env from .env.example and add your token.")
    print("For production (Render), set BOT_TOKEN env var.")
else:
    print(f"✅ BOT_TOKEN loaded ({len(BOT_TOKEN)} chars)")
    
# Create download directory
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
