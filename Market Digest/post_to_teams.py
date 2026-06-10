import os
import sys
import json
import uuid
import re
from datetime import datetime
import msal
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_CACHE_FILE = os.path.join(BASE_DIR, ".teams_token_cache.json")
CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
AUTHORITY = "https://login.microsoftonline.com/shriramcredit.in"
SCOPES = [
    "https://graph.microsoft.com/Team.ReadBasic.All",
    "https://graph.microsoft.com/Channel.ReadBasic.All",
    "https://graph.microsoft.com/ChannelMessage.Send",
    "https://graph.microsoft.com/Files.ReadWrite.All",
    "https://graph.microsoft.com/Chat.ReadWrite"
]

# Configuration Modes
# Set TEST_MODE = True to send reports privately to yourself (Karthikeyan Parthiban) under Teams "Chat with Self"
# Set TEST_MODE = False to send reports publicly to the Market Digest channel
TEST_MODE = False

# Destination: AI Program Team -> Market Digest Channel
TEAM_ID = "6a45b7ad-4328-4d61-903b-78448e10acfb"
CHANNEL_ID = "19:160409b26fa04a6ca95f7c7a8d85fb5a@thread.tacv2"

# Alternative Group Chat/Self-Chat Destination (for testing)
PROD_CHAT_ID = "19:8ce891468d5f4562be392af8a8b2b8ba@thread.v2" # AI COE Group Chat
TEST_CHAT_ID = "48:notes" # Private Self-Chat / Notes

CHAT_ID = TEST_CHAT_ID if TEST_MODE else PROD_CHAT_ID

def main():
    print("Market Digest Teams Poster - Initializing...")
    
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
        print("Error: No authenticated accounts found. Please re-run list_teams.py to authenticate.")
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

    # 4. Upload file to OneDrive via Microsoft Graph API
    # Destination folder in OneDrive: "Market Digest"
    onedrive_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Market Digest/{file_name}:/content"
    print(f"Uploading PDF to OneDrive folder '/Market Digest/{file_name}'...")
    
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

    # 4.5. Fetch team members for permission sharing (skip in test mode)
    recipient_emails = []
    if not TEST_MODE:
        print(f"Fetching members of team {TEAM_ID}...")
        members_resp = requests.get(f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/members", headers=headers)
        if members_resp.ok:
            members = members_resp.json().get("value", [])
            my_email = "karthikeyan.parthiban@shriramcredit.in"
            for m in members:
                # Check both email and mail fields
                email = m.get("email") or m.get("mail")
                if email and email.lower() != my_email.lower():
                    recipient_emails.append(email)
        else:
            print(f"Warning: Failed to fetch team members. Status: {members_resp.status_code}")
    else:
        print("Self-chat test mode: skipping group member fetching and permission sharing.")

    # Helper function to grant OneDrive file read permissions
    def grant_permissions(target_item_id, target_emails):
        if not target_emails:
            return
        print(f"Sharing item {target_item_id} with: {target_emails}...")
        invite_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{target_item_id}/invite"
        invite_payload = {
            "recipients": [{"email": email} for email in target_emails],
            "roles": ["read"],
            "requireSignIn": True,
            "sendInvitation": False
        }
        invite_resp = requests.post(invite_url, headers=headers, json=invite_payload)
        if invite_resp.ok:
            print("Permissions successfully granted!")
        else:
            print(f"Warning: Failed to grant permissions. Status: {invite_resp.status_code}")
            print(invite_resp.text)

    # Grant permissions to the PDF file
    grant_permissions(item_id, recipient_emails)

    # 4.6. Extract PDF GUID from eTag
    etag = drive_item.get("eTag", "")
    match = re.search(r"\{([^}]+)\}", etag)
    pdf_guid = match.group(1).lower() if match else str(uuid.uuid4())

    # 4.7. Check and upload podcast audio if it exists
    podcast_path = os.path.join(project_dir, "output", "podcast.mp3")
    audio_uploaded = False
    audio_guid = None
    audio_web_url = None
    audio_file_name = f"Market-Digest-Podcast-{today_str}.mp3"

    if os.path.exists(podcast_path):
        print("Found podcast.mp3! Uploading to OneDrive...")
        audio_onedrive_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Market Digest/{audio_file_name}:/content"
        with open(podcast_path, "rb") as f:
            audio_bytes = f.read()

        audio_upload_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/mpeg"
        }
        audio_resp = requests.put(audio_onedrive_url, headers=audio_upload_headers, data=audio_bytes)
        if audio_resp.ok:
            audio_item = audio_resp.json()
            audio_item_id = audio_item.get("id")
            audio_web_url = audio_item.get("webUrl")
            print(f"Podcast upload successful! File ID: {audio_item_id}")
            
            # Grant permissions to the audio file
            grant_permissions(audio_item_id, recipient_emails)
            
            # Extract audio GUID from eTag
            audio_etag = audio_item.get("eTag", "")
            audio_match = re.search(r"\{([^}]+)\}", audio_etag)
            audio_guid = audio_match.group(1).lower() if audio_match else str(uuid.uuid4())
            audio_uploaded = True
        else:
            print(f"Warning: Failed to upload podcast to OneDrive: {audio_resp.text}")

    # 5. Share item in the group chat using message attachments schema
    now = datetime.now()
    if now.hour < 12:
        report_type = "Premarket Report"
        intro_text = "Here is your morning overview of overnight global markets and key triggers for the day ahead:"
    else:
        report_type = "Post-Market Close"
        intro_text = "Here is the closing summary of today's market performance, key highlights, and sentiment:"

    attachments_list = [
        {
            "id": pdf_guid,
            "contentType": "reference",
            "contentUrl": web_url,
            "name": file_name
        }
    ]

    if audio_uploaded:
        attachments_list.append({
            "id": audio_guid,
            "contentType": "reference",
            "contentUrl": audio_web_url,
            "name": audio_file_name
        })

        content_html = (
            f"📊 <b>Market Digest — {now.strftime('%d %b %Y')} ({report_type})</b> is ready.<br><br>"
            f"{intro_text}<br><br>"
            f"🎙️ <b>Listen to the Market Overview Podcast (Arjun & Neha):</b><br>"
            f"<attachment id=\"{audio_guid}\"></attachment><br><br>"
            f"📄 <b>View full PDF report:</b><br>"
            f"<attachment id=\"{pdf_guid}\"></attachment>"
        )
    else:
        content_html = (
            f"📊 <b>Market Digest — {now.strftime('%d %b %Y')} ({report_type})</b> is ready.<br><br>"
            f"{intro_text}<br><br>"
            f"<attachment id=\"{pdf_guid}\"></attachment>"
        )

    message_payload = {
        "body": {
            "contentType": "html",
            "content": content_html
        },
        "attachments": attachments_list
    }

    # 6. Post the message to Teams
    if TEST_MODE:
        post_message_url = f"https://graph.microsoft.com/v1.0/chats/{CHAT_ID}/messages"
        print(f"Posting message to Teams self-chat ({CHAT_ID})...")
    else:
        post_message_url = f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages"
        print(f"Posting message to Teams channel 'Market Digest' ({CHANNEL_ID})...")
    
    post_resp = requests.post(post_message_url, headers=headers, json=message_payload)
    if not post_resp.ok:
        print(f"Error: Failed to post message to Teams. Status: {post_resp.status_code}")
        print(post_resp.text)
        sys.exit(1)

    if TEST_MODE:
        print("Success! Message with PDF attachment successfully posted to self-chat.")
    else:
        print("Success! Message with PDF attachment successfully posted to the 'Market Digest' channel.")
    print("="*60)

if __name__ == "__main__":
    main()
