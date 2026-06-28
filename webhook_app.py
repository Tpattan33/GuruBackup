import os
import re
import base64
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
    headers = {"Authorization": f"Basic {encoded}"}

    r = requests.get(export_url, headers=headers, allow_redirects=False)
    print(f"[download] step1 status={r.status_code} location={r.headers.get('Location')}")

    if r.status_code in (301, 302, 303, 307, 308):
        s3_url = r.headers["Location"]
        r = requests.get(s3_url)
        print(f"[download] step2 status={r.status_code} content-type={r.headers.get('content-type')}")

    if not r.ok:
        raise RuntimeError(f"Guru download failed: {r.status_code} {r.text[:200]!r}")

    return r.content


# --- Routes ---

@app.get("/")
def health_check():
    return {"status": "running"}


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

    if os.getenv("SKIP_SHAREPOINT") == "1":
        zip_bytes = download_guru_export(export_url)
        return {"status": "downloaded", "filename": filename, "bytes": len(zip_bytes)}

    zip_bytes = download_guru_export(export_url)
    result = upload_zip_to_sharepoint(filename, zip_bytes)

    return {
        "status": "uploaded",
        "filename": filename,
        "sharepoint_id": result.get("id") if isinstance(result, dict) else None,
    }