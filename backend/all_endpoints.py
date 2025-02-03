import asyncio
import os
import re
import warnings

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mental_health.generate_response import analyze_mental_health_situation
from resources.generate_response import analyze_resource_situation
from benefits.generate_response import analyze_benefits

import socketio

# Global dictionary to store running generation tasks by session id.
generation_tasks = {}


# Set environment variables and suppress warnings.
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_DEBUG_CPU_TYPE"] = "5"
warnings.filterwarnings("ignore", message=".*torchvision.*", category=UserWarning)

# Create the FastAPI app.
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://feif-i7.isri.cmu.edu:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_keep_alive_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Connection"] = "keep-alive"
    return response

class Item(BaseModel):
    text: str
    previous_text: list
    model: str

# (Optional) Original HTTP endpoints.
@app.post("/benefit_response/")
async def benefit_response(item: Item):
    return StreamingResponse(
        analyze_benefits(item.text, item.previous_text, item.model),
        media_type='text/event-stream'
    )

@app.post("/wellness_response/")
async def wellness_response(item: Item):
    return StreamingResponse(
        analyze_mental_health_situation(item.text, item.previous_text, item.model),
        media_type='text/event-stream'
    )

@app.post("/resource_response/")
async def resource_response(item: Item):
    return StreamingResponse(
        analyze_resource_situation(item.text, item.previous_text, item.model),
        media_type='text/event-stream'
    )

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

def process_raw_chunk(raw_chunk: str) -> str:
    """
    Remove the "data:" prefix (if present) and trim whitespace.
    """
    if raw_chunk.startswith("data:"):
        return raw_chunk[len("data:"):].strip()
    return raw_chunk.strip()

def finalize_text(text: str) -> str:
    """
    Final cleanup of the accumulated text:
      1. Remove trailing "[DONE]" if present.
      2. Collapse multiple spaces.
      3. Ensure punctuation is followed by a space.
      4. Insert a space between a lowercase letter and an uppercase letter.
      5. Ensure Markdown headers have a space after the hashes.
      6. Apply manual replacements for known token issues.
    """
    # Remove trailing "[DONE]"
    text = re.sub(r'\s*\[DONE\]\s*$', '', text, flags=re.IGNORECASE).strip()
    # Collapse multiple spaces.
    text = re.sub(r'\s+', ' ', text)
    # Insert a space after punctuation if missing.
    text = re.sub(r'([,!.?])(?=\S)', r'\1 ', text)
    # Insert a space between a lowercase letter and an uppercase letter.
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Ensure Markdown headers have a space after the hashes.
    text = re.sub(r'^(#{1,6})(\S)', r'\1 \2', text, flags=re.MULTILINE)
    # Manual replacements for known issues.
    replacements = {
        "Me as urable": "Measurable",
        "Ach ievable": "Achievable",
        "Occup ational": "Occupational",
        "Real istic": "Realistic",
        "Tim ely": "Timely",
        "Em otional": "Emotional",
        "Int ellectual": "Intellectual",
        "Sp iritual":"Spiritual"
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    return text.strip()

def accumulate_chunks(generator):
    """
    Accumulates chunks from the generator into a single formatted string.
    
    For each new token produced by the generator:
      - Process the token using process_raw_chunk.
      - If the accumulated text is non-empty and its last character is alphanumeric
        and the new token starts with an alphanumeric character, insert a space before concatenating.
      - Otherwise, simply concatenate the token.
      - Collapse multiple spaces.
      - Yield the finalized accumulated text.
    """
    accumulated = ""
    for raw_chunk in generator:
        token = process_raw_chunk(raw_chunk)
        if not token:
            yield finalize_text(accumulated)
            continue
        if accumulated and accumulated[-1].isalnum() and token[0].isalnum():
            accumulated += " " + token
        else:
            accumulated += token
        accumulated = re.sub(r'\s+', ' ', accumulated)
        yield finalize_text(accumulated)

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")
    await sio.emit("welcome", {"message": "Welcome from backend!"}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")

async def run_generation(sid, generator):
    try:
        for accumulated_text in accumulate_chunks(generator):
            await sio.emit("generation_update", {"chunk": accumulated_text}, room=sid)
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print(f"[Socket.IO] Generation task for {sid} was cancelled.")
        await sio.emit("generation_update", {"chunk": "Generation cancelled."}, room=sid)
        raise
    except Exception as e:
        print(f"[Socket.IO] Error during generation: {e}")
        await sio.emit("generation_update", {"chunk": f"Error: {e}"}, room=sid)
    finally:
        if sid in generation_tasks:
            del generation_tasks[sid]
        await sio.emit("generation_complete", {"message": "Response generation complete."}, room=sid)


@sio.event
async def start_generation(sid, data):
    """
    Expected data format:
      {
        "text": "user input",
        "previous_text": [...],
        "model": "copilot" or "chatgpt",
        "tool": "benefit" or "wellness" or "resource"
      }
    """
    print(f"[Socket.IO] Received start_generation from {sid} with data: {data}")

    text = data.get("text", "")
    previous_text = data.get("previous_text", [])
    model = data.get("model")
    tool = data.get("tool")
    
    if tool == "benefit":
        generator = analyze_benefits(text, previous_text, model)
    elif tool == "wellness":
        generator = analyze_mental_health_situation(text, previous_text, model)
    elif tool == "resource":
        generator = analyze_resource_situation(text, previous_text, model)
    else:
        await sio.emit("generation_update", {"chunk": "Error: Unknown tool."}, room=sid)
        return
    
    if sid in generation_tasks:
        generation_tasks[sid].cancel()

    task = asyncio.create_task(run_generation(sid, generator))
    generation_tasks[sid] = task

    # try:
    #     for accumulated_text in accumulate_chunks(generator):
    #         await sio.emit("generation_update", {"chunk": accumulated_text}, room=sid)
    #         await asyncio.sleep(0.1)
    # except Exception as e:
    #     print(f"[Socket.IO] Error during generation: {e}")
    #     await sio.emit("generation_update", {"chunk": f"Error: {e}"}, room=sid)
    
    # await sio.emit("generation_complete", {"message": "Response generation complete."}, room=sid)

@sio.event
async def reset_session(sid):
    print(f"[Socket.IO] Reset session for client: {sid}")
    if sid in generation_tasks:
        generation_tasks[sid].cancel()
        del generation_tasks[sid]
    await sio.emit("reset_ack", {"message": "Session reset."}, room=sid)


