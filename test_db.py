from database import supabase

response = (
    supabase
    .table("users")
    .select("*")
    .execute()
)

print(response.data)