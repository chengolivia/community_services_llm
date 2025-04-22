import openai 
import concurrent.futures
import re
import json 
import os 
import numpy as np

from app.eligibility_check import eligibility_check
from app.rag_utils import get_all_embeddings
from app.utils import call_chatgpt_api_all_chats, stream_process_chatgpt_response, get_all_prompts

openai.api_key = os.environ.get("SECRET_KEY")

internal_prompts, external_prompts = get_all_prompts()
model, saved_indices, documents = get_all_embeddings({'cspnj': 'data/cspnj_2025.csv'})

def construct_response(situation, all_messages,model,organization):
    """Process user situation + generate SMART goals, etc.

    Arguments:
        situation: String, last message user sent
        all_messages: List of dictionaries, with all the messages
        model: String, either chatgpt or copilot 
        
    Returns: Streaming response in text"""

    if model == 'chatgpt':
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provider helpful responses to the client'}] + all_messages + [{'role': 'user', 'content': situation}]
        response = call_chatgpt_api_all_chats(all_message_list,max_tokens=750)
        yield from stream_process_chatgpt_response(response)
        return 

    # Initially extract information via prompting + trusted resources
    initial_response, external_resources = get_questions_resources(situation,all_messages,organization)

    # Combine these extracted information via the orchestration prompt/module
    new_message = [{'role': 'system', 'content': internal_prompts['orchestration']}]
    new_message += [{'role': 'system', 'content': external_resources}]
    new_message += all_messages+[{"role": "user", "content": situation}, {'role': 'user' , 'content': initial_response}]
    response = call_chatgpt_api_all_chats(new_message,stream=True,max_tokens=1000)
    yield from stream_process_chatgpt_response(response)

def get_questions_resources(situation,all_messages,organization):
    """Process user situation + generate questions and resources

    Arguments:
        situation: String, last message user sent
        all_messages: List of dictionaries, with all the messages

    Returns: String response, with resources and questions, 
        and a string, containing a dictionary on which 
        external resources to load """
    
    all_message_list = []
    for prompt in ['goal','followup_question','resource','which_resource','benefit_extract']:
        all_message_list.append([{'role': 'system', 'content': internal_prompts[prompt].replace("[Organization]",organization)}]+all_messages+[{"role": "user", "content": situation}])
    with concurrent.futures.ThreadPoolExecutor() as executor:
        initial_responses = list(executor.map(lambda s: call_chatgpt_api_all_chats(s, stream=False), all_message_list))
    initial_responses = list(initial_responses)

    # Combine prompts with external information on resources
    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    matches = re.findall(pattern,str(initial_responses[2]),flags=re.DOTALL)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resources = list(executor.map(lambda s: extract_resources(s,{'resource_{}'.format(organization): True},k=5), matches))
    
    # Combine prompts with external information on benefits
    pattern = r"\[Situation\](.*?)\[/Situation\]"
    benefit_info = re.sub(
        pattern,
        lambda m: eligibility_check(m.group()),  # Pass the matched content as a string
        initial_responses[4],
        flags=re.DOTALL
    )
    if "Irrelevant" in benefit_info:
        benefit_info = ""
    else:
        constructed_messages = [{'role': 'system', 'content': internal_prompts['benefit_system']}] + [{'role': 'user', 'content': i['content'][:1000]} for i in all_messages if i['role'] == 'user']
        constructed_messages.append({'role': 'user', 'content': situation})
        constructed_messages.append({'role': 'user', 'content': 'Eligible Benefits: {}'.format(benefit_info)})
        benefit_info = call_chatgpt_api_all_chats(constructed_messages,stream=False)

    # Call modules with additional extra information
    which_external_resources = initial_responses[3]
    try:
        which_external_resources = json.loads(which_external_resources.strip()) 
    except:
        which_external_resources = {}
    full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user' and len(i['content']) < 500] + [situation])
    external_resources = extract_resources(full_situation,which_external_resources)


    response = "\n".join(["SMART Goals: {}\n\n\n".format(initial_responses[0]),
                          "Questions: {}\n\n\n".format(initial_responses[1]),
                          "Resources (use only these resources): {}".format("\n\n\n".join(resources)), 
                          "Benefit Info: {}".format(benefit_info)])
    return response, external_resources

def extract_resources(situation,which_indices,k=25):
    """Given a string, and a list of external resources to use
        find the most similar lines in the external resources
    
    Arguments:
        situation: String, what the user requests
        indices: Dictionary, mapping which 
            documents to use (guidances, e.g. crisis)
        
    Returns: A string, list of relevant lines"""
    ret = []

    for i in which_indices:
        if which_indices[i]:
            query_embedding = model.encode(situation, convert_to_tensor=False)
            _, I = saved_indices[i].search(np.array([query_embedding]), k=k)  # Retrieve top k resources
            ret += [":".join(documents[i][j].split(":")[1:]).strip() for j in I[0]]            
    return "\n".join(ret)

def get_benefit_demographics(user_input,all_messages):
    """Extract information from a user's input
    
    Arguments:
        user_input: Current user situation
        all_messages: All the previous messages
        
    Returns: Response, which is the extracted information"""

    new_messages = [{'role': 'system', 'content': internal_prompts['benefit_extract']}] + all_messages
    new_messages.append({'role': 'user', 'content': user_input})
    extracted_info = call_chatgpt_api_all_chats(new_messages,stream=False).strip()
    return extracted_info

def get_benefit_eligibility(situation,all_messages):
    """Given a situation and all the messages, get info on their benefits
    
    Arguments:
        situation: String, the user's current situation
        all_messages: List of previous messages
    
    Returns: String, info on their current benefit eligibilities"""
    
    extracted_info = get_benefit_demographics(situation,all_messages)

    pattern = r"\[Situation\](.*?)\[/Situation\]"
    eligibility_info = re.sub(
        pattern,
        lambda m: eligibility_check(m.group()),  # Pass the matched content as a string
        extracted_info,
        flags=re.DOTALL
    )
 
    return eligibility_info