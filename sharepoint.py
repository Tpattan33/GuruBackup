#imports
from dotenv import load_dotenv
import requests
import json
import os

# loads all of the env variables
load_dotenv()
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_VALUE = os.getenv("SECRET_VALUE")
SITE_URL = os.getenv("SITE_ID")
DRIVE_ID = os.getenv("DRIVE_ID")
TARGET_FOLDER = os.getenv("TARGET_FOLDER", "Guru Backups")
GRAPH = "https://graph.microsoft.com/v1.0"
# must be a multiple of 320 KiB
CHUNK = 320 * 1024 * 10 
# Graph API Simple Upload Cap
SIMPLE_UPLOAD_MAX = 250 * 1024 * 1024

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
        raise SystemExit(f"Microsoft auth failed: {r.status_code} {r.text}")

    return r.json()["access_token"]

    if "access_token" not in result:
        raise SystemExit(f"Auth failed: {result.get('error_description', result)}")

def upload_zip_to_sharepoint(filename, zip_bytes):
    token = get_access_token()

    url = {
        f"{GRAPH}/drives/{DRIVE_ID}"
        f"/root:/{TARGET_FOLDER}/
        {filename}:/content"
    }
    r = requests.put(url, headers=headers, data=zip_bytes)

    if not r.ok:
        raise SystemExit(f"SharePoint upload failed: {r.status_code} {r.text:500}")

    return r.json

def _header(token):
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
   data()
#will be the file that takes the data, connects to the sharepoint server and uploads the data from GURU
