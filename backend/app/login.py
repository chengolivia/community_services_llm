import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import jwt
from typing import Optional

DATABASE_PATH = "data/wellness_database.db"
SECRET_KEY = "your_secret_key_here"  # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

def hash_password(password):
    """Create secure password hash with salt."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                 salt.encode('utf-8'), 100000)
    return salt, pwdhash.hex()

def verify_password(stored_password, stored_salt, provided_password):
    """Verify password against stored hash."""
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), 
                                stored_salt.encode('utf-8'), 100000)
    return pwdhash.hex() == stored_password

def create_user(username, password, role='provider'):
    """Create a new user with secure password storage."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists"
    
    # Hash password
    salt, password_hash = hash_password(password)
    
    # Insert new user
    try:
        cursor.execute('''
        INSERT INTO users (username, password_hash, salt, role)
        VALUES (?, ?, ?, ?)
        ''', (username, password_hash, salt, role))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error creating user: {str(e)}"

def authenticate_user(username, password):
    """Authenticate a user based on username and password."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT username, password_hash, salt, role FROM users 
    WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return False, "Invalid username or password", None
    
    stored_username, stored_password, stored_salt, role = user
    
    if verify_password(stored_password, stored_salt, password):
        return True, "Authentication successful", role
    else:
        return False, "Invalid username or password", None

def verify_password(stored_password, stored_salt, provided_password):
    """Verify password against stored hash."""
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'),
                                 stored_salt.encode('utf-8'), 100000)
    return pwdhash.hex() == stored_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt