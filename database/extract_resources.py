import openai 
from utils import call_chatgpt_api
from secret import naveen_key as key 
import pandas as pd
from transformers import DPRQuestionEncoder, DPRQuestionEncoderTokenizer, DPRContextEncoder, DPRContextEncoderTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
import time 
import os 
import numpy as np

openai.api_key = key

system_prompt = open("prompts/system_prompt.txt").read()

def create_basic_prompt(situation, hotlines_df):
    """Format a prompt based on a situation and a list of hotlines
    We input all the hotlines to the ChatGPT API, and see what it returns
    
    Arguments:
        situation: String, what the user requests
        hotlines_df: Pandas DataFrame, which contains information on each service
    
    Returns: String, the prompt to use"""

    services = ", ".join(hotlines_df["Service"].tolist())
    prompt = f"""
    I have a list of hotline services: {services}. Based on the situation "{situation}", which hotlines should I call? 
    Return a few appropriate hotline names, number, and why they are the appropriate choices for this situation. Make sure you provide more than one hotline if they can help even just a little.
    """
    return prompt

def analyze_situation(situation, csv_file_path):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    hotlines_df = pd.read_csv(csv_file_path)
    prompt = create_basic_prompt(situation, hotlines_df)   
    response = call_chatgpt_api(system_prompt,prompt)
    return response

def analyze_situation_rag(situation, csv_file_path,k=3):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt using a RAG to whittle down the number of things
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    hotlines_df = pd.read_csv(csv_file_path)
    names = list(hotlines_df['Service'])
    descriptions = list(hotlines_df['Description'])
    documents = ["{}: {}".format(names[i],descriptions[i]) for i in range(len(names))]

    start = time.time()
    # Initialize FAISS and create an index
    file_path = "results/saved_embedding.npy"

    if os.path.exists(file_path):
        embeddings = np.load(file_path)
    else:
        tokenizer = DPRContextEncoderTokenizer.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base')
        model = DPRContextEncoder.from_pretrained('facebook/dpr-ctx_encoder-single-nq-base')
        inputs = tokenizer(documents, return_tensors='pt', padding=True, truncation=True)
        embeddings = model(**inputs).pooler_output.detach().numpy()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        np.save(file_path, embeddings)

    index = faiss.IndexFlatL2(embeddings.shape[1])  # Index for fast search
    index.add(embeddings)
    question_tokenizer = DPRQuestionEncoderTokenizer.from_pretrained('facebook/dpr-question_encoder-single-nq-base')
    question_model = DPRQuestionEncoder.from_pretrained('facebook/dpr-question_encoder-single-nq-base')

    # Tokenize and encode the query
    query_inputs = question_tokenizer(situation, return_tensors='pt', padding=True, truncation=True)
    query_embedding = question_model(**query_inputs).pooler_output.detach().numpy()

    print("k is {}".format(k))

    # Search FAISS index to find the most relevant hotlines
    _, I = index.search(query_embedding, k=k)  # Retrieve top 3 hotlines
    retrieved_hotlines = [documents[i] for i in I[0]]
    print("Retrieved hotlines {}".format(len(retrieved_hotlines)))

    retrieved_text = "\n".join(retrieved_hotlines)
    system_prompt = "You are a helpful assistant recommending hotline services."
    prompt = f"The user is experiencing: {situation}\nHere are some suggested hotlines:\n{retrieved_text}\nPlease explain why these hotlines are appropriate for the user's situation. The only thing to put in bold (**) is the name of the place."

    response = call_chatgpt_api(system_prompt,prompt)
    return response