from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import timedelta
import jwt
from jwt.exceptions import InvalidTokenError
import os
from typing import Optional
from datetime import datetime, timedelta
from app.database import CONNECTION_STRING
import hashlib
import secrets
import psycopg

SECRET_KEY = os.getenv("SECRET_KEY")  # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

# Request/Response Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    organization: str

class UserData(BaseModel):
    username: str
    role: str

# JWT Token Verification Dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserData:
    """
    Dependency to verify JWT token and extract user info.
    Use this in your protected routes.
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        
        if username is None or role is None:
            raise credentials_exception
            
        return UserData(username=username, role=role)
    except InvalidTokenError:
        raise credentials_exception

# Login Endpoint
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token
    """
    success, message, role, organization = authenticate_user(request.username, request.password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username, "role": role, "organization": organization},
        expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token,
        role=role,
        organization=organization
    )

class RegisterRequest(BaseModel):
    username: str
    password: str
    organization: Optional[str] = 'cspnj'

@router.post("/register")
async def register(request: RegisterRequest):
    success, message = create_user(
        username=request.username,
        password=request.password,
        role='provider',
        organization=request.organization
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


def hash_password(password):
    """Create secure password hash with salt
    
    Arguments:
        password: string, password to hash
    
    Returns: a secret salt and a hashed password under that salt"""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                 salt.encode('utf-8'), 100000)
    return salt, pwdhash.hex()


def create_user(username, password, role='provider', organization='cspnj'):
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists"

    salt, password_hash = hash_password(password)

    try:
        cursor.execute('''
        INSERT INTO users (username, password_hash, salt, role, organization)
        VALUES (%s, %s, %s, %s, %s)
        ''', (username, password_hash, salt, role, organization))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error creating user: {str(e)}"

# Protected route example
@router.get("/me", response_model=UserData)
async def get_current_user_info(current_user: UserData = Depends(get_current_user)):
    """
    Get current user information (protected route example)
    """
    return current_user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token for a given set of information
    
    Arguments:
        data: Username/authentication to encode
    
    Returns: Encoded version of data via JWT"""
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username, password):
    """Authenticate a username + password combo
    
    Arguments:
        username: string, username
        password: string, password
    
    Returns: Boolean success and string message 
    
    Side Effects: Checks if a username-password combo is valid"""
    
    print(CONNECTION_STRING)

    conn = psycopg.connect(CONNECTION_STRING)
    print(CONNECTION_STRING)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT username, password_hash, salt, role, organization FROM users 
    WHERE username = %s
    ''', (username,))
    print("EXECUTED")
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return False, "Invalid username or password", None
    
    _, stored_password, stored_salt, role, organization = user
    
    if verify_password(stored_password, stored_salt, password):
        return True, "Authentication successful", role, organization
    else:
        return False, "Invalid username or password", None, None

def verify_password(stored_password, stored_salt, provided_password):
    """Verify password against stored hash
    
    Arguments:
        stored_password: string, some stored password
        stored_salt: Corresponding salt for that password
        provided_password: What the user entered
    
    Returns: Boolean, whether the provided_password = stored password"""
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), 
                                stored_salt.encode('utf-8'), 100000)
    return pwdhash.hex() == stored_password
