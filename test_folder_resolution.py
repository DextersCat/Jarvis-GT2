import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

source_doc_id = config.get("google_drive_folder_source_doc_id")
print(f"Source doc ID: {source_doc_id}")

# Load token
with open("token.json", "r") as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data.get("token"),
    refresh_token=token_data.get("refresh_token"),
    token_uri=token_data.get("token_uri"),
    client_id=token_data.get("client_id"),
    client_secret=token_data.get("client_secret"),
    scopes=token_data.get("scopes"),
)

if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())

# Build services
docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

# Resolve folder ID from source doc
file_info = drive_service.files().get(
    fileId=source_doc_id,
    fields="name, parents"
).execute()

doc_name = file_info.get("name")
parents = file_info.get("parents", [])
folder_id = parents[0] if parents else None

print(f"Source doc name: {doc_name}")
print(f"Resolved folder ID: {folder_id}")

# Get folder name
if folder_id:
    try:
        folder_info = drive_service.files().get(
            fileId=folder_id,
            fields="name"
        ).execute()
        folder_name = folder_info.get("name")
        print(f"Folder name: {folder_name}")
    except Exception as e:
        folder_name = f"Unknown (ID: {folder_id})"
        print(f"⚠️ Could not access folder: {e}")
        print(f"Folder ID: {folder_id}")
    
    # Create a test document in that folder
    test_doc_title = f"Jarvis Test File - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    test_content = f"This is a test file created by Jarvis to verify folder resolution.\n\nTimestamp: {datetime.now().isoformat()}\nFolder: {folder_name}\nFolder ID: {folder_id}"
    
    # Create doc
    doc = docs_service.documents().create(body={"title": test_doc_title}).execute()
    doc_id = doc.get("documentId")
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    
    # Write content
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [{
                "insertText": {
                    "location": {"index": 1},
                    "text": test_content
                }
            }]
        }
    ).execute()
    
    # Move to folder
    try:
        previous_parents = ",".join(
            drive_service.files().get(
                fileId=doc_id,
                fields="parents"
            ).execute().get("parents", [])
        )
        
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents"
        ).execute()
        
        print(f"\n✅ SUCCESS!")
        print(f"Document created: {test_doc_title}")
        print(f"URL: {doc_url}")
        print(f"Location: {folder_name}")
    except Exception as move_error:
        print(f"\n⚠️ PARTIAL SUCCESS")
        print(f"Document created: {test_doc_title}")
        print(f"URL: {doc_url}")
        print(f"⚠️ Could not move to folder '{folder_name}': {move_error}")
        print(f"Document is in your Drive root - please move manually")
else:
    print("❌ Could not resolve folder ID")
