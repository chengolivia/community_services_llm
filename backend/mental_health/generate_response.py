import openai 
from mental_health.utils import call_chatgpt_api_all_chats
from mental_health.secret import naveen_key as key 
from resources.generate_response import analyze_situation_rag
from benefits.generate_response import analyze_benefits_non_stream
import re

openai.api_key = key

system_prompt = open("mental_health/prompts/system_prompt.txt").read()

def create_basic_prompt(situation):
    """Format a prompt based on a situation and a list of hotlines
    We input all the hotlines to the ChatGPT API, and see what it returns
    
    Arguments:
        situation: String, what the user requests
        hotlines_df: Pandas DataFrame, which contains information on each service
    
    Returns: String, the prompt to use"""

    prompt = open("mental_health/prompts/mental_health_prompt.txt").read().format(situation)
    return prompt

def analyze_mental_health_situation(situation, all_messages):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    prompt = create_basic_prompt(situation)   
    all_messages.append({"role": "user", "content": prompt})
    response = call_chatgpt_api_all_chats(all_messages,stream=False)
    all_messages.pop() 

    csv_file_path = "resources/data/all_resources.csv"
    pattern = r"\[Resource\](.*?)\[/Resource\]"
    # Replace the matched content with the transformed version
    response = re.sub(pattern, lambda m: analyze_situation_rag(m, csv_file_path,[],stream=False), response)
    
    pattern = r"\[Benefit\](.*?)\[/Benefit\]"
    # Replace the matched content with the transformed version
    response = re.sub(pattern, lambda m: analyze_benefits_non_stream(m,[]), response)

    
    response = response.replace("\n","<br/>")
    
    yield "data: " + response + "\n\n"