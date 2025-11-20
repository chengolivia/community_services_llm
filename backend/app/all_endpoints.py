import asyncio
import os
import threading
import time
import secrets
from datetime import timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import socketio

from app.submodules import construct_response, fetch_goals_and_resources
from app.process_profiles import get_all_outreach, get_all_service_users
from app.login import (
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    create_user
)
from app.database import update_conversation, add_new_service_user

# Environment configuration
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_DEBUG_CPU_TYPE"] = "5"

# FastAPI setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.environ.get("FRONTEND_URL", ""),
        "https://peercopilot.com",
        "https://www.peercopilot.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    organization: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    organization: str

class NewWellness(BaseModel):
    patientName: str
    lastSession: str
    nextCheckIn: str
    followUpMessage: str
    username: str
    location: str

# Middleware
@app.middleware("http")
async def add_keep_alive_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Connection"] = "keep-alive"
    return response

# Auth endpoints
@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    print(f"Login attempt for user: {login_data.username}")
    success, _, role, organization = authenticate_user(
        login_data.username, 
        login_data.password
    )
    
    if not success:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={
            "sub": login_data.username, 
            "role": role, 
            "organization": organization
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role,
        organization=organization
    )

@app.post("/api/auth/register")
async def register(register_data: RegisterRequest):
    """Register a new user and auto-login."""
    success, message = create_user(
        username=register_data.username,
        password=register_data.password,
        role="provider",
        organization=register_data.organization
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    access_token = create_access_token(
        data={
            "sub": register_data.username,
            "role": "provider",
            "organization": register_data.organization,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "provider",
        "organization": register_data.organization,
    }

# Health check endpoints
@app.get("/")
async def root():
    return {"status": "ok", "message": "PeerCopilot Backend Running"}


@app.get("/health")
async def health():
    return {"status": "ok"}

def warmup_models():
    """Background task to load embeddings after server starts"""
    time.sleep(30)  # Wait for server to be fully ready
    try:
        print("[Warmup] Loading embeddings...")
        from app.rag_utils import get_model_and_indices
        get_model_and_indices()
        print("[Warmup] Embeddings loaded successfully")
    except Exception as e:
        print(f"[Warmup] Failed to load embeddings: {e}")

threading.Thread(target=warmup_models, daemon=True).start()

# Service user endpoints
class NewServiceUser(BaseModel):
    patientName: str
    lastSession: str
    nextCheckIn: str
    followUpMessage: str
    username: str

@app.get("/service_user_list/")
async def service_user_list(name: str):
    return get_all_service_users(name)

@app.get("/outreach_list/")
async def outreach_list(name: str):
    return get_all_outreach(name)

@app.post("/new_service_user/")
async def create_service_user(item: NewWellness):
    print(f"[API] Creating service user: {item.dict()}")
    success, message = add_new_service_user(
        item.username,
        item.patientName, 
        item.lastSession, 
        item.nextCheckIn, 
        item.location,
        item.followUpMessage
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message, "item": item}

# Socket.IO setup
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Utility functions
def process_raw_chunk(raw_chunk: str) -> str:
    """Remove 'data:' prefix and clean chunk."""
    if raw_chunk.startswith("data:"):
        return raw_chunk[len("data: "):].replace('\n', '')
    return raw_chunk.strip()

def accumulate_chunks(generator):
    """
    Accumulates and processes streaming text chunks from a generator.
    
    Yields progressively accumulated text with proper formatting.
    """
    accumulated = ""
    for raw_chunk in generator:
        token = process_raw_chunk(raw_chunk)
        
        if token == "[DONE]":
            continue
            
        if token.startswith('#'):
            accumulated += '\n' + token
        elif token.endswith('<br/>'):
            accumulated += token + '\n'
        elif token == '<br/><br/>':
            accumulated += '<br/>'
        else:
            accumulated += token
            
        yield accumulated

# Background streaming
def _background_stream(
    sid, 
    text, 
    previous_text, 
    model, 
    organization, 
    loop, 
    metadata, 
    service_user_id, 
    full_response, 
    external_resources, 
    raw_prompt
):
    """
    Runs construct_response in its own OS thread.
    Uses run_coroutine_threadsafe so .emit() coroutines are correctly awaited.
    """
    try:
        gen = construct_response(
            text, 
            previous_text, 
            model, 
            organization, 
            full_response, 
            external_resources, 
            raw_prompt
        )
        
        accumulated_text = ""
        for accumulated_text in accumulate_chunks(gen):
            asyncio.run_coroutine_threadsafe(
                sio.emit("generation_update", {"chunk": accumulated_text}, room=sid),
                loop
            )
            time.sleep(0.1)
        
        # Update conversation in database
        print(f"[DB] Updating conversation for user: {metadata.get('username')}, "
              f"service_user: {service_user_id}, "
              f"conversation: {metadata.get('conversation_id')}")
        
        update_conversation(
            metadata,
            [
                {'role': 'user', 'content': text},
                {'role': 'system', 'content': accumulated_text}
            ],
            service_user_id
        )

    except Exception as e:
        print(f"[BackgroundStream] Error: {e}")
        asyncio.run_coroutine_threadsafe(
            sio.emit(
                "generation_update",
                {"chunk": f"Sorry, something went wrong: {e}"},
                room=sid
            ),
            loop
        )

    finally:
        asyncio.run_coroutine_threadsafe(
            sio.emit(
                "generation_complete", 
                {"message": "Response generation complete."}, 
                room=sid
            ),
            loop
        )

# Socket.IO events
@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")
    await sio.emit("welcome", {"message": "Welcome from backend!"}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")

@sio.event
async def start_generation(sid, data):
    """Initiate text generation based on user input."""
    print(f"[Socket.IO] start_generation from {sid} at {time.time()}")

    # Extract request data
    text = data.get("text", "")
    previous_text = data.get("previous_text", [])
    model = data.get("model")
    organization = data.get("organization")
    conversation_id = data.get("conversation_id", "")
    username = data.get("username")
    service_user_id = data.get("service_user_id")
    
    # Generate conversation ID if needed
    if not conversation_id:
        conversation_id = secrets.token_hex(16)
        await sio.emit("conversation_id", {"conversation_id": conversation_id}, room=sid)
    
    metadata = {
        'conversation_id': conversation_id,
        'username': username
    }
    
    # Fetch goals and resources
    needs_goals = True  # Currently always true, can be made dynamic
    
    if needs_goals:
        loop = asyncio.get_running_loop()
        goals, resources, full_response, external_resources, raw_prompt = \
            await loop.run_in_executor(
                None,
                fetch_goals_and_resources,
                text,
                previous_text,
                organization
            )

        await sio.emit(
            "goals_update",
            {"goals": goals, "resources": resources},
            room=sid
        )
    else:
        full_response, external_resources, raw_prompt = "", "", ""
    
    print(f"Finished goals/resources at {time.time()}")

    # Start background streaming
    loop = asyncio.get_running_loop()
    threading.Thread(
        target=_background_stream,
        args=(
            sid, text, previous_text, model, organization, 
            loop, metadata, service_user_id, 
            full_response, external_resources, raw_prompt
        ),
        daemon=True
    ).start()

@sio.event
async def reset_session(sid, data):
    """Reset the chat session."""
    print(f"[Socket.IO] Reset session for {sid}")
    print(f"  Reason: {data.get('reason')}")
    print(f"  Previous user: {data.get('previous_service_user_id')}")
    print(f"  New user: {data.get('new_service_user_id')}")
    
    await sio.emit("reset_ack", {
        "message": "Session reset.",
        "previous_service_user_id": data.get('previous_service_user_id'),
        "new_service_user_id": data.get('new_service_user_id')
    }, room=sid)
