from pydantic import BaseModel
from fastapi import FastAPI, Request
from mental_health.generate_response import analyze_mental_health_situation
from resources.generate_response import analyze_resource_situation
from benefits.generate_response import analyze_benefits
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import warnings



os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = '1'
os.environ['MKL_DEBUG_CPU_TYPE'] = '5'
warnings.filterwarnings("ignore", message=".*torchvision.*", category=UserWarning)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://feif-i7.isri.cmu.edu:3000"],  # React's dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data structure
class Item(BaseModel):
    text: str
    previous_text: list
    model: str

@app.middleware("http")
async def add_keep_alive_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Connection"] = "keep-alive"
    return response


@app.post("/benefit_response/")
async def benefit_response(item: Item):
  return StreamingResponse(analyze_benefits(item.text,item.previous_text,item.model), media_type='text/event-stream')

@app.post("/wellness_response/")
async def wellness_response(item: Item):
  return StreamingResponse(analyze_mental_health_situation(item.text,item.previous_text,item.model), media_type='text/event-stream')

@app.post("/resource_response/")
async def resource_response(item: Item):
  return StreamingResponse(analyze_resource_situation(item.text,item.previous_text,item.model), media_type='text/event-stream')