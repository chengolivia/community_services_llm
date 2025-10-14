import pandas as pd
import numpy as np
import psycopg
import os


DATA_DIR = "./backend/data/"
EMBEDDINGS_DIR = "/Users/oliviacheng/projects/research/community_services_llm/saved_embeddings/saved_embedding_"
CONNECTION_STRING = os.getenv("RESOURCE_DB_URL")

orgs = ['cspnj', 'clhs']


# Connect to PostgreSQL
with psycopg.connect(CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id SERIAL PRIMARY KEY,
                organization TEXT,
                service TEXT,
                description TEXT,
                url TEXT,
                phone TEXT,
                embedding vector(768)
            );
        """)
        
        for org in orgs:
            print("trying", org)
            df = pd.read_csv(f'{DATA_DIR}{org}.csv')
            embeddings = np.load(f'{EMBEDDINGS_DIR}{org}.npy')
            print(df.shape)
            print(embeddings.shape)
            
            assert len(df) == len(embeddings), f"{org} row/embedding mismatch"
            
            data = [(org, row['service'], row['description'], row['url'], 
                     row['phone'], embeddings[idx].tolist())
                    for idx, row in df.iterrows()]
            
            cur.executemany(
                "INSERT INTO resources (organization, service, description, url, phone, embedding) VALUES (%s, %s, %s, %s, %s, %s)",
                data
            )
        
        conn.commit()
