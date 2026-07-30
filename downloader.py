import os
import time
import random
import re
import tempfile
import shutil

# Node.js detection (ensures yt-dlp can use it if needed)
print("Node.js found:", shutil.which("node"))
if not shutil.which("node"):
    # Fallback for local Windows (adjust path if necessary)
    os.environ['YT_DLP_EXE_NODE'] = r'C:\Program Files\nodejs\node.exe'

from yt_dlp import YoutubeDL
from config import DOWNLOAD_DIR

COOKIES_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

def sanitize_filename(filename):
    if not filename:
        return "audio_download"
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().strip('.')
    return cleaned[:100] if cleaned else "audio_download"

def download_audio(url: str, cancel_flag=None, proxy: str = None):
    def progress_hook(d):
        if cancel_flag and cancel_flag.is_set():
            raise Exception("Download cancelled by user.")

    temp_download_dir = tempfile.mkdtemp()

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_download_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'extractor_args': {'youtube': 'player_client=android'},
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
        },
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'progress_hooks': [progress_hook],
        'cookiefile': COOKIES_FILE_PATH if os.path.exists(COOKIES_FILE_PATH) else None,
        'quiet': False,
        'no_warnings': False,
        'sleep_interval': 10,
        'max_sleep_interval': 20,
        'sleep_interval_requests': 2,
    }

    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            start_time = time.time()
            info = ydl.extract_info(url, download=True)
            elapsed_time = time.time() - start_time

            original_title = info.get('title', 'audio')
            sanitized_title = sanitize_filename(original_title)

            downloaded_files = [f for f in os.listdir(temp_download_dir) if f.endswith('.mp3')]
            if not downloaded_files:
                downloaded_files = os.listdir(temp_download_dir)

            if not downloaded_files:
                raise FileNotFoundError("No files found in temp directory")

            temp_file_path = os.path.join(temp_download_dir, downloaded_files[0])
            final_filename = os.path.join(DOWNLOAD_DIR, f"{sanitized_title}.mp3")

            shutil.move(temp_file_path, final_filename)
            shutil.rmtree(temp_download_dir, ignore_errors=True)

            return final_filename, original_title, elapsed_time

    except Exception as e:
        shutil.rmtree(temp_download_dir, ignore_errors=True)
        raise e

def download_video(url: str, cancel_flag=None, proxy: str = None):
    def progress_hook(d):
        if cancel_flag and cancel_flag.is_set():
            raise Exception("Download cancelled by user.")

    temp_download_dir = tempfile.mkdtemp()

    ydl_opts = {
        'format': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'outtmpl': os.path.join(temp_download_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'extractor_args': {'youtube': 'player_client=android'},
        'http_headers': {'User-Agent': random.choice(USER_AGENTS)},
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook],
        'cookiefile': COOKIES_FILE_PATH if os.path.exists(COOKIES_FILE_PATH) else None,
        'sleep_interval': 10,
        'max_sleep_interval': 20,
        'sleep_interval_requests': 2,
    }

    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            start_time = time.time()
            info = ydl.extract_info(url, download=True)
            elapsed_time = time.time() - start_time

            original_title = info.get('title', 'video')
            sanitized_title = sanitize_filename(original_title)

            downloaded_files = [f for f in os.listdir(temp_download_dir) if f.endswith(('.mp4', '.webm', '.mkv'))]
            if not downloaded_files:
                raise FileNotFoundError("No video files found")

            temp_file_path = os.path.join(temp_download_dir, downloaded_files[0])
            final_filename = os.path.join(DOWNLOAD_DIR, f"{sanitized_title}.mp4")

            shutil.move(temp_file_path, final_filename)
            shutil.rmtree(temp_download_dir, ignore_errors=True)

            return final_filename, original_title, elapsed_time

    except Exception as e:
        shutil.rmtree(temp_download_dir, ignore_errors=True)
        raise e


# ===== NEW: Instagram downloader =====
def download_instagram(url: str, cancel_flag=None, proxy: str = None):
    """Download Instagram post (video or image) using yt-dlp."""
    def progress_hook(d):
        if cancel_flag and cancel_flag.is_set():
            raise Exception("Download cancelled by user.")

    temp_download_dir = tempfile.mkdtemp()
    ydl_opts = {
        'outtmpl': os.path.join(temp_download_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'http_headers': {'User-Agent': random.choice(USER_AGENTS)},
        'nocheckcertificate': True,
        'progress_hooks': [progress_hook],
        'cookiefile': COOKIES_FILE_PATH if os.path.exists(COOKIES_FILE_PATH) else None,
        'quiet': False,
        'no_warnings': False,
        # Instagram may need more specific extractor args; yt-dlp handles it by default
    }
    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            start_time = time.time()
            info = ydl.extract_info(url, download=True)
            elapsed_time = time.time() - start_time

            original_title = info.get('title', 'instagram_post')
            sanitized_title = sanitize_filename(original_title)

            files = os.listdir(temp_download_dir)
            if not files:
                raise FileNotFoundError("No files downloaded")

            # Use the first file (yt-dlp usually downloads a single media)
            temp_file_path = os.path.join(temp_download_dir, files[0])
            ext = os.path.splitext(files[0])[1]  # .mp4, .jpg, etc.
            final_filename = os.path.join(DOWNLOAD_DIR, f"{sanitized_title}{ext}")

            shutil.move(temp_file_path, final_filename)
            shutil.rmtree(temp_download_dir, ignore_errors=True)

            return final_filename, original_title, elapsed_time, ext

    except Exception as e:
        shutil.rmtree(temp_download_dir, ignore_errors=True)
        raise e