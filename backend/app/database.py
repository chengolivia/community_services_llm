import hashlib
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
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        service_user_id TEXT NOT NULL UNIQUE,
        last_session TEXT,
        check_in TEXT,
        follow_up_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (service_user_id) REFERENCES profiles(service_user_id) ON DELETE CASCADE
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
        id SERIAL PRIMARY KEY,
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

def update_conversation(metadata, previous_text, service_user_id):
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
            "INSERT INTO conversations (id, username,outreach_generated, service_user_id) VALUES (%s, %s, %s, %s)",
            (conversation_id, username,False, service_user_id)
        )

    for msg in previous_text:
        sender = msg["role"]
        text = msg["content"]
        if sender and text:
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender, text, service_user_id) VALUES (%s, %s, %s, %s) ON CONFLICT (conversation_id, sender, text) DO NOTHING",
                (conversation_id, sender, text, service_user_id)
            )

    conn.commit()
    conn.close()

def generate_service_user_id(provider_username: str, patient_name: str) -> str:
    """
    Deterministically generate a pseudonymous service user ID
    based on the provider and service user's names.
    """
    raw = f"{provider_username.strip().lower()}::{patient_name.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]  # short, unique, anonymized


def add_new_service_user(provider_username, patient_name, last_session, next_checkin, location,followup_message):
    """Create or update a service user's record using a deterministic hashed ID."""
    
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    try:
        # Generate deterministic, anonymized ID
        service_user_id = generate_service_user_id(provider_username, patient_name)
        print(f"[DEBUG] Deterministic ID for {provider_username}/{patient_name}: {service_user_id}")

        # Insert into profiles if not exists
        cursor.execute('''
        INSERT INTO profiles (service_user_id, service_user_name, provider, location, status)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (service_user_id) DO NOTHING
        ''', (service_user_id, patient_name, provider_username, location, "Active"))

        # Insert or update outreach details
        cursor.execute('''
        INSERT INTO outreach_details 
        (service_user_id, last_session, check_in, follow_up_message)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (service_user_id) DO UPDATE SET
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


