from sharepoint import upload_zip_to_sharepoint

# Upload a small test zip
test_bytes = b"PK\x05\x06" + b"\x00" * 18  # minimal valid zip
result = upload_zip_to_sharepoint("test_upload.zip", test_bytes)
print("Result:", result)