from database import supabase

response = (
    supabase
    .table("users")
    .insert({
        "telegram_id": 123456789,
        "username": "test_user"
    })
    .execute()
)

print(response.data)