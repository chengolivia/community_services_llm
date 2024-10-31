import openai 
from utils import call_chatgpt_api
from secret import naveen_key as key 

openai.api_key = key

system_prompt = open("prompts/system_prompt.txt").read()

def create_basic_prompt(situation, pdf_text):
    """Format a prompt based on a situation and a list of hotlines
    We input all the hotlines to the ChatGPT API, and see what it returns
    
    Arguments:
        situation: String, what the user requests
        hotlines_df: Pandas DataFrame, which contains information on each service
    
    Returns: String, the prompt to use"""

    print("PDF Text length {}".format(len(pdf_text)))

    prompt = """
    I am trying to suggest activities that can help people with the 8 dimensions of wellness. 
    Create SMART goals (Specific, Measurable, Achievable, Realistic, and Timely) tailored to the client’s needs.
    Here is the situation that someone is dealing with: {}
    Can you suggest 2-3 activites, which can be along different dimensions of wellness, that align with their situations. 
    Think carefully; remember that suggestions from different types of wellness might be helpful, because wellness is holistic.
    Please state the dimensions of wellness
    """.format(situation)
    return prompt

def analyze_situation(situation, pdf_text):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    prompt = create_basic_prompt(situation, pdf_text)   
    response = call_chatgpt_api(system_prompt,prompt)
    return response