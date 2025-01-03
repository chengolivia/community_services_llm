import openai 
from mental_health.utils import call_chatgpt_api_all_chats
from mental_health.secret import naveen_key as key 
from resources.generate_response import analyze_situation_rag
from benefits.generate_response import analyze_benefits_non_stream
import concurrent.futures
import re
import time 
import asyncio 

openai.api_key = key

system_prompt = open("mental_health/prompts/system_prompt.txt").read()
mental_health_system_prompt = open("mental_health/prompts/mental_health_prompt.txt").read()
question_prompt = open("mental_health/prompts/question_prompts.txt").read()
summary_prompt = open("mental_health/prompts/summary_prompt.txt").read()
resource_prompt = open("mental_health/prompts/resource_prompt.txt").read()

def analyze_mental_health_situation(situation, all_messages):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    start = time.time() 

    all_message_list = []


    all_message_list = [[{'role': 'system', 'content': mental_health_system_prompt}]+all_messages+[{"role": "user", "content": situation}]]
    all_message_list.append([{'role': 'system', 'content': question_prompt}]+all_messages+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': resource_prompt}]+all_messages+[{"role": "user", "content": situation}])
    print("Code before GPT took {}".format(time.time()-start))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        responses = list(executor.map(lambda s: call_chatgpt_api_all_chats(s, stream=False), all_message_list))

    responses = list(responses)
    print("First GPT call took {}".format(time.time()-start))

    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    matches = re.findall(pattern,str(responses[2]),flags=re.DOTALL)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        resources = list(executor.map(lambda s: analyze_situation_rag(s,stream=False), matches))

    resources = "\n\n\n".join(resources)


    print("Second GPT call took {}".format(time.time()-start))

    response = "\n".join(["SMART Goals: {}\n\n\n".format(responses[0]),
                          "Questions: {}\n\n\n".format(responses[1]),
                          "Resources (use only these resources): {}".format(resources)])
    
    new_message = [{'role': 'system', 'content': summary_prompt}]+all_messages+[{"role": "user", "content": situation}, {'role': 'user' , 'content': response}]
    response = call_chatgpt_api_all_chats(new_message,stream=True,max_tokens=400)
    
    for event in response:
        if event.choices[0].delta.content != None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n","<br/>")
            yield "data: " + current_response + "\n\n"
    
    print("Took {} time".format(time.time()-start))