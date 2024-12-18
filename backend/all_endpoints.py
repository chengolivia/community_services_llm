from fastapi import FastAPI, File, UploadFile
import shutil 
from pydantic import BaseModel
from mental_health.generate_response import analyze_mental_health_situation
from resources.generate_response import analyze_resource_situation
from benefits.generate_response import analyze_benefits
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from benefits.secret import gao_key as key 
from openai import OpenAI
import os

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

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    print("Uploading file!")
    try:
        file_path = f"uploads/{file.filename}"
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        audio_file= open(file_path, "rb")
        client = OpenAI(api_key=key)
        transcription = client.audio.transcriptions.create(
          model="whisper-1", 
          file=audio_file
        )
        os.remove(file_path)
        print("Result {}".format(transcription.text))
        
        return {"message": transcription.text, "file_path": file_path}
    except Exception as e:
        print("Error {}".format(e))
        return {"error": str(e)}