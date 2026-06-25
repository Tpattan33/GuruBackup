import os
import requests
from dotenv import load_dotenv

load_dotenv()

GURU_API = "https://api.getguru.com/api/v1"

EMAIL = os.getenv("GURU_EMAIL")
TOKEN = os.getenv("GURU_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def guru_auth():
    if not EMAIL:
        raise SystemExit("GURU_EMAIL is not set in .env")
    if not TOKEN:
        raise SystemExit("GURU_TOKEN is not set in .env")
    
    return (EMAIL, TOKEN)

def fetch_collections():
    url = f"{GURU_API}/collections"

    r = requests.get(url, auth=guru_auth())

    if not r.ok:
        raise SystemExit(f"Could not list collections: {r.status_code} {r.text[:500]}")

    return [{"id": c["id"], "name": c["name"]} for c in r.json()]

def safe_filename(name):
    bad_chars = '<>:"/|?*'
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.strip()

def export_collection(collection): 
    collection_id = collection["id"]
    name = collection["name"]

    url = f"{GURU_API}/collections/{collection_id}/export/advanced"

    if not WEBHOOK_URL:
        raise SystemExit("WEBHOOK_URL is not set in .env")

    r = requests.post(
        url,
        auth = guru_auth(),
        json = {
            "notificationEndpoint": WEBHOOK_URL,
            "type":"export-collection",

        }
    )

    if not r.ok:
        print(f"Export failed for {name}: {r.status_code} {r.text[:500]}")
        return None

    print(f"Started export for {name}")
    print(r.text[:500])
    
    return r.content


def main():
    collections = fetch_collections()

    print(f"Found {len(collections)} collection(s):")

    print("\nStarting export jobs...")
    for collection in collections:
        export_collection(collection)

if __name__ == "__main__":
    main()