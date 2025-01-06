import openai 
import numpy as np
from sentence_transformers import SentenceTransformer
import time 

from utils import *
from resources.rag_utils import *
from resources.secret import naveen_key as key 

openai.api_key = key
csv_file_path = "resources/data/all_resources.csv"
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

# Main processing logic
documents, names, descriptions, urls, phones = process_resources(csv_file_path)
documents_by_guidance = process_guidance_resources(['human_resource', 'peer', 'crisis', 'trans'])

saved_models = {}
for guidance, doc_list in documents_by_guidance.items():
    embeddings_file_path = f"results/saved_embedding_{guidance}.npy"
    embeddings = load_embeddings(embeddings_file_path, doc_list, model)
    saved_models[guidance] = create_faiss_index(embeddings)

# Process main documents
file_path = "results/saved_embedding.npy"
embeddings = load_embeddings(file_path, documents, model)
main_index = create_faiss_index(embeddings)

def process_chatgpt_response(response):
    """Process ChatGPT response and yield content."""
    for event in response:
        if event.choices[0].delta.content is not None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n", "<br/>")
            yield "data: " + current_response + "\n\n"

def analyze_resource_situation(situation, all_messages,text_model):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    if text_model == 'chatgpt':
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provide resourecs to the client'}] + all_messages + [{'role': 'user', 'content': situation}]
        time.sleep(4)
        response = call_chatgpt_api_all_chats(all_message_list)
        yield from process_chatgpt_response(response)

    full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user']+[situation])

    response = analyze_situation_rag(full_situation,k=10)
    stream_response = call_chatgpt_api_all_chats([{'role': 'system', 'content': 'You are a helpful assistant who formats the list of resources provided in a nice Markdown format. Give the list of the most relevant resources along with explanations of why they are relevant. Try to make sure resources are relevant to the location'},
                                                  {'role': 'user','content': response}])
    yield from process_chatgpt_response(stream_response)

def analyze_situation_rag(situation,k=3):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt using a RAG to whittle down the number of things
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    query_embedding = model.encode(situation, convert_to_tensor=False)
    _, I = main_index.search(np.array([query_embedding]), k=k)  # Retrieve top k resources
    retrieved_resources = [f"{names[i]}, URL: {urls[i]}, Phone: {phones[i]}, Description: {descriptions[i]}" for i in I[0]]
    return "\n".join(retrieved_resources)

def analyze_situation_rag_guidance(situation,relevant_guidance,k=20):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt using a RAG to whittle down the number of things
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    # Encode the query using the Sentence Transformer model

    ret = []

    for i in relevant_guidance:
        if relevant_guidance[i]:
            query_embedding = model.encode(situation, convert_to_tensor=False)
            _, I = saved_models[i].search(np.array([query_embedding]), k=k)  # Retrieve top k resources
            ret += [documents_by_guidance[i][j].split(":")[1].strip() for j in I[0]]            
    return "\n".join(ret)