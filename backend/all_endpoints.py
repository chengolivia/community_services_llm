from fastapi import FastAPI, File, UploadFile
import shutil 
from pydantic import BaseModel
from mental_health.generate_response import analyze_mental_health_situation
from resources.generate_response import analyze_resource_situation
from benefits.generate_response import analyze_benefits
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from benefits.secret import gao_key as key 
from benefits.utils import call_chatgpt_api_all_chats
from openai import OpenAI
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = '1'

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

@app.post("/benefit_response/")
async def benefit_response(item: Item):
  return StreamingResponse(analyze_benefits(item.text,item.previous_text,item.model), media_type='text/event-stream')

@app.post("/wellness_response/")
async def wellness_response(item: Item):
  return StreamingResponse(analyze_mental_health_situation(item.text,item.previous_text,item.model), media_type='text/event-stream')

@app.post("/resource_response/")
async def resource_response(item: Item):
  return StreamingResponse(analyze_resource_situation(item.text,item.previous_text,item.model), media_type='text/event-stream')


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

@app.post("/notes")
async def upload_notes(item: Item):
  all_messages = [{"role": "system", "content": "You are a helpful assistant than can summarize notes into a Markdown format"}]
  all_messages.append({"role": "user", "content": "I have the following notes: {}, can you summarize these into a pretty Markdown format? Return only the Markdown text, no need for anything else. The notes might be brief, but try to fill in the blanks, and write out a more comprehensive set of notes with details on who the client is, what the conversation is about, and the next set of goals. AVOID using tabs/nested lists, as they render strangely".format(item.text + "\n".join(['{}: {}'.format(i['role'],i['content']) for i in item.previous_text]))})

  # Get the response from the ChatGPT API
  response = call_chatgpt_api_all_chats(all_messages,stream=False)
  response = "\n".join(response.strip().split("\n")[1:-1])
  print("Response is {}".format(response))
  response = response.replace("-","1.")
  print("Message {}".format(response))

  return {"message": response}
