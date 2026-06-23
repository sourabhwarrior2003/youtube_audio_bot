import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

def save_user(user):

    existing = (
        supabase
        .table("users")
        .select("*")
        .eq("telegram_id", user.id)
        .execute()
    )

    if existing.data:

        return existing.data[0]

    result = (
        supabase
        .table("users")
        .insert({
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name
        })
        .execute()
    )

    return result.data[0]

def save_song(title, youtube_url):

    existing = (
        supabase
        .table("songs")
        .select("*")
        .eq("youtube_url", youtube_url)
        .execute()
    )

    if existing.data:

        song = existing.data[0]

        (
            supabase
            .table("songs")
            .update({
                "download_count":
                song["download_count"] + 1
            })
            .eq("id", song["id"])
            .execute()
        )

        return song

    result = (
        supabase
        .table("songs")
        .insert({
            "title": title,
            "youtube_url": youtube_url,
            "download_count": 1
        })
        .execute()
    )

    return result.data[0]

def save_download(
    user_id,
    song_id
):

    result = (
        supabase
        .table("downloads")
        .insert({
            "user_id": user_id,
            "song_id": song_id
        })
        .execute()
    )

    return result.data[0]

def get_user_by_telegram_id(
    telegram_id
):

    result = (
        supabase
        .table("users")
        .select("*")
        .eq(
            "telegram_id",
            telegram_id
        )
        .execute()
    )

    if result.data:
        return result.data[0]

    return None

def get_song_by_url(
    youtube_url
):

    result = (
        supabase
        .table("songs")
        .select("*")
        .eq(
            "youtube_url",
            youtube_url
        )
        .execute()
    )

    if result.data:
        return result.data[0]

    return None

def get_total_users():

    result = (
        supabase
        .table("users")
        .select(
            "*",
            count="exact"
        )
        .execute()
    )

    return result.count


def get_total_songs():

    result = (
        supabase
        .table("songs")
        .select(
            "*",
            count="exact"
        )
        .execute()
    )

    return result.count


def get_total_downloads():

    result = (
        supabase
        .table("downloads")
        .select(
            "*",
            count="exact"
        )
        .execute()
    )

    return result.count
def get_trending_songs():

    result = (
        supabase
        .table("songs")
        .select("*")
        .order(
            "download_count",
            desc=True
        )
        .limit(10)
        .execute()
    )

    return result.data