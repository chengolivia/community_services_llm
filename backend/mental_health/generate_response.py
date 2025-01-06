import openai 
from utils import call_chatgpt_api_all_chats
from mental_health.secret import naveen_key as key 
from resources.generate_response import analyze_situation_rag, analyze_situation_rag_guidance
import concurrent.futures
import re
import time 
import json

openai.api_key = key

system_prompt = open("mental_health/prompts/system_prompt.txt").read()
mental_health_system_prompt = open("mental_health/prompts/mental_health_prompt.txt").read()
question_prompt = open("mental_health/prompts/question_prompts.txt").read()
benefit_prompt = open("benefits/prompts/uncertain_prompt.txt").read()
summary_prompt = open("mental_health/prompts/summary_prompt.txt").read()
resource_prompt = open("mental_health/prompts/resource_prompt.txt").read()
which_resource_prompt = open("mental_health/prompts/which_resource.txt").read()

external_resources = {}
for i in ['human_resource','peer','crisis','trans']:
    external_resources[i] = open("mental_health/prompts/resources/{}.txt".format(i)).read()

def analyze_mental_health_situation(situation, all_messages,model):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    start = time.time() 

    if model == 'chatgpt':
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provider helpful responses to the client'}] + all_messages + [{'role': 'user', 'content': situation}]
        # Add a sleep time, so the time taken doesn't bias responses
        time.sleep(4)

        response = call_chatgpt_api_all_chats(all_message_list)

        for event in response:
            if event.choices[0].delta.content != None:
                current_response = event.choices[0].delta.content
                current_response = current_response.replace("\n","<br/>")
                yield "data: " + current_response + "\n\n"
        return 

    all_message_list = []

    all_message_list = [[{'role': 'system', 'content': mental_health_system_prompt}]+all_messages+[{"role": "user", "content": situation}]]
    all_message_list.append([{'role': 'system', 'content': question_prompt}]+all_messages+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': resource_prompt}]+all_messages+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': which_resource_prompt}]+[{'role': 'user', 'content': i['content'][:1000]} for i in all_messages if i['role'] == 'user']+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': benefit_prompt}]+all_messages+[{"role": "user", "content": situation}])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        responses = list(executor.map(lambda s: call_chatgpt_api_all_chats(s, stream=False), all_message_list))

    responses = list(responses)

    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    matches = re.findall(pattern,str(responses[2]),flags=re.DOTALL)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        resources = list(executor.map(lambda s: analyze_situation_rag(s), matches))

    resources = "\n\n\n".join(resources)

    response = "\n".join(["SMART Goals: {}\n\n\n".format(responses[0]),
                          "Questions: {}\n\n\n".format(responses[1]),
                          "Resources (use only these resources): {}".format(resources)])

    try:
        which_resources = json.loads(responses[3].strip()) 
    except:
        which_resources = {}

    new_message = [{'role': 'system', 'content': summary_prompt}]
 
    full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user' and len(i['content']) < 500] + [situation])

    rag_info = analyze_situation_rag_guidance(full_situation,which_resources)
    new_message += [{'role': 'system', 'content': rag_info}]

    new_message += all_messages+[{"role": "user", "content": situation}, {'role': 'user' , 'content': response}]
 
    response = call_chatgpt_api_all_chats(new_message,stream=True,max_tokens=400)
    
    for event in response:
        if event.choices[0].delta.content != None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n","<br/>")
            yield "data: " + current_response + "\n\n"
    
    print("Took {} time".format(time.time()-start))