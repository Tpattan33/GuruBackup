import os
import re
import base64
import time
import tempfile
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

from sharepoint import upload_zip_to_sharepoint

load_dotenv()

app = FastAPI()

GURU_EMAIL = os.getenv("GURU_EMAIL")
GURU_TOKEN = os.getenv("GURU_TOKEN")


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip() or "guru_export"


def download_guru_export(export_url):
    print(f"[creds] email={GURU_EMAIL!r} token_len={len(GURU_TOKEN) if GURU_TOKEN else None}")

    if not GURU_EMAIL or not GURU_TOKEN:
        raise RuntimeError("GURU_EMAIL or GURU_TOKEN is missing from Render environment variables")

    credentials = f"{GURU_EMAIL}:{GURU_TOKEN}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "User-Agent": "curl/8.13.0",
        "Accept": "*/*",
    }

    delays = [30, 60, 120, 180, 240, 300]
    for attempt, delay in enumerate(delays, 1):
        print(f"[download] attempt {attempt}, waiting {delay}s...")
        time.sleep(delay)

        r = requests.get(export_url, headers=headers, allow_redirects=True, stream=True)
        print(f"[download] status={r.status_code}")

        if r.ok:
            # Stream to temp file instead of loading into memory
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp.close()
            print(f"[download] saved to {tmp.name}")
            return tmp.name  # return file path instead of bytes

        print(f"[download] not ready yet, will retry...")

    raise RuntimeError(f"Guru download failed after all retries: {r.status_code}")


# --- Routes ---

@app.get("/")
def health_check():
    return {"status": "running"}


@app.get("/test-creds")
def test_creds(url: str = ""):
    """Test if Render's credentials can download a Guru export URL.
    Usage: /test-creds?url=https://content.api.getguru.com/files/dn/YOUR-UUID
    """
    if not url:
        return {"error": "Pass a ?url= parameter with a fresh exportUrl from your logs"}

    credentials = f"{GURU_EMAIL}:{GURU_TOKEN}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "User-Agent": "curl/8.13.0",
        "Accept": "*/*",
    }

    r = requests.get(url, headers=headers, allow_redirects=True)
    return {
        "status": r.status_code,
        "content_type": r.headers.get("content-type"),
        "content_length": r.headers.get("content-length"),
        "final_url": r.url,
        "body_preview": r.text[:200] if not r.ok else "OK - got content",
    }


@app.post("/trigger-exports")
def trigger_exports():
    """Trigger all Guru collection exports from Render's IP."""
    from guru import fetch_collections, export_collection
    collections = fetch_collections()
    for c in collections:
        export_collection(c)
    return {"status": "triggered", "count": len(collections)}


@app.post("/guru-webhook")
async def guru_webhook(request: Request):
    payload = await request.json()
    print("Guru webhook payload:", payload)

    export_url = payload.get("exportUrl")
    collection = payload.get("collection") or {}
    collection_name = collection.get("name", "guru_export")

    if not export_url:
        return {"status": "ignored", "reason": "No exportUrl found"}

    filename = f"{safe_filename(collection_name)}.zip"
    tmp_path = download_guru_export(export_url)

    try:
        if os.getenv("SKIP_SHAREPOINT") == "1":
            size = os.path.getsize(tmp_path)
            return {"status": "downloaded", "filename": filename, "bytes": size}

        with open(tmp_path, "rb") as f:
            zip_bytes = f.read()

        result = upload_zip_to_sharepoint(filename, zip_bytes)

        return {
            "status": "uploaded",
            "filename": filename,
            "sharepoint_id": result.get("id") if isinstance(result, dict) else None,
        }
    finally:
        # Always clean up the temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"[cleanup] removed {tmp_path}")