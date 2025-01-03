import openai 
from resources.utils import call_chatgpt_api_all_chats
from resources.secret import naveen_key as key 
import openai 
from resources.utils import *
from resources.secret import gao_key as key 
import pandas as pd
import faiss
import os 
import numpy as np
from sentence_transformers import SentenceTransformer


openai.api_key = key
csv_file_path = "resources/data/all_resources.csv"

system_prompt = open("resources/prompts/system_prompt.txt").read()

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


def analyze_resource_situation(situation, all_messages):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user']+[situation])
    print("Full situation {}".format(full_situation))

    response = analyze_situation_rag(full_situation,k=10)
    stream_response = call_chatgpt_api_all_chats([{'role': 'system', 'content': 'You are a helpful assistant who formats the list of resources provided in a nice Markdown format. Give the list of the most relevant resources along with explanations of why they are relevant. Try to make sure resources are relevant to the location'},
                                                  {'role': 'user','content': response}])


    for event in stream_response:
        if event.choices[0].delta.content != None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n","<br/>")
            yield "data: " + current_response + "\n\n"

def analyze_situation_rag(situation,k=3,stream=True):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt using a RAG to whittle down the number of things
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    # Encode the query using the Sentence Transformer model
    query_embedding = model.encode(situation, convert_to_tensor=False)

    # Search FAISS index to find the most relevant resources
    _, I = index.search(np.array([query_embedding]), k=k)  # Retrieve top k resources
    retrieved_resources = [f"{documents[i]}, URL: {urls[i]}, Phone: {phones[i]}, Description: {descriptions[i]}" for i in I[0]]

    # Prepare the retrieved text
    retrieved_text = "\n".join(retrieved_resources)
    
    return retrieved_text