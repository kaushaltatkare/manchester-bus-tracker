import os 
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("BODS_API_KEY")  # fetch the key by name; returns None if missing
if not key:
    print("ERROR: BODS_API_KEY not found. Check your .env file.")
else:
    print(f"Key loaded: {key[:4]}****")  # show only the first 4 characters