"""RAG utilities: embedding loading, FAISS index creation, and resource processing."""

import os
import numpy as np
import pandas as pd
import faiss
import psycopg
from sentence_transformers import SentenceTransformer
from pathlib import Path

from .utils import BASE_DIR

# Environment configuration
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

CONNECTION_STRING = os.getenv("RESOURCE_DB_URL")

# Lazy loading globals
_model = None
_saved_indices = None
_documents = None

def get_model_and_indices():
    """Lazy load embeddings model and indices."""
    global _model, _saved_indices, _documents
    if _model is None:
        _model, _saved_indices, _documents = get_all_embeddings(['cspnj', 'clhs'])
    return _model, _saved_indices, _documents

def load_embeddings(file_path: str, documents: list, model) -> np.ndarray:
    """
    Load or compute embeddings and save them.
    
    Args:
        file_path: Path to save/load embeddings
        documents: List of document strings
        model: SentenceTransformer model
    
    Returns:
        Numpy array of embeddings
    """
    if os.path.exists(file_path):
        return np.load(file_path)
    
    embeddings = model.encode(
        documents, 
        convert_to_tensor=False, 
        show_progress_bar=True
    )
    embeddings = np.array(embeddings)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    np.save(file_path, embeddings)
    
    return embeddings

def process_guidance_resources(guidance_types: list) -> dict:
    """
    Load guidance-specific resources and process them.
    
    Args:
        guidance_types: List of guidance type names
    
    Returns:
        Dictionary mapping guidance type to list of documents
    """
    documents_by_guidance = {}
    
    for guidance in guidance_types:
        file_path = BASE_DIR / f"prompts/external/{guidance}.txt"
        with open(file_path) as file:
            resource_data = [
                line for line in file.read().split("\n") 
                if len(line) > 10
            ]
            documents_by_guidance[guidance] = [
                f"{line}: {resource_data[i]}" 
                for i, line in enumerate(resource_data)
            ]
    
    return documents_by_guidance

def create_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Create and return FAISS index.
    
    Args:
        embeddings: Numpy array of embeddings
    
    Returns:
        FAISS index
    """
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def process_resources(resource_list: list) -> tuple:
    """
    Load and process resources from database.
    
    Args:
        resource_list: List of organization keys to query
    
    Returns:
        Tuple of (documents_dict, embeddings_dict)
    """
    documents_dict = {}
    embeddings_dict = {}
    
    with psycopg.connect(CONNECTION_STRING) as conn:
        for org_key in resource_list:
            # Fetch resources from database
            resources_df = pd.read_sql_query(
                """
                SELECT service, description, url, phone, embedding 
                FROM resources 
                WHERE organization = %s
                """, 
                conn, 
                params=[org_key]
            )
            
            # Parse embedding strings to arrays
            for i in range(len(resources_df)):
                embedding_str = resources_df.loc[i, 'embedding']
                resources_df.loc[i, 'embedding'] = (
                    embedding_str.strip("[").strip("]").split(",")
                )
            
            # Convert to numpy array
            embeddings = np.array(
                list(resources_df['embedding'])
            ).astype(float)
            
            # Format documents
            formatted_docs = [
                f"Resource: {row['service']}, "
                f"URL: {row['url']}, "
                f"Phone: {row['phone']}, "
                f"Description: {row['description']}"
                for _, row in resources_df.iterrows()
            ]
            
            documents_dict[org_key] = formatted_docs
            embeddings_dict[org_key] = embeddings
    
    return documents_dict, embeddings_dict

def get_all_embeddings(resource_list: list) -> tuple:
    """
    Get all embeddings for RAG system.
    
    Args:
        resource_list: List of organization identifiers
    
    Returns:
        Tuple of (model, indices_dict, documents_dict)
    """
    # Initialize model
    model = SentenceTransformer(
        'sentence-transformers/all-mpnet-base-v2', 
        token=os.getenv('HF_TOKEN')
    )
    
    # Process guidance resources
    guidance_types = ['human_resource', 'peer', 'crisis', 'trans']
    documents = process_guidance_resources(guidance_types)
    
    saved_indices = {}
    
    # Create indices for guidance resources
    for guidance, doc_list in documents.items():
        embeddings_file = f"saved_embeddings/saved_embedding_{guidance}.npy"
        embeddings = load_embeddings(embeddings_file, doc_list, model)
        saved_indices[guidance] = create_faiss_index(embeddings)
    
    # Process organization resources
    org_resources, resource_embeddings = process_resources(resource_list)
    
    for org_key in org_resources:
        doc_key = f'resource_{org_key}'
        documents[doc_key] = org_resources[org_key]
        saved_indices[doc_key] = create_faiss_index(resource_embeddings[org_key])
    
    # Debug logging
    example_docs = [
        doc for doc in documents.get('resource_cspnj', [])
        if 'Vineland' in doc and 'Salvation' in doc
    ]
    if example_docs:
        print(f"[Debug] Found {len(example_docs)} Vineland Salvation resources")
    
    return model, saved_indices, documents