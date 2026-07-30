import os
import logging
import threading
import re
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.error import Conflict, TimedOut, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN, DOWNLOAD_DIR
from database import (
    save_user,
    save_song,
    save_download,
    get_user_by_telegram_id,
    get_total_users,
    get_total_songs,
    get_total_downloads,
    get_trending_songs,
)

# Ensure logs directory exists
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "bot.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Regex patterns for YouTube and Instagram
YOUTUBE_URL_PATTERN = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+")
INSTAGRAM_URL_PATTERN = re.compile(r"(https?://)?(www\.)?(instagram\.com|instagr\.am)/.+")


class YouTubeDownloaderBot:
    """Main bot class encapsulating all handlers and application logic."""

    def __init__(self, token: str):
        self.token = token
        self.active_downloads = {}  # user_id -> threading.Event
        self.application = None

    def build_application(self) -> None:
        """Build the telegram application with extended timeouts."""
        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .build()
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        app = self.application
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("audio", self.audio_command))
        app.add_handler(CommandHandler("video", self.video_command))
        app.add_handler(CommandHandler("instagram", self.instagram_command))  # new
        app.add_handler(CommandHandler("stop", self.stop))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_error_handler(self.error_handler)

    # --------------------- Handlers ---------------------

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyboard = [
            ["🎧 Audio", "🎥 Video"],
            ["📊 Stats", "📜 History"],
            ["🔥 Trending", "❓ Help"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        description_text = (
            "👋 Welcome to YouTube/Instagram Downloader Bot!\n\n"
            "🎧 Download Audio (YouTube)\n"
            "🎥 Download Video (YouTube)\n"
            "📸 Download Instagram Post (video/photo)\n\n"
            "Just send a YouTube or Instagram URL directly.\n"
            "Or use commands:\n"
            "/audio <youtube_url>\n"
            "/video <youtube_url>\n"
            "/instagram <instagram_url>\n\n"
            "Example:\n"
            "https://youtube.com/watch?v=abcd1234\n"
            "https://instagram.com/p/xyz\n\n"
            "📬 Developer:@Thewarrior2003"
        )
        await update.message.reply_text(description_text, reply_markup=reply_markup)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        text = update.message.text.strip()

        if text == "❓ Help":
            await self.help_command(update, context)
        elif text == "📊 Stats":
            await self.stats_command(update, context)
        elif text == "📜 History":
            await self.history_command(update, context)
        elif text == "🔥 Trending":
            await self.trending_command(update, context)
        elif text == "🎧 Audio":
            await self._safe_send_message(update, "Send a YouTube URL and I will download the audio.")
        elif text == "🎥 Video":
            await self._safe_send_message(update, "Send a YouTube URL and I will download the video.")
        elif text.lower() in ["hi", "hello"]:
            await self._safe_send_message(update, "👋 Hi! Send a YouTube or Instagram link to get started.")
        elif YOUTUBE_URL_PATTERN.search(text):
            if "video" in text.lower():
                await self._process_video(update, context, text, user_id)
            else:
                await self._process_audio(update, context, text, user_id)
        elif INSTAGRAM_URL_PATTERN.search(text):
            await self._process_instagram(update, context, text, user_id)
        else:
            await self._safe_send_message(update, "Please send a valid YouTube or Instagram link.")

    async def audio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await self._safe_send_message(update, "Usage: /audio <YouTube URL>")
            return
        await self._process_audio(update, context, context.args[0], update.effective_user.id)

    async def video_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await self._safe_send_message(update, "Usage: /video <YouTube URL>")
            return
        await self._process_video(update, context, context.args[0], update.effective_user.id)

    async def instagram_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await self._safe_send_message(update, "Usage: /instagram <Instagram URL>")
            return
        await self._process_instagram(update, context, context.args[0], update.effective_user.id)

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        cancel_flag = self.active_downloads.get(user_id)
        if cancel_flag:
            cancel_flag.set()
            await self._safe_send_message(update, "⏹️ Stopped your download.")
        else:
            await self._safe_send_message(update, "No active download to stop.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = (
            "Commands:\n"
            "/start - Show welcome message\n"
            "/audio <link> - Download audio (YouTube)\n"
            "/video <link> - Download video (YouTube)\n"
            "/instagram <link> - Download Instagram post\n"
            "/stop - Cancel current download\n\n"
            "You can also just send a YouTube or Instagram link directly!"
        )
        await self._safe_send_message(update, help_text)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        total_users = get_total_users()
        total_songs = get_total_songs()
        total_downloads = get_total_downloads()
        stats_text = (
            f"📊 Bot Statistics\n\n"
            f"👤 Total Users: {total_users}\n"
            f"🎵 Total Songs: {total_songs}\n"
            f"⬇️ Total Downloads: {total_downloads}"
        )
        await self._safe_send_message(update, stats_text)

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._safe_send_message(update, "📜 History feature coming soon.")

    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        songs = get_trending_songs()
        if not songs:
            await self._safe_send_message(update, "No songs downloaded yet.")
            return
        message = "🔥 Top Downloaded Songs\n\n"
        for i, song in enumerate(songs, start=1):
            message += f"{i}. {song['title']}\n⬇️ {song['download_count']} downloads\n\n"
        await self._safe_send_message(update, message)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors and log them."""
        error = context.error
        logger.error(f"Exception while handling an update: {error}", exc_info=error)
        if isinstance(error, (TimedOut, NetworkError)):
            logger.warning("Network error occurred, skipping user notification.")
            return
        try:
            await self._safe_send_message(update, "❌ An error occurred. Please try again later.")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    # --------------------- Internal helpers ---------------------

    async def _safe_send_message(self, update: Update, text: str, max_retries: int = 3) -> bool:
        """Send a message with retry logic."""
        for attempt in range(max_retries):
            try:
                await update.message.reply_text(text)
                return True
            except (TimedOut, NetworkError) as e:
                logger.warning(f"Send message attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to send message after {max_retries} attempts.")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}")
                return False
        return False

    async def _safe_send_audio(self, update: Update, audio_file: str, caption: str, max_retries: int = 3) -> bool:
        """Send audio with retry and fallback to document."""
        for attempt in range(max_retries):
            try:
                with open(audio_file, "rb") as f:
                    await update.message.reply_audio(
                        audio=f,
                        caption=caption,
                        title=os.path.basename(audio_file)[:30],
                    )
                return True
            except Exception as e:
                logger.warning(f"Send audio attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to send audio after {max_retries} attempts. Falling back to document.")
                    try:
                        with open(audio_file, "rb") as f:
                            await update.message.reply_document(
                                document=f,
                                caption=caption + "\n( sent as file due to network issue )",
                            )
                        logger.info("Fallback document sent successfully.")
                        return True
                    except Exception as doc_err:
                        logger.error(f"Fallback document send also failed: {doc_err}")
                        return False
        return False

    async def _safe_send_video(self, update: Update, video_file: str, caption: str, max_retries: int = 3) -> bool:
        """Send video with retry logic."""
        for attempt in range(max_retries):
            try:
                with open(video_file, "rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=caption,
                        supports_streaming=True,
                    )
                return True
            except Exception as e:
                logger.warning(f"Send video attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to send video after {max_retries} attempts.")
                    return False
        return False

    async def _process_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int) -> None:
        await self._safe_send_message(update, "⏳ Downloading audio...")
        cancel_flag = threading.Event()
        self.active_downloads[user_id] = cancel_flag

        audio_file = None
        try:
            url = YOUTUBE_URL_PATTERN.search(text).group(0)
            from downloader import download_audio

            audio_file, title, elapsed_time = download_audio(url, cancel_flag)

            # Save Data To Supabase (with error handling)
            try:
                telegram_user = update.effective_user
                save_user(telegram_user)
                db_user = get_user_by_telegram_id(telegram_user.id)
                song = save_song(title, url)
                save_download(user_id=db_user["id"], song_id=song["id"])
                logger.info("✅ Database saved successfully")
            except Exception as db_error:
                logger.error(f"⚠️ Database error (continuing anyway): {db_error}")

            if not os.path.exists(audio_file):
                await self._safe_send_message(update, f"Audio file not found: {audio_file}")
                return

            file_size = os.path.getsize(audio_file) / (1024 * 1024)
            if file_size > 50:
                await self._safe_send_message(update, f"File too large ({file_size:.1f}MB). Limit is 50MB.")
                os.remove(audio_file)
                return

            caption = f"🎧 {title}\n⏱️ Downloaded in {elapsed_time:.1f}s"
            success = await self._safe_send_audio(update, audio_file, caption)

            if success:
                await self._safe_send_message(update, f"✅ Audio sent successfully! ({elapsed_time:.1f}s)")
            else:
                await self._safe_send_message(update, "❌ Failed to send audio due to network issues. Please try again.")

        except Exception as e:
            logger.error(f"Audio download error: {e}")
            error_msg = str(e)
            if "cancelled" in error_msg.lower():
                await self._safe_send_message(update, "⏹️ Download cancelled.")
            else:
                await self._safe_send_message(update, "❌ Failed to download audio. Please try again later.")

        finally:
            if audio_file and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    logger.info(f"Cleaned up audio file: {audio_file}")
                except Exception as e:
                    logger.error(f"Error cleaning up audio file: {e}")
            self.active_downloads.pop(user_id, None)

    async def _process_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int) -> None:
        await self._safe_send_message(update, "⏳ Downloading video...")
        cancel_flag = threading.Event()
        self.active_downloads[user_id] = cancel_flag

        video_file = None
        try:
            url = YOUTUBE_URL_PATTERN.search(text).group(0)
            from downloader import download_video

            video_file, title, elapsed_time = download_video(url, cancel_flag)

            # Save Data To Supabase (with error handling)
            try:
                telegram_user = update.effective_user
                save_user(telegram_user)
                db_user = get_user_by_telegram_id(telegram_user.id)
                song = save_song(title, url)
                save_download(user_id=db_user["id"], song_id=song["id"])
                logger.info("✅ Database saved successfully")
            except Exception as db_error:
                logger.error(f"⚠️ Database error (continuing anyway): {db_error}")

            if not os.path.exists(video_file):
                await self._safe_send_message(update, f"Video file not found: {video_file}")
                return

            file_size = os.path.getsize(video_file) / (1024 * 1024)
            if file_size > 50:
                await self._safe_send_message(update, f"File too large ({file_size:.1f}MB). Limit is 50MB.")
                os.remove(video_file)
                return

            caption = f"🎥 {title}\n⏱️ Downloaded in {elapsed_time:.1f}s"
            success = await self._safe_send_video(update, video_file, caption)

            if success:
                await self._safe_send_message(update, f"✅ Video sent successfully! ({elapsed_time:.1f}s)")
            else:
                await self._safe_send_message(update, "❌ Failed to send video due to network issues. Please try again.")

        except Exception as e:
            logger.error(f"Video download error: {e}")
            error_msg = str(e)
            if "cancelled" in error_msg.lower():
                await self._safe_send_message(update, "⏹️ Download cancelled.")
            else:
                await self._safe_send_message(update, "❌ Failed to download video. Please try again later.")

        finally:
            if video_file and os.path.exists(video_file):
                try:
                    os.remove(video_file)
                    logger.info(f"Cleaned up video file: {video_file}")
                except Exception as e:
                    logger.error(f"Error cleaning up video file: {e}")
            self.active_downloads.pop(user_id, None)

    # --- NEW: Instagram processor ---
    async def _process_instagram(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int) -> None:
        await self._safe_send_message(update, "⏳ Downloading Instagram post...")
        cancel_flag = threading.Event()
        self.active_downloads[user_id] = cancel_flag

        file_path = None
        try:
            url = INSTAGRAM_URL_PATTERN.search(text).group(0)
            from downloader import download_instagram

            file_path, title, elapsed_time, ext = download_instagram(url, cancel_flag)

            if not os.path.exists(file_path):
                await self._safe_send_message(update, f"File not found: {file_path}")
                return

            file_size = os.path.getsize(file_path) / (1024 * 1024)
            if file_size > 50:
                await self._safe_send_message(update, f"File too large ({file_size:.1f}MB). Limit is 50MB.")
                os.remove(file_path)
                return

            caption = f"📸 {title}\n⏱️ Downloaded in {elapsed_time:.1f}s"

            # Decide how to send based on extension
            if ext.lower() in ['.mp4', '.mov', '.avi', '.webm']:
                success = await self._safe_send_video(update, file_path, caption)
            elif ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # Try photo if size <= 10MB, else document
                if file_size < 10:
                    try:
                        with open(file_path, 'rb') as f:
                            await update.message.reply_photo(
                                photo=f,
                                caption=caption
                            )
                        success = True
                    except Exception as e:
                        logger.warning(f"Send photo failed: {e}, falling back to document")
                        success = False
                else:
                    success = False

                if not success:
                    # fallback to document
                    with open(file_path, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            caption=caption
                        )
                    success = True
            else:
                # Unknown extension → send as document
                with open(file_path, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        caption=caption
                    )
                success = True

            if success:
                await self._safe_send_message(update, f"✅ Instagram post sent! ({elapsed_time:.1f}s)")
            else:
                await self._safe_send_message(update, "❌ Failed to send file. Please try again.")

        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            if "cancelled" in str(e).lower():
                await self._safe_send_message(update, "⏹️ Download cancelled.")
            else:
                await self._safe_send_message(update, "❌ Failed to download Instagram post. Please try again later.")

        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file: {e}")
            self.active_downloads.pop(user_id, None)

    # --------------------- Run ---------------------

    def run(self) -> None:
        """Start the bot (polling or webhook based on environment)."""
        if not self.application:
            self.build_application()

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        print("✅ Bot is starting...")
        logger.info("Bot is starting...")

        if os.getenv("RENDER"):
            port = int(os.environ.get("PORT", 10000))
            webhook_url = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com")
            logger.info(f"Starting in PRODUCTION mode on port {port}")
            print(f"🚀 Production mode - Webhook: {webhook_url}")
            self.application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=BOT_TOKEN,
                webhook_url=f"{webhook_url}/{BOT_TOKEN}",
                drop_pending_updates=True,
            )
        else:
            logger.info("Starting in DEVELOPMENT mode (polling)")
            print("🔧 Development mode - Using polling")
            try:
                self.application.run_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES,
                    poll_interval=1,
                    timeout=30,
                )
            except Conflict as e:
                print(f"❌ Conflict error: {e}")
                print("Please make sure only one bot instance is running.")
                logger.error(f"Conflict error: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                logger.exception(f"Unexpected error: {e}")


# ==================== ENTRY POINT ====================

def main():
    bot = YouTubeDownloaderBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()