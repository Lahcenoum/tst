import sqlite3
import random
import string
from datetime import datetime

DB_FILE = 'ssh_bot_users.db'

def init_db_for_codes():
    """Initializes the necessary database tables for gift codes if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER, current_uses INTEGER DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS redeemed_users (code TEXT, telegram_user_id INTEGER, PRIMARY KEY (code, telegram_user_id))')
        # Ensure 'users' table exists for point updates, if not already handled by the main bot's init_db
        cursor.execute('CREATE TABLE IF NOT EXISTS users (telegram_user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, last_daily_claim DATE, join_bonus_claimed INTEGER DEFAULT 0, language_code TEXT DEFAULT "ar", created_date DATE)')
        conn.commit()
    print("Database initialized for gift code management.")

def create_gift_code(code_name, points, max_uses):
    """Creates a new gift code in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        try:
            conn.execute("INSERT INTO redeem_codes (code, points, max_uses, current_uses) VALUES (?, ?, ?, 0)",
                         (code_name, points, max_uses))
            conn.commit()
            print(f"✅ Code '{code_name}' created successfully. Grants {points} points and can be used {max_uses} times.")
        except sqlite3.IntegrityError:
            print(f"❌ Error: Code '{code_name}' already exists.")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

def redeem_gift_code_manual(code, user_id):
    """Simulates a user redeeming a gift code."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Ensure user exists (mimics get_or_create_user behavior)
        if not cursor.execute("SELECT 1 FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone():
            today = datetime.now().date().isoformat()
            cursor.execute("INSERT INTO users (telegram_user_id, points, created_date) VALUES (?, ?, ?)", (user_id, 0, today))
            conn.commit() # Commit user creation before proceeding

        code_data = cursor.execute("SELECT points, max_uses, current_uses FROM redeem_codes WHERE code = ?", (code,)).fetchone()
        
        if not code_data:
            print(f"❌ Code '{code}' is invalid or does not exist.")
            return False
        
        points, max_uses, current_uses = code_data
        if current_uses >= max_uses:
            print(f"❌ Code '{code}' has reached its maximum usage limit ({max_uses}).")
            return False
        
        if cursor.execute("SELECT 1 FROM redeemed_users WHERE code = ? AND telegram_user_id = ?", (code, user_id)).fetchone():
            print(f"❌ User {user_id} has already used code '{code}'.")
            return False
            
        cursor.execute("UPDATE users SET points = points + ? WHERE telegram_user_id = ?", (points, user_id))
        cursor.execute("UPDATE redeem_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
        cursor.execute("INSERT INTO redeemed_users (code, telegram_user_id) VALUES (?, ?)", (code, user_id))
        conn.commit()
        
        new_balance = cursor.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()[0]
        print(f"🎉 User {user_id} successfully redeemed code '{code}'. Received {points} points. New balance: {new_balance}.")
        return True

def list_all_codes():
    """Lists all existing gift codes and their status."""
    with sqlite3.connect(DB_FILE) as conn:
        codes = conn.execute("SELECT code, points, max_uses, current_uses FROM redeem_codes").fetchall()
    
    if not codes:
        print("ℹ️ No gift codes found.")
        return

    print("\n--- All Gift Codes ---")
    for code, points, max_uses, current_uses in codes:
        print(f"Code: {code}")
        print(f"  Points: {points}")
        print(f"  Max Uses: {max_uses}")
        print(f"  Current Uses: {current_uses}")
        print(f"  Remaining Uses: {max_uses - current_uses}")
        print("----------------------")

def get_user_points_manual(user_id):
    """Retrieves and prints a user's current points."""
    with sqlite3.connect(DB_FILE) as conn:
        result = conn.execute("SELECT points FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()
        if result:
            print(f"💰 User {user_id} current points: {result[0]}")
        else:
            print(f"ℹ️ User {user_id} not found in database.")

def generate_random_code(length=8):
    """Generates a random alphanumeric code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

if __name__ == "__main__":
    init_db_for_codes()

    while True:
        print("\n--- Gift Code Manager ---")
        print("1. Create New Code")
        print("2. Redeem Code (Manual Test)")
        print("3. List All Codes")
        print("4. Check User Points")
        print("5. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            name = input("Enter code name (e.g., WELCOME2025, leave empty for random): ").strip()
            if not name:
                name = generate_random_code()
                print(f"Generated random code: {name}")
            try:
                points = int(input("Enter points this code grants: "))
                uses = int(input("Enter max number of uses for this code: "))
                create_gift_code(name, points, uses)
            except ValueError:
                print("❌ Invalid input for points or uses. Please enter numbers.")
        elif choice == '2':
            code = input("Enter code to redeem: ")
            try:
                user_id = int(input("Enter Telegram User ID for redemption: "))
                redeem_gift_code_manual(code, user_id)
            except ValueError:
                print("❌ Invalid input for User ID. Please enter a number.")
        elif choice == '3':
            list_all_codes()
        elif choice == '4':
            try:
                user_id = int(input("Enter Telegram User ID to check points: "))
                get_user_points_manual(user_id)
            except ValueError:
                print("❌ Invalid input for User ID. Please enter a number.")
        elif choice == '5':
            print("Exiting Gift Code Manager.")
            break
        else:
            print("❌ Invalid choice. Please try again.")

