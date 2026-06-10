"""
Market Digest - Teams Auth + Discovery (single session)
Run: python list_teams.py
Signs in via device code, caches token to disk, lists all your Teams & channels.
"""
import json, sys, os, msal, requests

TOKEN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".teams_token_cache.json")
CLIENT_ID   = "d3590ed6-52b3-4102-aeff-aad2292ab01c"  # Microsoft Office public client
LOGIN_HINT  = "karthikeyan.parthiban@shriramcredit.in"
AUTHORITY   = "https://login.microsoftonline.com/shriramcredit.in"
SCOPES      = [
    "https://graph.microsoft.com/Team.ReadBasic.All",
    "https://graph.microsoft.com/Channel.ReadBasic.All",
    "https://graph.microsoft.com/ChannelMessage.Send",
    "https://graph.microsoft.com/Files.ReadWrite.All",
]

# --- Load cache ---
cache = msal.SerializableTokenCache()
if os.path.exists(TOKEN_CACHE_FILE):
    cache.deserialize(open(TOKEN_CACHE_FILE).read())

app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

# --- Try silent first ---
accounts = app.get_accounts()
result = None
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])

# --- Device code if needed ---
if not result or "access_token" not in result:
    flow = app.initiate_device_flow(scopes=SCOPES)
    print("\n" + "="*60)
    print("  ACTION REQUIRED: Sign in to Microsoft")
    print("="*60)
    print(flow["message"])
    print("="*60)
    sys.stdout.flush()
    result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    print("ERROR:", result.get("error_description", result))
    sys.exit(1)

# --- Persist cache ---
with open(TOKEN_CACHE_FILE, "w") as f:
    f.write(cache.serialize())
print("Token cached to", TOKEN_CACHE_FILE)

token   = result["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# --- List Teams ---
print("\nFetching your Teams ...\n")
resp = requests.get("https://graph.microsoft.com/v1.0/me/joinedTeams", headers=headers)
resp.raise_for_status()
teams = resp.json().get("value", [])

if not teams:
    print("No Teams found for this account.")
    sys.exit(0)

print(f"{'#':<4} {'Team Name':<40} {'Team ID'}")
print("-"*100)
for i, t in enumerate(teams, 1):
    print(f"{i:<4} {t['displayName']:<40} {t['id']}")

print()
print("Fetching channels for each team ...\n")

for t in teams:
    ch_resp = requests.get(f"https://graph.microsoft.com/v1.0/teams/{t['id']}/channels", headers=headers)
    if not ch_resp.ok:
        continue
    channels = ch_resp.json().get("value", [])
    print(f"  Team: {t['displayName']}")
    print(f"  Team ID: {t['id']}")
    for ch in channels:
        print(f"    Channel: {ch['displayName']:<35} ID: {ch['id']}")
    print()

print("="*60)
print("Copy the Team ID and Channel ID you want to post to.")
print("="*60)
