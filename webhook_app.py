import os
import re
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv
 
from sharepoint import upload_zip_to_sharepoint
 
load_dotenv()
 
app = FastAPI()
 
# Match these names to what download_guru_export() actually uses.
EMAIL = (os.getenv("GURU_EMAIL") or "").strip()
TOKEN = (os.getenv("GURU_TOKEN") or "").strip()
 
 
def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip() or "guru_export"
 
 
def download_guru_export(export_url):
    # Step 1: hit Guru with auth to get the redirect URL
    r = requests.get(
        export_url,
        auth=(GURU_EMAIL, GURU_TOKEN),
        allow_redirects=False,  # don't follow automatically
    )

    print(f"[download] step1 status={r.status_code} location={r.headers.get('Location')}")

    # Step 2: if redirected, follow WITHOUT auth (S3 doesn't want it)
    if r.status_code in (301, 302, 303, 307, 308):
        s3_url = r.headers["Location"]
        r = requests.get(s3_url)  # no auth header
        print(f"[download] step2 status={r.status_code} content-type={r.headers.get('content-type')}")

    if not r.ok:
        raise RuntimeError(f"Guru download failed: {r.status_code} {r.text[:200]}")

    return r.content
 
 
# --- Routes (must live at module level so FastAPI registers them) ---
 
@app.get("/")
def health_check():
    return {"status": "running"}
 
 
@app.post("/guru-webhook")
async def guru_webhook(request: Request):
    payload = await request.json()
    print("Guru webhook payload:", payload)
 
    export_url = payload.get("exportUrl")
    # The collection name is nested under "collection" in Guru's payload.
    collection = payload.get("collection") or {}
    collection_name = collection.get("name", "guru_export")
 
    if not export_url:
        return {
            "status": "ignored",
            "reason": "No exportUrl found",
            "payload": payload,
        }
 
    filename = f"{safe_filename(collection_name)}.zip"
 
    zip_bytes = download_guru_export(export_url)
    print(f"Downloaded {filename}: {len(zip_bytes)} bytes")
 
    # While SharePoint isn't finished, set SKIP_SHAREPOINT=1 in Render to
    # confirm the webhook + Guru download work without the upload step.
    if os.getenv("SKIP_SHAREPOINT") == "1":
        return {"status": "downloaded", "filename": filename, "bytes": len(zip_bytes)}
 
    result = upload_zip_to_sharepoint(filename, zip_bytes)
 
    return {
        "status": "uploaded",
        "filename": filename,
        "sharepoint_id": result.get("id") if isinstance(result, dict) else None,
    }