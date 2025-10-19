import psycopg
import csv
from pathlib import Path
import os
from .utils import BASE_DIR

CONNECTION_STRING = os.getenv("DATABASE_URL")


def init_database():
    """Initialize all the tables in database
     
    Arguments: None
     
    Returns: None
    
    Side Effects: Initialize all the databases"""

    Path("data").mkdir(exist_ok=True)
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY SERIAL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY SERIAL,
        service_user_id TEXT UNIQUE NOT NULL,
        service_user_name TEXT NOT NULL UNIQUE,
        provider TEXT NOT NULL,
        location TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS outreach_details (
        id INTEGER PRIMARY KEY SERIAL,
        user_name TEXT NOT NULL UNIQUE,
        last_session TEXT,
        check_in TEXT,
        follow_up_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_name) REFERENCES profiles(service_user_id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        outreach_generated BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY SERIAL,
        conversation_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        outreach_generated BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        UNIQUE(conversation_id, sender, text)
    )
    ''')
    
    conn.commit()
    conn.close()

def migrate_data_from_csv():
    """Transfer all the data from the CSV into databases
    
    Arguments: None
    
    Returns: None
    
    Side Effects: Loops through CSV and adds the data into database"""

    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    try:
        with open(BASE_DIR / "data/profiles.csv", 'r') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                cursor.execute('''
                INSERT INTO profiles 
                (service_user_id, service_user_name, provider, location, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (service_user_id) DO NOTHING
                ''', (row['service_user_id'], row['service_user_name'], 
                    row['provider'], row.get('location', ''), row.get('status', 'Active')))
    except FileNotFoundError:
        print("profiles.csv not found, skipping migration")
    
    try:
        with open(BASE_DIR / "data/outreach_details.csv", 'r') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                cursor.execute('''
                INSERT INTO outreach_details
                (user_name, last_session, check_in, follow_up_message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_name) DO NOTHING
                ''', (row['user_name'], row['last_session'], 
                    row['check_in'], row['follow_up_message']))
    except FileNotFoundError:
        print("outreach_details.csv not found, skipping migration")
    
    conn.commit()
    conn.close()

def update_conversation(metadata, previous_text):
    """
    Update the information in the conversations database
        Based on a new message

    Arguments:
        metadata: Dictionary with username and conversation_id
        previous_text: List of dictionaries with sender and text
    
    Returns: None

    Side Effects: Writes the text in previous_text to the database
    """
    username = metadata.get("username")
    conversation_id = metadata.get("conversation_id")
    
    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())
        print(f"[DB] Generated new conversation_id: {conversation_id}")

    if username == "" or conversation_id == "":
        return

    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM conversations WHERE id = %s", (conversation_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO conversations (id, username,outreach_generated) VALUES (%s, %s, %s)",
            (conversation_id, username,False)
        )

    for msg in previous_text:
        sender = msg["role"]
        text = msg["content"]
        if sender and text:
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender, text) VALUES (%s, %s, %s) ON CONFLICT (conversation_id, sender, text) DO NOTHING",
                (conversation_id, sender, text)
            )

    conn.commit()
    conn.close()

def add_new_wellness_checkin(provider_username, patient_name, last_session, next_checkin, followup_message):
    """Create a new entry for a new provider-service user combo, along with a followup message
    
    Arguments:
        provider_username: string, username of the peer provider
        patient_name: string, username of the service user
        last_session: string, date of the last session
        next_checkin: string, date for the next recommended checkin
        followup_message: string, suggested message to send the 
            service user"""
    
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    try:
        # Generate user ID
        base_id = f"{provider_username}_{patient_name.lower().replace(' ', '_')}"
        
        # Check for existing IDs with same base
        cursor.execute('''
        SELECT service_user_id FROM profiles 
        WHERE service_user_id LIKE %s
        ORDER BY service_user_id
        ''', (f"{base_id}%",))
        
        existing_ids = [row[0] for row in cursor.fetchall()]
        
        # Determine new ID
        if not existing_ids:
            service_user_id = base_id
        elif base_id in existing_ids:
            counter = 2
            while f"{base_id}_{counter}" in existing_ids:
                counter += 1
            service_user_id = f"{base_id}_{counter}"
        else:
            service_user_id = base_id
        
        print(f"[DEBUG] Generated ID: {service_user_id}")
        
        # Insert user id
        service_user_id = patient_name.lower().replace(" ", "_")
        cursor.execute('''
        SELECT service_user_id FROM profiles WHERE service_user_id = %s
        ''', (service_user_id,))
        
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO profiles (service_user_id, service_user_name, provider, location, status)
            VALUES (%s, %s, %s, %s, %s)
            ''', (service_user_id, patient_name, provider_username, "Freehold, New Jersey", "Active"))
        
        cursor.execute('''
        INSERT INTO outreach_details 
        (user_name, last_session, check_in, follow_up_message)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_name) DO UPDATE SET
            last_session = EXCLUDED.last_session,
            check_in = EXCLUDED.check_in,
            follow_up_message = EXCLUDED.follow_up_message
        ''', (service_user_id, last_session, next_checkin, followup_message))
        conn.commit()
        return True, f"Check-in saved successfully (ID: {service_user_id})"
    except Exception as e:
        conn.rollback()
        print(f"[DB Error] {e}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()


