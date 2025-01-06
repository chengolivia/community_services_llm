import pandas as pd
import faiss
import os 
import numpy as np

def load_embeddings(file_path, documents, model):
    """Load or compute embeddings and save them."""
    if os.path.exists(file_path):
        return np.load(file_path)
    else:
        embeddings = model.encode(documents, convert_to_tensor=False, show_progress_bar=True)
        embeddings = np.array(embeddings)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        np.save(file_path, embeddings)
        return embeddings

def process_resources(csv_file_path):
    """Load and process resources data."""
    resources_df = pd.read_csv(csv_file_path)
    names = list(resources_df['service'])
    descriptions = list(resources_df['description'])
    urls = list(resources_df['url'])
    phones = list(resources_df['phone'])

    return ["{}: {}".format(names[i], descriptions[i]) for i in range(len(names))], names, descriptions, urls, phones

def process_guidance_resources(guidance_types):
    """Load guidance-specific resources and process them."""
    documents_by_guidance = {}
    for guidance in guidance_types:
        with open(f"mental_health/prompts/resources/{guidance}.txt") as file:
            resource_data = [line for line in file.read().split("\n") if len(line) > 10]
            documents_by_guidance[guidance] = [f"{line}: {resource_data[i]}" for i, line in enumerate(resource_data)]
    return documents_by_guidance

def create_faiss_index(embeddings):
    """Create and return FAISS index."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index
