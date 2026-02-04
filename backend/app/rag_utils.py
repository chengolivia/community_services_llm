"""RAG utilities: embedding loading, FAISS index creation, and resource processing."""

import os
import numpy as np
import pandas as pd
import psycopg
from sentence_transformers import SentenceTransformer
import faiss
import pickle 
import glob 

# Environment configuration
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

CONNECTION_STRING = os.getenv("RESOURCE_DB_URL")

# Lazy loading globals
_model = None
_saved_indices = None
_documents = None
_saved_pages = None
_documents_pages = None 

all_organizations = ['cspnj','clhs']

STORAGE_DIR = "vector_storage"

def simple_text_splitter(text, chunk_size=1000, chunk_overlap=100):
    """
    A lightweight replacement for RecursiveCharacterTextSplitter.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # Move the start pointer forward, but subtract overlap
        start += (chunk_size - chunk_overlap)
    return chunks

def ingest_folder(folder_path, category_name,embedding_model,saved_indices_peer,documents_peer):
    """
    Reads all files in a folder, chunks them, and adds them to your FAISS indices.
    """
    category_docs = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".md") or filename.endswith(".html") or filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                # Split into smaller chunks so GPT doesn't get overwhelmed
                chunks = simple_text_splitter(content, chunk_size=1000, chunk_overlap=100)
                for i, chunk in enumerate(chunks):
                    category_docs.append(f"Source: {filename} (Part {i})\n{chunk}")

    # Create the FAISS index for this specific category
    doc_key = f"cat_{category_name}"
    embeddings = embedding_model.encode(category_docs, convert_to_numpy=True)

    # Initialize FAISS (assuming you're using IndexFlatL2 for simplicity)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save to your global dictionaries
    saved_indices_peer[doc_key] = index
    documents_peer[doc_key] = category_docs
    print(f"Loaded {len(category_docs)} chunks into {doc_key}")
    return saved_indices_peer,documents_peer

def save_vector_store(saved_indices_peer,documents_peer):
    """Saves all currently loaded indices and documents to disk."""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
    
    # 1. Save the text documents (the actual content GPT needs)
    with open(os.path.join(STORAGE_DIR, "documents.pkl"), "wb") as f:
        pickle.dump(documents_peer, f)
    
    # 2. Save each FAISS index individually
    for key, index in saved_indices_peer.items():
        index_path = os.path.join(STORAGE_DIR, f"{key}.index")
        faiss.write_index(index, index_path)
    
    print(f"Successfully saved {len(saved_indices_peer)} indices to {STORAGE_DIR}")

def load_vector_store():
    """Loads indices and documents from disk into memory."""
    saved_indices_peer = {}
    documents_peer = {}
    doc_path = os.path.join(STORAGE_DIR, "documents.pkl")
    if not os.path.exists(doc_path):
        print("No existing storage found. Starting fresh.")
        return

    # 1. Load the text documents
    with open(doc_path, "rb") as f:
        documents_peer = pickle.load(f)
    
    # 2. Load all .index files in the directory
    for filename in os.listdir(STORAGE_DIR):
        if filename.endswith(".index"):
            key = filename.replace(".index", "")
            index_path = os.path.join(STORAGE_DIR, filename)
            saved_indices_peer[key] = faiss.read_index(index_path)
            
    print(f"Loaded {len(saved_indices_peer)} indices from disk.")
    return saved_indices_peer, documents_peer

def get_model_and_indices():
    """Lazy load embeddings model and indices."""
    global _model, _saved_indices, _documents, _saved_pages, _documents_pages
    if _model is None:
        _model, _saved_indices, _documents = get_all_resources(all_organizations)
        _saved_pages, _documents_pages = get_all_pages(all_organizations,_model)
    return _model, _saved_indices, _documents, _saved_pages, _documents_pages


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

def get_all_resources(resource_list: list) -> tuple:
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

    documents = {}
    saved_indices = {}
    
    # Process organization resources
    org_resources, resource_embeddings = process_resources(resource_list)
    
    for org_key in org_resources:
        doc_key = f'resource_{org_key}'
        documents[doc_key] = org_resources[org_key]
        saved_indices[doc_key] = create_faiss_index(resource_embeddings[org_key])
        
    return model, saved_indices, documents

def get_all_pages(org_list: list,embedding_model) -> tuple:
    """
    Get all embeddings for RAG system.
    
    Args:
        resource_list: List of organization identifiers
    
    Returns:
        Tuple of (model, indices_dict, documents_dict)
    """

    saved_indices_peer = {}
    documents_peer = {}

    # 2. Try to load from disk first
    saved_indices_peer, documents_peer = load_vector_store()

    # 3. Only ingest if the store is empty (or if you have new files)
    if saved_indices_peer == {}:
        print("[DEBUG] Ingesting files for the first time...")

        for org in org_list:
            all_folders = glob.glob("library_resources/{}/*".format(org))
            for folder in all_folders:
                saved_indices_peer, documents_peer = ingest_folder(folder, folder.split("/")[-1],embedding_model,saved_indices_peer, documents_peer)
        # Save after first ingestion
        save_vector_store(saved_indices_peer,documents_peer)

    return saved_indices_peer, documents_peer