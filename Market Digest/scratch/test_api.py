import requests

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    session = requests.Session()
    
    # 1. Access index page without login (should redirect to /login)
    print("Testing auth redirection...")
    r = session.get(f"{BASE_URL}/", allow_redirects=False)
    print(f"Index access (no login) status: {r.status_code}")
    print(f"Location: {r.headers.get('Location')}")
    assert r.status_code == 302
    assert "/login" in r.headers.get("Location")

    # 2. Login with correct admin credentials
    print("\nTesting login...")
    login_data = {
        "mobile": "9791117131",
        "password": "admin"
    }
    r = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"Login response status: {r.status_code}")
    print(f"Redirect Location: {r.headers.get('Location')}")
    assert r.status_code == 302
    assert r.headers.get("Location") == "/"

    # 3. Retrieve user list
    print("\nRetrieving user list...")
    r = session.get(f"{BASE_URL}/api/admin/users")
    print(f"GET /api/admin/users status: {r.status_code}")
    users = r.json()
    print(f"Users: {users}")
    assert any(u['mobile'] == '9791117131' for u in users)

    # 4. Create a new user
    print("\nCreating new test user...")
    new_user = {
        "mobile": "9999988888",
        "password": "password123",
        "role": "user"
    }
    r = session.post(f"{BASE_URL}/api/admin/users", json=new_user)
    print(f"POST /api/admin/users status: {r.status_code}")
    res = r.json()
    print(f"Response: {res}")
    assert res.get("ok") is True

    # 5. List users again and verify the new user exists
    r = session.get(f"{BASE_URL}/api/admin/users")
    users = r.json()
    test_user_obj = next((u for u in users if u['mobile'] == '9999988888'), None)
    assert test_user_obj is not None
    print(f"Test user found: {test_user_obj}")

    # 6. Update password for the test user
    print("\nUpdating password for test user...")
    update_data = {
        "user_id": test_user_obj['id'],
        "password": "newpassword456"
    }
    r = session.put(f"{BASE_URL}/api/admin/users", json=update_data)
    print(f"PUT /api/admin/users status: {r.status_code}")
    assert r.json().get("ok") is True

    # 7. Delete the test user
    print("\nDeleting test user...")
    r = session.delete(f"{BASE_URL}/api/admin/users?user_id={test_user_obj['id']}")
    print(f"DELETE /api/admin/users status: {r.status_code}")
    assert r.json().get("ok") is True

    # 8. Check logs
    print("\nRetrieving system activity logs...")
    r = session.get(f"{BASE_URL}/api/admin/logs")
    print(f"GET /api/admin/logs status: {r.status_code}")
    logs = r.json()
    print("Latest 5 logs:")
    for log in logs[:5]:
        print(f"  {log['timestamp']} [{log['mobile']}] {log['action']}")
    
    print("\nAll API tests PASSED successfully!")

if __name__ == "__main__":
    test_flow()
