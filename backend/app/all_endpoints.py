import asyncio
import os

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import json
import time 

from app.submodules import (
    get_questions_resources,
    construct_response,
    call_chatgpt_api_all_chats,
    fetch_goals_and_resources,
    internal_prompts,
)
from app.process_profiles import get_all_outreach, get_all_service_users
from app.login import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import update_conversation, add_new_service_user

import socketio
from datetime import timedelta
import secrets

generation_tasks = {}

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_DEBUG_CPU_TYPE"] = "5"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", # local development
         os.environ.get("FRONTEND_URL", ""),  # production frontend
        "https://peercopilot.com",  # Render URL (backup)
        "https://www.peercopilot.com",  # Render URL (backup)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Run the React frontend
@app.middleware("http")
async def add_keep_alive_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Connection"] = "keep-alive"
    return response

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    organization: str

# Add this endpoint to your FastAPI app
@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    print("Analyzing login_data {} {}".format(login_data.username,login_data.password))
    success, _, role, organization = authenticate_user(login_data.username, login_data.password)
    if not success:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.username, "role": role, "organization": organization},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role,
        organization=organization
    )
    
@app.get("/")
async def root():
    return {"status": "ok", "message": "PeerCopilot Backend Running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

class NewWellness(BaseModel):
    patientName: str
    lastSession: str
    nextCheckIn: str
    followUpMessage: str
    username: str
    location: str

@app.get("/service_user_list/")
async def service_user_list(name):
    return get_all_service_users(name)

@app.get("/outreach_list/")
async def outreach_list(name):
    return get_all_outreach(name)

@app.post("/new_service_user/")
async def create_item(item: NewWellness):
    print(f"[API] Received: {item.dict()}")
    success, message = add_new_service_user(
        item.username,
        item.patientName, 
        item.lastSession, 
        item.nextCheckIn, 
        item.location,
        item.followUpMessage
    )
    print(f"[API] Result: {success}, {message}")
    if success:
        return {"success": True, "message": message, "item": item}
    else:
        raise HTTPException(status_code=400, detail=message)


# app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")

# Handle Socket Messages

class Message(BaseModel):
    text: str
    previous_text: list
    model: str
    organization: str
    conversation_id: str
    username: str
    service_user_id: str | None = None 

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

def process_raw_chunk(raw_chunk: str) -> str:
    if raw_chunk.startswith("data:"):
        return raw_chunk[len("data: "):].replace('\n','')
    return raw_chunk.strip()

def accumulate_chunks(generator):
    """
    Accumulates and processes streaming text chunks from a generator.

    This function iterates over a generator of raw text chunks, processes each chunk,
    and appends it to an accumulated string with appropriate formatting. The function 
    yields the progressively accumulated text after each chunk is processed.

    Processing rules:
    - If the token is "[DONE]", it is ignored.
    - If the token starts with '#', a newline is prepended before adding it.
    - If the token ends with '<br/>', a newline is appended after it.
    - If the token is '<br/><br/>', it is replaced with a single '<br/>'.
    - Otherwise, the token is appended to the accumulated text.

    Parameters:
    generator (iterator): An iterator that yields raw text chunks.

    Yields:
    str: The progressively accumulated text after processing each chunk.
    """
    accumulated = ""
    for raw_chunk in generator:
        # print("before: {}".format(list(raw_chunk)))
        token = process_raw_chunk(raw_chunk)
        # print("after: {}".format(token))
        if token != "[DONE]":
            if token.startswith('#'):
                accumulated += '\n' + token
            elif token.endswith('<br/>'):
                accumulated += token + '\n' 
            elif token == '<br/><br/>':
                accumulated += '<br/>'
            else:
                accumulated += token
        yield accumulated

# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND STREAM HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _background_stream(sid, text, previous_text, model, organization, loop, metadata, service_user_id,full_response, external_resources, raw_prompt):
    """
    Runs construct_response in its own OS thread.
    Uses run_coroutine_threadsafe so .emit() coroutines are correctly awaited.
    """
    import time
    try:
        # 1) Build your response generator (this may block, but only this thread)
        gen = construct_response(text, previous_text, model, organization,full_response, external_resources, raw_prompt)
        # 2) Stream chunks
        for accumulated_text in accumulate_chunks(gen):
            # Schedule the async emit on the main asyncio loop
            asyncio.run_coroutine_threadsafe(
                sio.emit("generation_update", {"chunk": accumulated_text}, room=sid),
                loop
            )
            time.sleep(0.1)
        print(f"[DB Update] Updating conversation for username: {metadata.get('username')}, service_user_id: {service_user_id}, conversation_id: {metadata.get('conversation_id')}")
        update_conversation(
            metadata,
            [
                {'role': 'user', 'content': text},
                {'role': 'system', 'content': accumulated_text}
            ],
            service_user_id
        )

    except Exception as e:
        # Log server‐side...
        print(f"[BackgroundStream] Error during streaming: {e}")
        # And send a friendly error message into the chat pane
        asyncio.run_coroutine_threadsafe(
            sio.emit(
              "generation_update",
              {"chunk": f"Sorry, something went wrong: {e}"},
              room=sid
            ),
            loop
        )

    finally:
        # Always tell the client we’re done
        asyncio.run_coroutine_threadsafe(
            sio.emit("generation_complete", {"message": "Response generation complete."}, room=sid),
            loop
        )

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")
    await sio.emit("welcome", {"message": "Welcome from backend!"}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")

@sio.event
async def start_generation(sid, data):
    """
    Initiates a text generation process based on the provided user input and tool type.

    This function processes incoming data from a Socket.IO connection, determines the appropriate
    analysis function based on the specified tool type, and starts an asynchronous generation task.
    If a previous task exists for the given session ID (`sid`), it is canceled before starting a new one.

    Expected data format:
    {
        "text": str,          # User input text.
        "previous_text": list, # List of previous messages for context.
        "model": str,         # Model type ("copilot" or "chatgpt").
        "tool": str           # Tool type ("benefit", "wellness", or "resource").
    }

    Parameters:
    sid (str): The session ID associated with the request.
    data (dict): A dictionary containing the input text, previous conversation history,
                 selected model, and tool type.

    Behavior:
    - Calls the appropriate function (`analyze_benefits`, `analyze_mental_health_situation`, or
      `analyze_resource_situation`) based on the `tool` value.
    - Emits an error message if an invalid `tool` is provided.
    - Cancels any existing generation task associated with the session ID before starting a new one.
    - Creates an asynchronous task (`run_generation`) to process the generator and store it.
    """
    print(f"[Socket.IO] Received start_generation from {sid} at time {time.time()}")

    text = data.get("text", "")
    previous_text = data.get("previous_text", [])
    model = data.get("model")
    organization = data.get("organization")
    conversation_id = data.get("conversation_id","")
    username = data.get("username")
    service_user_id = data.get("service_user_id")
    
    if conversation_id == "":
        conversation_id = secrets.token_hex(16)
        await sio.emit("conversation_id", {"conversation_id": conversation_id}, room=sid)
    metadata = {
        'conversation_id': conversation_id,
        'username': username
    }
    
        # 1) Offload the small “intent check” to a thread so we don't block
    loop = asyncio.get_running_loop()
    intent_msgs = [
      {
        "role": "system",
        "content": (
          "You’re a request analyzer.  "
          "Given one user message, answer **strictly** in JSON with two keys:\n"
          '  • "needs_goals": true if they want advice or help or concrete next steps;\n'
          '  • "verbosity": one of "brief","medium","deep".\n'
          "Return only valid JSON, no extra commentary."
        )
      },
      {"role": "user", "content": text}
    ]
    try:
        meta_resp = await loop.run_in_executor(
          None,
          call_chatgpt_api_all_chats,
          intent_msgs,
          False,
          40
        )
        meta = json.loads(meta_resp.strip())
        needs_goals = bool(meta.get("needs_goals", False))
    except Exception as e:
        print(f"[Socket.IO] Error parsing needs_goals: {e}")
        needs_goals = False
    print("Finished Intent check, time={}".format(time.time()))

    # 2) If goals are needed, fetch & emit them
    #if the goals are not nneeded then emit them and remove them and delete them 
    #If the goals are not needed then emit them and discard them and delete them 
    if needs_goals:
        # Use shared helper so we only run the pipeline once
        loop = asyncio.get_running_loop()
        goals, resources, full_response, external_resources, raw_prompt = await loop.run_in_executor(
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
        full_response, external_resources, raw_prompt = "","",""
    print("Finished getting goals/resources, time={}".format(time.time()))

    # 3) Offload the rest of the chat‐stream to a background thread
    loop = asyncio.get_running_loop()
    threading.Thread(
        target=_background_stream,
        args=(sid, text, previous_text, model, organization, loop, metadata, service_user_id,full_response, external_resources, raw_prompt),
        daemon=True
    ).start()
    # if conversation_id == "":
    #     conversation_id = secrets.token_hex(16)
    #     await sio.emit("conversation_id", {"conversation_id": conversation_id}, room=sid)
    # username = data.get("username","")

    # generator = construct_response(text, previous_text, model,organization)
    
    # if sid in generation_tasks:
    #     generation_tasks[sid].cancel()

    # task = asyncio.create_task(run_generation(sid, generator,text,{'conversation_id': conversation_id, 'username': username}))
    # generation_tasks[sid] = task


@sio.event
async def reset_session(sid, data):
    print(f"[Socket.IO] Reset session for client: {sid}")
    print(f"[Socket.IO] Reset reason: {data.get('reason')}")
    print(f"[Socket.IO] Previous service user: {data.get('previous_service_user_id')}")
    print(f"[Socket.IO] New service user: {data.get('new_service_user_id')}")
    
    if sid in generation_tasks:
        generation_tasks[sid].cancel()
        del generation_tasks[sid]
    
    await sio.emit("reset_ack", {
        "message": "Session reset.",
        "previous_service_user_id": data.get('previous_service_user_id'),
        "new_service_user_id": data.get('new_service_user_id')
    }, room=sid)
# @app.get("/{full_path:path}")
# async def serve_react_app(full_path: str):
#     return FileResponse("../frontend/build/index.html")
