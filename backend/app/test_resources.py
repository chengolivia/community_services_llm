import os
from dotenv import load_dotenv
load_dotenv()

from rag_utils import get_model_and_indices
from tools import resources_tool

embedding_model, saved_resources, documents_resources, metadata_resources, \
    geo_trees, geo_indices, saved_articles, documents_articles = get_model_and_indices()

def test(query, location=None, k=5, org="cspnj"):
    print(f"\n{'='*60}")
    print(f"Query: '{query}' | Location: '{location}' | Org: {org}")
    print('='*60)
    result = resources_tool(
        query=query,
        organization=org,
        location=location,
        k=k,
        saved_indices=saved_resources,
        documents=documents_resources,
        metadata=metadata_resources,
        geo_trees=geo_trees,
        geo_indices=geo_indices,
        embedding_model=embedding_model
    )
    print(result)

test("food banks", location="swartswood",org="cspnj")
