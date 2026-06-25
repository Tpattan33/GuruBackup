import os
import re
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

from sharepoint import upload_zip_to_sharepoint

load_dotenv

EMAIL = os.getenv("GURU_EMAIL")
TOKEN = os.getenv("GURU_TOKEN")

def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip() or "guru_export"

def download_guru_export(export_url):
    r = requests.get(
        export_url,
        auth=(GURU_EMAIL, GURU_TOKEN),
        stream=True,
    )
    
    if not r.ok:
        raise RuntimeError(f"Guru download failed: {r.status_code} {r.text[:500]}")

    return r.content

    @app.get("/")
    def health_check():
        return {"status": "running"}

    @app.post("/guru-webhook")
    async def guru_webook(request: Request):
        payload = await request.json()

        print("Guru webhook payload:", payload)

        export_url = payload.get("exportUrl")
        collection_name = payload.get("name", "guru_export")

        if not export_url:
            return {
                "status": "ignored",
                "reason": "No exportUrl found"
                "payload": paylod,
            }

        filename = f"{safe_filename(collection_name)}.zip"

        zip_bytes = download_guru_export(export_url)

        result = upload_zip_to_sharepoint(filename, zip_bytes)

        return {
            "status": "uploaded",
            "filename": filename,
            "sharepoint_id":
            result.get("id"),
        }