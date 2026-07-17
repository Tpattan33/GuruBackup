import os
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_VALUE = os.getenv("SECRET_VALUE")
SITE_ID = os.getenv("SITE_ID")
DRIVE_ID = os.getenv("DRIVE_ID")
TARGET_FOLDER = os.getenv("TARGET_FOLDER", "Guru Backups")
GRAPH = "https://graph.microsoft.com/v1.0"

CHUNK = 320 * 1024 * 10  # must be a multiple of 320 KiB
SIMPLE_UPLOAD_MAX = 4 * 1024 * 1024  # 4MB - use simple upload below this


def get_access_token():
    """Client-credentials flow -> returns a Microsoft Graph access token."""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": SECRET_VALUE,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    r = requests.post(url, data=data)

    if not r.ok:
        raise RuntimeError(f"Microsoft auth failed: {r.status_code} {r.text}")

    return r.json()["access_token"]


def upload_zip_to_sharepoint(filename, zip_bytes):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    file_size = len(zip_bytes)
    print(f"[sharepoint] uploading {filename} ({file_size} bytes) to {TARGET_FOLDER}/")

    if file_size <= SIMPLE_UPLOAD_MAX:
        # Simple upload for small files
        url = f"{GRAPH}/drives/{DRIVE_ID}/root:/{TARGET_FOLDER}/{filename}:/content"
        r = requests.put(url, headers={**headers, "Content-Type": "application/zip"}, data=zip_bytes)

        if not r.ok:
            raise RuntimeError(f"SharePoint upload failed: {r.status_code} {r.text[:500]}")

        print(f"[sharepoint] uploaded successfully")
        return r.json()

    else:
        # Chunked upload for large files
        # Create upload session
        session_url = f"{GRAPH}/drives/{DRIVE_ID}/root:/{TARGET_FOLDER}/{filename}:/createUploadSession"
        r = requests.post(session_url, headers=headers, json={
            "item": {"@microsoft.graph.conflictBehavior": "replace"}
        })

        if not r.ok:
            raise RuntimeError(f"Failed to create upload session: {r.status_code} {r.text[:500]}")

        upload_url = r.json()["uploadUrl"]

        # Upload in chunks
        offset = 0
        while offset < file_size:
            chunk = zip_bytes[offset:offset + CHUNK]
            chunk_size = len(chunk)
            end = offset + chunk_size - 1

            r = requests.put(
                upload_url,
                headers={
                    "Content-Length": str(chunk_size),
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                },
                data=chunk,
            )

            if not r.ok and r.status_code != 202:
                raise RuntimeError(f"Chunk upload failed: {r.status_code} {r.text[:500]}")

            print(f"[sharepoint] uploaded {end + 1}/{file_size} bytes")
            offset += chunk_size

        print(f"[sharepoint] upload complete")
        return r.json()