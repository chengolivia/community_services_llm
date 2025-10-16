import pandas as pd
import numpy as np
import psycopg
import os


DATA_DIR = "./backend/data/"
EMBEDDINGS_DIR = "/Users/oliviacheng/projects/research/community_services_llm/saved_embeddings/saved_embedding_"
CONNECTION_STRING = os.getenv("RESOURCE_DB_URL")

guides = ['human_resource', 'crisis', 'peer', 'trans']


# Connect to PostgreSQL
with psycopg.connect(CONNECTION_STRING) as conn:
    with conn.cursor() as cur:
        # TODO: update columns
        cur.execute("""
            CREATE TABLE IF NOT EXISTS guidance (
                id SERIAL PRIMARY KEY,

            );
        """)
        
        for g in guides:
            print("trying", g)
            df = pd.read_csv(f'{DATA_DIR}{g}.csv')
            embeddings = np.load(f'{EMBEDDINGS_DIR}{org}.npy')
            print(df.shape)
            print(embeddings.shape)
            
            assert len(df) == len(embeddings), f"{g} row/embedding mismatch"
            
            data = [(g, row['service'], row['description'], row['url'], 
                     row['phone'], embeddings[idx].tolist())
                    for idx, row in df.iterrows()]
            
            # TODO: update columns
            cur.executemany(
                "INSERT INTO resources (organization, service, description, url, phone, embedding) VALUES (%s, %s, %s, %s, %s, %s)",
                data
            )
        
        conn.commit()
