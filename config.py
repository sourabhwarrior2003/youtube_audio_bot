import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if BOT_TOKEN:
    BOT_TOKEN = BOT_TOKEN.strip()  # Remove extra spaces
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not configured. Please set it in environment variable")
# Directory to store downloaded files
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
# Download directory - use temp directory for cloud deployment
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', os.path.join(os.path.dirname(__file__), 'downloads'))

# Optional: Proxy configuration
PROXY = os.getenv('PROXY', None)

# Create download directory if it doesn't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)