from fastapi import FastAPI
from pydantic import BaseModel
from mental_health.generate_response import analyze_mental_health_situation
from resources.generate_response import analyze_resource_situation
from benefits.generate_response import analyze_benefits
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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

@app.post("/benefit_response/")
async def benefit_response(item: Item):
  return StreamingResponse(analyze_benefits(item.text,item.previous_text), media_type='text/event-stream')

@app.post("/wellness_response/")
async def wellness_response(item: Item):
  return StreamingResponse(analyze_mental_health_situation(item.text,item.previous_text), media_type='text/event-stream')

@app.post("/resource_response/")
async def resource_response(item: Item):
  return StreamingResponse(analyze_resource_situation(item.text,item.previous_text), media_type='text/event-stream')