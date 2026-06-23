from database import save_song

result = save_song(
    title="Kesariya",
    youtube_url="https://youtube.com/watch?v=test123"
)

print(result)