import os
import logging
import threading
import re
import asyncio
import base64
from telegram import Update
from telegram.error import Conflict, TimedOut, NetworkError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN, DOWNLOAD_DIR
from downloader import download_audio, download_video


# Ensure logs directory exists
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging with proper encoding for Windows
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dictionary to track active downloads cancellation flags per user id
active_downloads = {}

# Regex pattern to detect YouTube URLs
YOUTUBE_URL_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description_text = (
       "👋 *Welcome to YouTube Downloader Bot!*\n\n"
        "With this bot, you can download:\n"
        "🎧 *Audio* — /audio <YouTube URL>\n"
        "🎥 *Video* — /video <YouTube URL>\n\n"
        "Example:\n"
        "/audio https://youtube.com/watch?v=abcd1234\n"
        "/video https://youtube.com/watch?v=abcd1234\n\n"
        "ℹ️ *Supported formats:*\n"
        "- MP3 (audio)\n"
        "- MP4 (video)\n\n"
        "📬 [Contact Developer](https://t.me/Thewarrior2003)\n"
        "*your frind(sourabh)*"
    )
    await safe_send_message(update, description_text, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() in ["hi", "hello"]:
        await safe_send_message(update, "👋 Hi! Send a YouTube link to get started.")
        return

    if YOUTUBE_URL_PATTERN.search(text):
        if "video" in text.lower():
            await process_video(update, context, text, user_id)
        else:
            await process_audio(update, context, text, user_id)
    else:
        await safe_send_message(update, "Please send a valid YouTube link.")

async def safe_send_message(update: Update, text: str, max_retries=3, parse_mode=None):
    """Safely send message with retry logic and error handling"""
    for attempt in range(max_retries):
        try:
            await update.message.reply_text(text, parse_mode=parse_mode)
            return True
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Send message attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Wait before retry
            else:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    return False

async def safe_send_audio(update: Update, audio_file: str, caption: str, max_retries=3):
    """Safely send audio file with retry logic"""
    for attempt in range(max_retries):
        try:
            with open(audio_file, 'rb') as audio_f:
                await update.message.reply_audio(
                    audio=audio_f,
                    caption=caption,
                    title=os.path.basename(audio_file)[:30]
                )
            return True
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Send audio attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                logger.error(f"Failed to send audio after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending audio: {e}")
            return False
    return False

async def safe_send_video(update: Update, video_file: str, caption: str, max_retries=3):
    """Safely send video file with retry logic"""
    for attempt in range(max_retries):
        try:
            with open(video_file, 'rb') as video_f:
                await update.message.reply_video(
                    video=video_f,
                    caption=caption,
                    supports_streaming=True
                )
            return True
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Send video attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                logger.error(f"Failed to send video after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error sending video: {e}")
            return False
    return False

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int):
    await safe_send_message(update, "⏳ Downloading audio...")
    cancel_flag = threading.Event()
    active_downloads[user_id] = cancel_flag
    
    audio_file = None
    try:
        url = YOUTUBE_URL_PATTERN.search(text).group(0)
        
        audio_file, title, elapsed_time = download_audio(url, cancel_flag)

        if not os.path.exists(audio_file):
            await safe_send_message(update, f"Audio file not found: {audio_file}")
            return

        file_size = os.path.getsize(audio_file) / (1024 * 1024)  # Size in MB
        if file_size > 50:  # Telegram file size limit is 50MB
            await safe_send_message(update, f"File too large ({file_size:.1f}MB). Telegram limit is 50MB.")
            os.remove(audio_file)
            return

        # Send the audio file
        caption = f"🎧 {title}\n⏱️ Downloaded in {elapsed_time:.1f}s"
        success = await safe_send_audio(update, audio_file, caption)
        
        if success:
            await safe_send_message(update, f"✅ Audio sent successfully! ({elapsed_time:.1f}s)")
        else:
            await safe_send_message(update, "❌ Failed to send audio due to network issues. Please try again.")
                
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        error_msg = str(e)
        if "cancelled" in error_msg.lower():
            await safe_send_message(update, "⏹️ Download cancelled.")
        else:
            await safe_send_message(update, "❌ Failed to download audio. Please try again later.")
    finally:
        
        
        # Clean up downloaded file
        if audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                logger.info(f"Cleaned up audio file: {audio_file}")
            except Exception as e:
                logger.error(f"Error cleaning up audio file: {e}")
        
        active_downloads.pop(user_id, None)

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int):
    await safe_send_message(update, "⏳ Downloading video...")
    cancel_flag = threading.Event()
    active_downloads[user_id] = cancel_flag
    
    video_file = None
    try:
        url = YOUTUBE_URL_PATTERN.search(text).group(0)
        
        video_file, title, elapsed_time = download_video(url, cancel_flag)

        if not os.path.exists(video_file):
            await safe_send_message(update, f"Video file not found: {video_file}")
            return

        file_size = os.path.getsize(video_file) / (1024 * 1024)  # Size in MB
        if file_size > 50:  # Telegram file size limit is 50MB
            await safe_send_message(update, f"File too large ({file_size:.1f}MB). Telegram limit is 50MB.")
            os.remove(video_file)
            return

        # Send the video file
        caption = f"🎥 {title}\n⏱️ Downloaded in {elapsed_time:.1f}s"
        success = await safe_send_video(update, video_file, caption)
        
        if success:
            await safe_send_message(update, f"✅ Video sent successfully! ({elapsed_time:.1f}s)")
        else:
            await safe_send_message(update, "❌ Failed to send video due to network issues. Please try again.")
                
    except Exception as e:
        logger.error(f"Video download error: {e}")
        error_msg = str(e)
        if "cancelled" in error_msg.lower():
            await safe_send_message(update, "⏹️ Download cancelled.")
        else:
            await safe_send_message(update, "❌ Failed to download video. Please try again later.")
    finally:
        # Clean up downloaded file
        if video_file and os.path.exists(video_file):
            try:
                os.remove(video_file)
                logger.info(f"Cleaned up video file: {video_file}")
            except Exception as e:
                logger.error(f"Error cleaning up video file: {e}")
        
        active_downloads.pop(user_id, None)

async def audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_send_message(update, "Usage: /audio <YouTube URL>")
        return
    await process_audio(update, context, context.args[0], update.effective_user.id)

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_send_message(update, "Usage: /video <YouTube URL>")
        return
    await process_video(update, context, context.args[0], update.effective_user.id)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cancel_flag = active_downloads.get(user_id)
    if cancel_flag:
        cancel_flag.set()
        await safe_send_message(update, "⏹️ Stopped your download.")
    else:
        await safe_send_message(update, "No active download to stop.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Commands:\n"
        "/start - Show welcome message\n"
        "/audio <link> - Download audio\n"
        "/video <link> - Download video\n"
        "/stop - Cancel current download\n\n"
        "You can also just send a YouTube link directly!"
    )
    await safe_send_message(update, help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the telegram bot."""
    error = context.error
    logger.error(f"Exception while handling an update: {error}", exc_info=error)
    
    # Don't try to send error messages for network timeouts to avoid infinite loops
    if isinstance(error, (TimedOut, NetworkError)):
        logger.warning("Network error occurred, skipping user notification")
        return
    
    try:
        await safe_send_message(update, "❌ An error occurred. Please try again later.")
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

def main():
    """Start the bot."""
    # Decode cookies from environment variable if present (for Render deployment)
    cookies_base64 = os.getenv('COOKIES_BASE64')
    if cookies_base64:
        print("Decoding cookies.txt from environment...")
        try:
            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')
            with open(cookies_path, 'wb') as f:
                f.write(base64.b64decode(cookies_base64))
            print("✅ Cookies.txt created successfully!")
        except Exception as e:
            print(f"Error decoding cookies: {e}")
            logger.error(f"Error decoding cookies: {e}")
    
    # Validate environment
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not configured. Please set it in config.py")
    
    # Ensure download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Create application with better timeout settings
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("audio", audio_command))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start the Bot
    print("✅ Bot is starting...")
    logger.info("Bot is starting...")
    
    # Check if we're in production (Render) or development
    if os.getenv('RENDER'):
        # Production on Render - use webhook
        port = int(os.environ.get('PORT', 10000))
        webhook_url = os.getenv('WEBHOOK_URL', f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com")
        
        logger.info(f"Starting in PRODUCTION mode on port {port}")
        print(f"🚀 Production mode - Webhook: {webhook_url}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{webhook_url}/{BOT_TOKEN}",
            drop_pending_updates=True
        )
    else:
        # Development - use polling with better settings
        logger.info("Starting in DEVELOPMENT mode (polling)")
        print("🔧 Development mode - Using polling")
        
        try:
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                poll_interval=1,  # Reduce polling interval
                timeout=30  # Increase timeout
            )
        except Conflict as e:
            print(f"❌ Conflict error: {e}")
            print("Please make sure only one bot instance is running")
            logger.error(f"Conflict error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.exception(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()