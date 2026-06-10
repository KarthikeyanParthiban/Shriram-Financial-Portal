import sqlite3

DB_PATH = r"d:\Projects\Github\Market Digest\database.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if 9876543210 exists
    cursor.execute("SELECT * FROM users WHERE mobile = ?", ("9876543210",))
    old_admin = cursor.fetchone()
    
    if old_admin:
        # Check if 9791117131 already exists
        cursor.execute("SELECT * FROM users WHERE mobile = ?", ("9791117131",))
        new_admin = cursor.fetchone()
        
        if not new_admin:
            # Update the old admin to the new mobile number
            cursor.execute("UPDATE users SET mobile = ? WHERE mobile = ?", ("9791117131", "9876543210"))
            conn.commit()
            print("[DB Migration] Successfully migrated admin mobile from 9876543210 to 9791117131")
        else:
            # New admin already exists, just delete the old one
            cursor.execute("DELETE FROM users WHERE mobile = ?", ("9876543210",))
            conn.commit()
            print("[DB Migration] 9791117131 already exists, deleted old admin account 9876543210")
    else:
        print("[DB Migration] Old admin mobile 9876543210 not found. Checking 9791117131...")
        cursor.execute("SELECT * FROM users WHERE mobile = ?", ("9791117131",))
        if cursor.fetchone():
            print("[DB Migration] 9791117131 is already seeded.")
        else:
            print("[DB Migration] WARNING: No admin user found. DB will auto-seed 9791117131 on next app restart.")
            
    conn.close()

if __name__ == "__main__":
    migrate()
