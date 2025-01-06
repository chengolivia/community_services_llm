import openai 
from utils import call_chatgpt_api_all_chats, stream_process_chatgpt_response
from secret import naveen_key as key 
from resources.generate_response import analyze_situation_rag, analyze_situation_rag_guidance
import concurrent.futures
import re
import time 
import json

openai.api_key = key

mental_health_system_prompt = open("mental_health/prompts/mental_health_prompt.txt").read()
question_prompt = open("mental_health/prompts/question_prompts.txt").read()
benefit_prompt = open("benefits/prompts/uncertain_prompt.txt").read()
summary_prompt = open("mental_health/prompts/summary_prompt.txt").read()
resource_prompt = open("mental_health/prompts/resource_prompt.txt").read()
which_resource_prompt = open("mental_health/prompts/which_resource.txt").read()

external_resources = {}
for i in ['human_resource','peer','crisis','trans']:
    external_resources[i] = open("mental_health/prompts/resources/{}.txt".format(i)).read()

def get_questions_resources(situation,all_messages):
    """Process user situation + generate questions and resources

    Arguments:
        situation: String, last message user sent
        all_messages: List of dictionaries, with all the messages

    Returns: String response, with resources and questions, 
        and a string, containing a dictionary on which 
        external resources to load """

    start = time.time()
    all_message_list = [[{'role': 'system', 'content': mental_health_system_prompt}]+all_messages+[{"role": "user", "content": situation}]]
    all_message_list.append([{'role': 'system', 'content': question_prompt}]+all_messages+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': resource_prompt}]+all_messages+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': which_resource_prompt}]+[{'role': 'user', 'content': i['content'][:1000]} for i in all_messages if i['role'] == 'user']+[{"role": "user", "content": situation}])
    all_message_list.append([{'role': 'system', 'content': benefit_prompt}]+all_messages+[{"role": "user", "content": situation}])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        initial_responses = list(executor.map(lambda s: call_chatgpt_api_all_chats(s, stream=False), all_message_list))

    initial_responses = list(initial_responses)
    print("Line 35 {}".format(time.time()-start))
    start = time.time()

    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    matches = re.findall(pattern,str(initial_responses[2]),flags=re.DOTALL)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        resources = list(executor.map(lambda s: analyze_situation_rag(s), matches))

    resources = "\n\n\n".join(resources)

    response = "\n".join(["SMART Goals: {}\n\n\n".format(initial_responses[0]),
                          "Questions: {}\n\n\n".format(initial_responses[1]),
                          "Resources (use only these resources): {}".format(resources)])
    which_external_resources = initial_responses[4]
    print("Line 50 {}".format(time.time()-start))
    start = time.time()

    return response, which_external_resources

def analyze_mental_health_situation(situation, all_messages,model):
    """Process user situation + generate SMART goals, etc.

    Arguments:
        situation: String, last message user sent
        all_messages: List of dictionaries, with all the messages
        model: String, either chatgpt or copilot 
        
    Returns: Streaming response in text"""
    
    if model == 'chatgpt':
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provider helpful responses to the client'}] + all_messages + [{'role': 'user', 'content': situation}]
        time.sleep(4)
        response = call_chatgpt_api_all_chats(all_message_list)
        yield from stream_process_chatgpt_response(response)
        return 

    start = time.time() 
    response, which_external_resources = get_questions_resources(situation,all_messages)
    print("Line 69 {}".format(time.time()-start))
    start = time.time()

    try:
        which_external_resources = json.loads(which_external_resources.strip()) 
    except:
        which_external_resources = {}


    full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user' and len(i['content']) < 500] + [situation])
    rag_info = analyze_situation_rag_guidance(full_situation,which_external_resources)

    print("Line 81 {}".format(time.time()-start))
    start = time.time()

    new_message = [{'role': 'system', 'content': summary_prompt}]
    new_message += [{'role': 'system', 'content': rag_info}]
    new_message += all_messages+[{"role": "user", "content": situation}, {'role': 'user' , 'content': response}]
 
    response = call_chatgpt_api_all_chats(new_message,stream=True,max_tokens=400)
    print("Line 89 {}".format(time.time()-start))
    start = time.time()
    
    yield from stream_process_chatgpt_response(response)
