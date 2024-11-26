from fastapi import FastAPI
from pydantic import BaseModel
from mental_health.generate_response import analyze_mental_health_situation
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React's dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data structure
class Item(BaseModel):
    text: str
    previous_text: list

@app.post("/benefit_response/")
async def create_item(item: Item):
    response = [
        {
          'category': 'Highly Eligible',
          'phone': '1-800-772-1213',
          'website': 'https://www.nj.gov/humanservices/dfd/programs/ssi/',
          'description':
            'Supplemental Security Income (SSI) for Single Adults',
          'reason': 'The user meets all the eligibility criteria for SSI as a single adult. They have an income less than $1,971 per month from work, and their resources are less than $2,000.',
        },
        {
          'category': 'Likely Eligible',
          'phone': '1-800-772-1213',
          'website': 'https://www.ssa.gov/',
          'description': 'Social Security Administration (SSA)',
          'reason': 'The user has been working for the past 12 years, which should give them 48 credits, assuming they’ve been earning at least $1,730 per year. This makes them eligible for the SSA, considering that a minimum of 40 credits is required. However, the actual earnings and credits need to be confirmed.',
        },
        {
          'category': 'Maybe Eligible',
          'phone': '1-732-243-0311',
          'website': 'https://njmedicare.com/',
          'description':
            'Benefits 3 & 4: Medicare Part A & B, and Social Security Disability Insurance (SSDI)',
          'reason': 'For Medicare, the user meets the age requirement for eligibility. However, further details regarding their health status may be required to determine SSDI eligibility.',
        },
      ]
    return response

@app.post("/wellness_response/")
async def create_item(item: Item):
    def event_generator():
        for token in analyze_mental_health_situation(item.text,item.previous_text):
            yield {'text': token}

    EventSourceResponse(event_generator())
