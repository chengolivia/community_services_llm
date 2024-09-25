import openai
import pandas as pd

openai.api_key = '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'

def load_hotlines(file_path):
    hotlines_df = pd.read_csv(file_path)
    return hotlines_df

def create_prompt(situation, hotlines_df):
    services = ", ".join(hotlines_df["Service"].tolist())
    prompt = f"""
    I have a list of hotline services: {services}. Based on the situation "{situation}", which hotline should I call? 
    Return the hotline name, number, and why it is the most appropriate choice for this situation.
    """
    return prompt

system_prompt = "You are a highly knowledgeable, patient, and helpful assistant that specializes in collecting user information and evaluating eligibility \
                for various social and financial benefits. Your goal is to guide the user through the process, ensuring they provide clear and accurate answers. \
                Be polite and professional in your responses. If a user’s input is unclear or incomplete, ask follow-up questions to gather the necessary details. \
                Always provide additional explanations or examples if the user appears confused. If a question involves complex terms, offer simple definitions to ensure the user understands"

def call_chatgpt_api(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return response['choices'][0]['message']['content'].strip()

def analyze_situation(situation, csv_file_path):
    hotlines_df = load_hotlines(csv_file_path)
    prompt = create_prompt(situation, hotlines_df)   
    response = call_chatgpt_api(prompt)
    return response

situation = "I'm in urgent need of help as I'm experiencing a mental health crisis and struggling with thoughts of self-harm."
csv_file_path = "hotlines.csv"
result = analyze_situation(situation, csv_file_path)
print("Response from ChatGPT:")
print(result)
