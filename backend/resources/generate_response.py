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

    print("All situation {}".format(situation))

    response = analyze_situation_rag(situation, csv_file_path, all_messages[-2:])
    for event in response:
        if event.choices[0].delta.content != None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n","<br/>")
            yield "data: " + current_response + "\n\n"

def analyze_situation_rag(situation,k=5,stream=True):
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

    # system_prompt = "You are a highly knowledgeable and empathetic assistant designed to offer personalized suggestions for resources based on a center member's specific situation. Your goal is to thoughtfully analyze the given context and recommend relevant resources that would be most effective in addressing the center member's needs. Ensure your response is clear, concise, and directly relevant to the center member's circumstances. Prioritize resources that are nearer the individual's location."
    
    # prompt = f"The center member wants resources for: {situation}"
    
    # all_resources = (f"Here are some suggested resources:\n{retrieved_text}\n"
    #     "Please explain why these resources are appropriate for the center member's situation; note that all of these recommendations, etc. are for the center member. "
    #     "The only thing to put in bold (**) is the name of the place. Please also state the URL, and the phone number for the place, the responsible region of the service (name of the city or county, not the street address, and if the service does not specify the responsible location, just leave the answer blank), eligibility requirements, description of the service, and an explanation why this was selected"
    #     "If a resource is not relevant, do NOT include it. For example, it's not always needed to include food or housing resources; sometimes the center member just wants one particular thing. Also do NOT include resources that are far away (e.g. more than 50 miles away, or those that might not be available in their region/state). Please sort by the relevance and the ease of accessing the resource (e.g. one with the least stringent conditions comes first). Finally, group resources by type (e.g. housing, transportation, mental health, etc.) and sort these types so housing comes first, then food, then mental health, etc. If the center member has a question, then answer that question as well, and use all the messages so far to answer the center member's question. If a center member only asks a question, no need to provide resources."
    # )

    # all_messages = [{"role": "system", "content": system_prompt}] + all_messages
    # all_messages.append({"role": "user", "content": prompt})
    # all_messages.append({"role": "system", "content": all_resources})

    # # Get the response from the ChatGPT API
    # response = call_chatgpt_api_all_chats(all_messages,stream=stream)
    # all_messages = all_messages[1:-1]
    # print("Finished analysis")
    # return response
