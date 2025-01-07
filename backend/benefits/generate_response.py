import openai 
from utils import call_chatgpt_api_all_chats, stream_process_chatgpt_response
from secret import gao_key as key 
import re
import time 
from benefits.eligibility_check import eligibility_check

openai.api_key = key
system_prompt = open("benefits/prompts/system_prompt.txt").read()
extract_prompt = open("benefits/prompts/uncertain_prompt.txt").read()

def get_situation_llm(user_input,all_messages):
    """Extract information from a user's input
    
    Arguments:
        user_input: Current user situation
        all_messages: All the previous messages
        
    Returns: Response, which is the extracted information"""

    new_messages = [{'role': 'system', 'content': extract_prompt}] + all_messages
    new_messages.append({'role': 'user', 'content': user_input})
    extracted_info = call_chatgpt_api_all_chats(new_messages,stream=False).strip()
    return extracted_info

def analyze_benefits_non_stream(situation, all_messages):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    extracted_info = get_situation_llm(situation,all_messages)

    eligibility_info = eligibility_check(extracted_info)

    prompt = (
        f"The center member is eligible for the following benefits {eligibility_info}"
        f"The last message is {situation}"
        "Can you respond with the following: "
        "1. If the center member is asking a question in the last message, please only answer the question; no need to state the benefit eligibilities"
        "2. If the center member is not asking a question, provide a nicely formatted version of the benefits, which states which things the center member MAY be eligible for, which things they're not, etc. and why not. Sort this from most likely eligible to least, and provide explanations as well. Also state what additional information might be helpful to determine eligibilities and why."
        "3. What additional information might be helpful to further help determine eligibilities"
        "4. Any next steps or links for applying for benefits. The SSI website is: https://www.ssa.gov/apply/ssi. The SSA website is: https://www.ssa.gov/apply. The medicare website is: https://www.ssa.gov/medicare/sign-up. You can apply for SSDI here: https://secure.ssa.gov/iClaim/dib. Can you state the type of documentation needed to apply as well"
        "Make sure you're conversational and as collegial as possible; note that all benefit programs should be addressed toward the center member, whom the provider is aiming to assist."
    )

    all_messages = [{'role': 'system', 'content': system_prompt}] + all_messages
    all_messages.append({'role': 'user', 'content': prompt})

    response = call_chatgpt_api_all_chats(all_messages,stream=False)
    all_messages = all_messages[1:-1]

    return response

def analyze_benefits(situation, all_messages,model):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    if model == 'chatgpt':
        print("Using ChatGPT")
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provide information on benefit eligibility'}] + all_messages + [{'role': 'user', 'content': situation}]
        time.sleep(4)

        response = call_chatgpt_api_all_chats(all_message_list)
        yield from stream_process_chatgpt_response(response)
        return 

    extracted_info = get_situation_llm(situation,all_messages)
    print("The extracted info is {}".format(extracted_info))

    pattern = r"\[Situation\](.*?)\[/Situation\]"
    eligibility_info = re.sub(
        pattern,
        lambda m: eligibility_check(m.group()),  # Pass the matched content as a string
        extracted_info,
        flags=re.DOTALL
    )

    constructed_messages = [{'role': 'system', 'content': system_prompt}] + all_messages
    constructed_messages.append({'role': 'user', 'content': situation})
    constructed_messages.append({'role': 'user', 'content': 'Eligible Benefits: {}'.format(eligibility_info)})

    response = call_chatgpt_api_all_chats(constructed_messages,stream=True,max_tokens=500)
    yield from stream_process_chatgpt_response(response)