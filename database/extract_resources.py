import openai 
from utils import call_chatgpt_api
from secret import gao_key as key 
import pandas as pd
from transformers import DPRQuestionEncoder, DPRQuestionEncoderTokenizer, DPRContextEncoder, DPRContextEncoderTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
import time 
import os 
import numpy as np
from sentence_transformers import SentenceTransformer, util

openai.api_key = key

system_prompt = open("prompts/system_prompt.txt").read()

def create_basic_prompt(situation, resources_df):
    """Format a prompt based on a situation and a list of resources
    We input all the resources to the ChatGPT API, and see what it returns
    
    Arguments:
        situation: String, what the user requests
        resources_df: Pandas DataFrame, which contains information on each service
    
    Returns: String, the prompt to use"""

    services = ", ".join(resources_df["Service"].tolist())
    prompt = f"""
    I have a list of resources: {services}. Based on the situation "{situation}", which resources should I use? 
    Return a few appropriate resources, number, and why they are the appropriate choices for this situation. Make sure you provide more than one resource if they can help even just a little.
    """
    return prompt


def analyze_situation(situation, csv_file_path):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    resources_df = pd.read_csv(csv_file_path)
    prompt = create_basic_prompt(situation, resources_df)   
    response = call_chatgpt_api(system_prompt,prompt)
    return response

def analyze_situation_rag(situation, csv_file_path,k=10):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt using a RAG to whittle down the number of things
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    resources_df = pd.read_csv(csv_file_path)
    names = list(resources_df['service'])
    descriptions = list(resources_df['description'])
    urls = list(resources_df['url'])
    phones = list(resources_df['phone'])

    documents = ["{}: {}".format(names[i],descriptions[i]) for i in range(len(names))]

    # Initialize FAISS and create an index
    file_path = "results/saved_embedding.npy"

    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

    # Define the file path for storing embeddings
    if os.path.exists(file_path):
        embeddings = np.load(file_path)
    else:
        # Encode the documents using all-mpnet-base-v2
        embeddings = model.encode(documents, convert_to_tensor=False, show_progress_bar=True)
        embeddings = np.array(embeddings)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        np.save(file_path, embeddings)

    # Set up the FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance (cosine similarity can be used as well)
    index.add(embeddings)

    # Get relevant resources using the call_chatgpt_api function
    relevant_resources = call_chatgpt_api(
        "You are a highly knowledgeable and empathetic assistant designed to offer personalized suggestions for resources based on a user’s specific situation. Your goal is to thoughtfully analyze the given context and recommend 1-2 types of resources that would be most effective in addressing the user’s needs. Ensure your response is clear, concise, and directly relevant to the user’s circumstances. ",
        " Provide a brief description, 1-2 sentences, of each resource type, explaining how it could assist the user in resolving or improving their situation: {}".format(situation)
    )
    print("Relevant resources:", relevant_resources)

    # Encode the query using the Sentence Transformer model
    query_embedding = model.encode(relevant_resources, convert_to_tensor=False)

    # Search FAISS index to find the most relevant resources
    _, I = index.search(np.array([query_embedding]), k=k)  # Retrieve top k resources
    retrieved_resources = [f"{documents[i]}, URL: {urls[i]}, Phone: {phones[i]}" for i in I[0]]
    print("Retrieved resources:", len(retrieved_resources))

    # Prepare the retrieved text
    retrieved_text = "\n".join(retrieved_resources)
    system_prompt = "You are a helpful assistant recommending resources."
    prompt = (
        f"The user is experiencing: {situation}\nHere are some suggested resources:\n{retrieved_text}\n"
        "Please explain why these resources are appropriate for the user's situation. "
        "The only thing to put in bold (**) is the name of the place. Please also state the URL and the phone number for the place. "
        "If a resource is not relevant, do NOT include it. Please sort by the relevance of the resource. Finally, group resources by type (e.g. housing, transportation, mental health, etc.)."
    )

    # Get the response from the ChatGPT API
    response = call_chatgpt_api(system_prompt, prompt)
    return response

def translate_with_gpt(text, language):
    prompt = f"Translate the following text to {language}:\n\n{text}"
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"