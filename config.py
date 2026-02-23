import os

# Bot configuration - MUST be set in environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Download directory - use temp directory for cloud deployment
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', os.path.join(os.path.dirname(__file__), 'downloads'))

# Optional: Proxy configuration
PROXY = os.getenv('PROXY', None)

# Create download directory if it doesn't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)