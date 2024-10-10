import openai
import pandas as pd
import sqlite3

openai.api_key = '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'

def load_hotlines(file_path):
    hotlines_df = pd.read_csv(file_path)
    conn = sqlite3.connect(':memory:')  # Creates an in-memory SQLite database
    hotlines_sql = hotlines_df.to_sql('main', conn, index=False, if_exists='replace')

    return conn

def get_sql(situation):
    prompt = f"""
    I have a list of hotline services, with the following fields Service,Phone_Number,Description,County,Category. 
    It's in a table titled 'main', with Category having the following choices: "Mental Health", "Addiction", "Veteran Support","General".
    Also, a particular service can be more than one category (e.g. it could be Mental Health, Addiction)
    Based on the situation "{situation}", return me an SQL query (and ONLY the SQL query) that retrieves the resources that I should call. 
    It's if the query is not very precise; here, recall matters more.  
    """
    return prompt

def refine_further(hotlines_df,situation):
    services = ", ".join(hotlines_df["Service"].tolist())
    prompt = f"""
    I have a list of hotline services: {services}. Based on the situation "{situation}", which hotline should I call? 
    Return the hotline name, number, and why it is the most appropriate choice for this situation. 
    If something is life-threatening, or an emergency, also suggest 911 (if it isn't already suggested)
    """
    return prompt

system_prompt = "You are a highly knowledgeable, patient, and helpful assistant that specializes in collecting user information and evaluating eligibility \
                for various social and financial benefits. Your goal is to guide the user through the process, ensuring they provide clear and accurate answers. \
                Be polite and professional in your responses. If a user’s input is unclear or incomplete, ask follow-up questions to gather the necessary details. \
                Always provide additional explanations or examples if the user appears confused. If a question involves complex terms, offer simple definitions to ensure the user understands"


system_prompt = "You are a highly knowledgeable, patient, and helpful assistant that specializes in collecting user information and evaluating eligibility \
                for various social and financial benefits. Your goal is to guide the user through the process, ensuring they provide clear and accurate answers. \
                Be polite and professional in your responses. If a user’s input is unclear or incomplete, ask follow-up questions to gather the necessary details. \
                Always provide additional explanations or examples if the user appears confused. If a question involves complex terms, offer simple definitions to ensure the user understands"



def call_chatgpt_api(prompt):
    messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    response =openai.chat.completions.create(model="gpt-4o-mini",
        messages=messages,max_tokens=300)
    return response.choices[0].message.content.strip()

def analyze_situation(situation, csv_file_path):
    conn = load_hotlines(csv_file_path)
    sql_prompt = get_sql(situation)   
    sql_statement = call_chatgpt_api(sql_prompt)
    sql_statement = sql_statement.replace("```sql",'').replace('```','').strip()
    retrieved_rows =  pd.read_sql_query(sql_statement, conn)
    refinement_prompt = refine_further(retrieved_rows,situation)
    final_answer = call_chatgpt_api(refinement_prompt)

    return final_answer

situation = "I'm in urgent need of help as I'm experiencing a mental health crisis and struggling with thoughts of self-harm."
csv_file_path = "hotlines.csv"
result = analyze_situation(situation, csv_file_path)
print("Response from ChatGPT:")
print(result)
