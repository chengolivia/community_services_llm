import openai 
from mental_health.utils import call_chatgpt_api_all_chats
from mental_health.secret import naveen_key as key 
from resources.generate_response import analyze_situation_rag
from benefits.generate_response import analyze_benefits_non_stream
import concurrent.futures
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

    total_length = sum([len(i['content']) for i in all_messages])
    print("Initial call to ChatGPT, with {} prompt".format(total_length))
    response = call_chatgpt_api_all_chats(all_messages,stream=False)
    all_messages.pop() 

    csv_file_path = "resources/data/all_resources.csv"
    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    # Replace the matched content with the transformed version
    print("Raw response {}".format(response))

    def parallel_sub(text,pattern,f):
        matches = re.findall(pattern,text,flags=re.DOTALL)
        with concurrent.futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(f, matches))
        for i in range(len(results)):
                text = text.replace(matches[i],results[i])
        return text

    response = parallel_sub(response,pattern,lambda m: analyze_situation_rag(m,csv_file_path,[],stream=False))
    response = response.replace("[Resource]","").replace("[/Resource]","")
    
    pattern = r"\[Benefit\](.*?)\[/Benefit\]"
    # Replace the matched content with the transformed version
    response = re.sub(pattern, lambda m: analyze_benefits_non_stream(m.group().replace("[Benefit]","").replace("[/Benefit]",""),[]), response,flags=re.DOTALL)

    
    response = response.replace("\n","<br/>")
    
    yield "data: " + response + "\n\n"