import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(url, key)

# Test 1: Fetch the list of tables (public schema)
try:
    # Try to query a table that should exist (e.g., 'charts')
    # If the table doesn't exist yet, this will return an empty list, not an error.
    response = supabase.table("charts").select("*").limit(1).execute()
    print("✅ Successfully connected to Supabase.")
    print(f"   Query returned {len(response.data)} rows (expected if table is empty).")
except Exception as e:
    print("❌ Connection failed or query error:")
    print(e)

# Test 2: Try to insert a test record into a temporary table (optional)
# You can create a simple 'test' table in Supabase for this purpose.
# For example, if you have a 'test' table with an 'id' column, you could insert.
# But for now, we'll just check the connection.
