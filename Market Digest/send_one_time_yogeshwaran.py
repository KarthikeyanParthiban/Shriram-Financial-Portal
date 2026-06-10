import os
import sys
import json
import uuid
from datetime import datetime
import msal
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_CACHE_FILE = os.path.join(BASE_DIR, ".teams_token_cache.json")
CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
AUTHORITY = "https://login.microsoftonline.com/shriramcredit.in"
SCOPES = [
    "https://graph.microsoft.com/Files.ReadWrite.All",
    "https://graph.microsoft.com/Chat.ReadWrite"
]

YOGESHWARAN_CHAT_ID = "19:b5e3ad77-8eff-43cb-bf80-b87b5841783f_c8d39d06-25ac-4e3c-851c-d26fa18c8530@unq.gbl.spaces"
MY_EMAIL = "karthikeyan.parthiban@shriramcredit.in"

def main():
    print("Market Digest - Sending one-time report to Yogeshwaran N with permissions...")
    
    # 1. Load MSAL token cache
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        cache.deserialize(open(TOKEN_CACHE_FILE).read())
    else:
        print(f"Error: Token cache not found at {TOKEN_CACHE_FILE}")
        sys.exit(1)

    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()
    if not accounts:
        print("Error: No authenticated accounts found. Please re-authenticate.")
        sys.exit(1)

    # 2. Acquire token silently
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result or "access_token" not in result:
        print("Error: Could not acquire token silently.")
        sys.exit(1)

    token = result["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3. Locate the PDF report file
    today_str = datetime.now().strftime("%Y-%m-%d")
    project_dir = BASE_DIR
    pdf_path = os.path.join(project_dir, "output", "report.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF report not found at {pdf_path}")
        sys.exit(1)

    file_size = os.path.getsize(pdf_path)
    file_name = f"Market-Digest-{today_str}.pdf"
    print(f"Found PDF report: {file_name} ({file_size} bytes)")

    # 4. Fetch chat members to find the recipient's email
    print(f"Fetching members of chat {YOGESHWARAN_CHAT_ID}...")
    members_resp = requests.get(f"https://graph.microsoft.com/v1.0/chats/{YOGESHWARAN_CHAT_ID}/members", headers=headers)
    if not members_resp.ok:
        print(f"Error: Failed to fetch chat members: {members_resp.status_code}")
        print(members_resp.text)
        sys.exit(1)
        
    members = members_resp.json().get("value", [])
    recipient_emails = []
    for m in members:
        email = m.get("email")
        if email and email.lower() != MY_EMAIL.lower():
            recipient_emails.append(email)
            
    if not recipient_emails:
        # Fallback to direct guess if members query fails to return other emails
        recipient_emails = ["yogeshwaran.n@shriramcredit.in"]
        
    print(f"Target recipient email(s) for file sharing: {recipient_emails}")

    # 5. Upload file to OneDrive via Microsoft Graph API
    onedrive_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Market Digest/one_time/{file_name}:/content"
    print(f"Uploading PDF to OneDrive folder '/Market Digest/one_time/{file_name}'...")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/pdf"
    }
    
    upload_resp = requests.put(onedrive_url, headers=upload_headers, data=pdf_bytes)
    if not upload_resp.ok:
        print(f"Error: Failed to upload file to OneDrive. Status: {upload_resp.status_code}")
        print(upload_resp.text)
        sys.exit(1)

    drive_item = upload_resp.json()
    item_id = drive_item.get("id")
    web_url = drive_item.get("webUrl")
    print(f"Upload successful! File ID: {item_id}")
    print(f"Web URL: {web_url}")

    # 6. Grant read permission to recipient(s) via /invite
    invite_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/invite"
    invite_payload = {
        "recipients": [{"email": email} for email in recipient_emails],
        "roles": ["read"],
        "requireSignIn": True,
        "sendInvitation": False
    }
    print(f"Granting read permissions to {recipient_emails}...")
    invite_resp = requests.post(invite_url, headers=headers, json=invite_payload)
    if not invite_resp.ok:
        print(f"Error: Failed to grant file permissions via Graph API. Status: {invite_resp.status_code}")
        print(invite_resp.text)
        sys.exit(1)
        
    print("Permissions successfully granted!")

    # 7. Share item in the one-on-one chat using message attachments schema
    attachment_id = str(uuid.uuid4())
    
    message_payload = {
        "body": {
            "contentType": "html",
            "content": f"📊 <b>Market Digest — {datetime.now().strftime('%d %b %Y')}</b> is ready.<br><br>Here is the corporate report, Yogeshwaran: <attachment id=\"{attachment_id}\"></attachment>"
        },
        "attachments": [
            {
                "id": attachment_id,
                "contentType": "reference",
                "contentUrl": web_url,
                "name": file_name
            }
        ]
    }

    # 8. Post the message to the one-on-one chat
    post_message_url = f"https://graph.microsoft.com/v1.0/chats/{YOGESHWARAN_CHAT_ID}/messages"
    print(f"Posting message to Yogeshwaran N's chat ({YOGESHWARAN_CHAT_ID})...")
    
    post_resp = requests.post(post_message_url, headers=headers, json=message_payload)
    if not post_resp.ok:
        print(f"Error: Failed to post message. Status: {post_resp.status_code}")
        print(post_resp.text)
        sys.exit(1)

    print("Success! Message with PDF attachment successfully sent to Yogeshwaran N with download access.")
    print("="*60)

if __name__ == "__main__":
    main()
