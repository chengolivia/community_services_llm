import sqlite3
import csv
from pathlib import Path

# Database setup
DATABASE_PATH = "data/wellness_database.db"

def init_database():
    """Create the database and tables if they don't exist."""
    # Create data directory if it doesn't exist
    Path("data").mkdir(exist_ok=True)
    
    # Create database connection and cursor
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table for authentication
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create profiles table (equivalent to profiles.csv)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_user_id TEXT UNIQUE NOT NULL,
        service_user_name TEXT NOT NULL,
        provider TEXT NOT NULL,
        location TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create outreach_details table (equivalent to outreach_details.csv)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS outreach_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        last_session TEXT,
        check_in TEXT,
        follow_up_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_name) REFERENCES profiles(service_user_id)
    )
    ''')

    # Conversations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        UNIQUE(conversation_id, sender, text)
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()

def migrate_data_from_csv():
    """Migrate existing CSV data to SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Migrate profiles data
    try:
        with open("data/profiles.csv", 'r') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                cursor.execute('''
                INSERT OR IGNORE INTO profiles 
                (service_user_id, service_user_name, provider, location, status)
                VALUES (?, ?, ?, ?, ?)
                ''', (row['service_user_id'], row['service_user_name'], 
                      row['provider'], row.get('location', ''), row.get('status', 'Active')))
    except FileNotFoundError:
        print("profiles.csv not found, skipping migration")
    
    # Migrate outreach details data
    try:
        with open("data/outreach_details.csv", 'r') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                cursor.execute('''
                INSERT OR IGNORE INTO outreach_details
                (user_name, last_session, check_in, follow_up_message)
                VALUES (?, ?, ?, ?)
                ''', (row['user_name'], row['last_session'], 
                      row['check_in'], row['follow_up_message']))
    except FileNotFoundError:
        print("outreach_details.csv not found, skipping migration")
    
    conn.commit()
    conn.close()
    print("Data migration complete")


def update_conversation(metadata, previous_text):
    """
    Save the messages in `previous_text` to the database under the conversation and user specified in `metadata`.

    `metadata` should include:
        - 'username': str
        - 'conversation_id': str
        - 'model': str (optional)
        - 'organization': str (optional)

    `previous_text` should be a list of dicts like:
        [{"sender": "user", "text": "Hello"}, {"sender": "assistant", "text": "Hi"}]
    """
    username = metadata.get("username")
    conversation_id = metadata.get("conversation_id")

    if username == "" or conversation_id == "":
        print("[update_conversation] Skipping: missing username or conversation_id.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Insert conversation row if it doesn't already exist
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO conversations (id, username) VALUES (?, ?)",
            (conversation_id, username)
        )

    # Insert each message
    for msg in previous_text:
        sender = msg["role"]
        text = msg["content"]
        if sender and text:
            print("Inserting {} {}".format(sender,text))
            cursor.execute(
                "INSERT OR IGNORE INTO messages (conversation_id, sender, text) VALUES (?, ?, ?)",
                (conversation_id, sender, text)
            )

    conn.commit()
    conn.close()