import openai 
from utils import call_chatgpt_api
from secret import naveen_key as key 
import pandas as pd
import numpy as np

openai.api_key = key

def extract_information(conversation):
    """Given a conversation as a string, extract the information into a dictionary
    
    Arguments:
        conversation: string
        
    Returns: Dictionary, with each key-value pair representing one piece of information"""

    system_prompt = open("prompts/system_prompt.txt").read()
    prompt = open("prompts/information_prompt.txt").read().format(conversation)
    
    lines = call_chatgpt_api(system_prompt,prompt).strip().split("\n")
    
    extracted_info = {}
    for line in lines:
        if ": " in line:
            key, value = line.split(": ")
            extracted_info[key.strip().lower().replace(" ", "_")] = value.strip().replace("$","").replace(",","")
    print(extracted_info)
    return extracted_info


def call_llm_extract(user_input):
    """Extract information from a user's input
    
    Arguments:
        user_input: What the user enters
        pdf_text: Information from the PDF, as text
        
    Returns: Response, which is the extracted information"""
    system_prompt = open("prompts/system_prompt_extract.txt").read()
    prompt = open("prompts/uncertain_prompt.txt").read().format(user_input)
    extracted_info = call_chatgpt_api(system_prompt,prompt).strip()
    return extracted_info

def call_llm_update(original_info, update_request, pdf_text):
    """Update information from a user's input
    
    Arguments:
        user_input: What the original info the user entered is, as text
        update_request: What the user wants updated, text
        pdf_text: Information from the PDF, as text
        
    Returns: Response, which is the updated information"""
    
    update_sys_prompt = open("prompts/update_system_prompt.txt").read()
    prompt = open("prompts/update_prompt.txt").read().format(pdf_text,original_info,update_request)
    updated_info = call_chatgpt_api(update_sys_prompt,prompt).strip()
    return updated_info
