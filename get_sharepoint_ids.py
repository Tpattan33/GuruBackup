import requests, os
from dotenv import load_dotenv
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_VALUE = os.getenv("SECRET_VALUE")

# Get token
r = requests.post(
    f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": SECRET_VALUE,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
)
token = r.json().get("access_token")
print("Auth:", r.status_code)

# Get site ID
r2 = requests.get(
    "https://graph.microsoft.com/v1.0/sites/njmqa.sharepoint.com:/sites/GURUQA",
    headers={"Authorization": f"Bearer {token}"}
)
print("Site:", r2.status_code)
print(r2.text[:300])

# Get drive ID
site_id = "njmqa.sharepoint.com,9066e095-d215-42da-9fdb-236660f7a746,1da66b47-41ef-47dc-acc0-a6fd1567199e"
r3 = requests.get(
    f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives",
    headers={"Authorization": f"Bearer {token}"}
)
print("Drives:", r3.status_code)
print(r3.text[:500])