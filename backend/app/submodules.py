"""Core pipeline: resource extraction, refinement, and orchestration for responses.

This module exposes `construct_response` which calls RAG extraction and OpenAI
APIs to build streaming responses.
"""

import os
import re
import time
import concurrent.futures
import googlemaps
import numpy as np
import openai
import json 
import pickle 
from ddgs import DDGS

from app.rag_utils import get_model_and_indices
from app.utils import (
    call_chatgpt_api_all_chats,
    stream_process_chatgpt_response,
    get_all_prompts,
)
import faiss

# Initialize
openai.api_key = os.environ.get("SECRET_KEY")
# NOTE: This eagerly loads embedding models and indices on import which can be
# expensive; consider lazy-loading in production to reduce startup time.
embedding_model, saved_indices, documents = get_model_and_indices()

internal_prompts, external_prompts = get_all_prompts()

STORAGE_DIR = "vector_storage"
google_maps_api = os.getenv("GOOGLE_API_KEY")
gmaps = googlemaps.Client(key=google_maps_api)


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
def ingest_folder(folder_path, category_name):
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

def save_vector_store():
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
    global documents_peer, saved_indices_peer
    
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

saved_indices_peer = {}
documents_peer = {}

# 2. Try to load from disk first
load_vector_store()

# 3. Only ingest if the store is empty (or if you have new files)
if not saved_indices_peer:

    print("[DEBUG] Ingesting files for the first time...")
    ingest_folder("library_resources/peer", "peer")
    ingest_folder("library_resources/crisis", "crisis")
    ingest_folder("library_resources/trans", "trans")
    # Save after first ingestion
    save_vector_store()

# ============================================================================
# RAG RESOURCE EXTRACTION
# ============================================================================

def extract_resources(
    embedding_model, 
    saved_indices, 
    documents, 
    situation: str, 
    which_indices: dict, 
    k: int = 25
) -> str:
    """
    Extract most similar resources using RAG.
    
    Args:
        embedding_model: SentenceTransformer model
        saved_indices: Dictionary of FAISS indices
        documents: Dictionary of document lists
        situation: User's situation text
        which_indices: Dictionary indicating which indices to search
        k: Number of results to retrieve
    
    Returns:
        Newline-separated resource strings
    """
    results = []
    
    for index_name, should_search in which_indices.items():
        if not should_search:
            continue
            
        # Encode query
        query_embedding = embedding_model.encode(
            situation, 
            convert_to_tensor=False
        )
        
        # Search index
        _, indices = saved_indices[index_name].search(
            np.array([query_embedding]), 
            k=k
        )
        
        # Collect results
        doc_list = documents[index_name]
        results.extend([
            doc_list[j] for j in indices[0] 
            if j < len(doc_list)
        ])
    
    return "\n".join(results)

# ============================================================================
# RESOURCE PROCESSING
# ============================================================================

def deduplicate_resources(resources: list) -> list:
    """
    Remove duplicate resources from list.
    
    Args:
        resources: List of resource strings
    
    Returns:
        Deduplicated list of resources
    """
    all_lines = "\n".join(resources).split("\n")
    seen_resources = set()
    unique_lines = []
    
    idx = 0
    while idx < len(all_lines):
        line = all_lines[idx]
        
        # Found a new resource header
        if "Resource:" in line and line not in seen_resources:
            seen_resources.add(line)
            unique_lines.append(line)
            idx += 1
            
            # Include continuation lines
            while idx < len(all_lines) and "Resource:" not in all_lines[idx]:
                unique_lines.append(all_lines[idx])
                idx += 1
        
        # Skip duplicate resource
        elif line in seen_resources:
            idx += 1
            while idx < len(all_lines) and "Resource:" not in all_lines[idx]:
                idx += 1
        
        # Skip non-resource line
        else:
            idx += 1
    
    return unique_lines

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def get_questions_resources(
    situation: str,
    all_messages: list,
    organization: str,
    k: int = 5
) -> tuple:
    """
    Process user situation and generate goals, questions, and resources.
    
    Args:
        situation: Current user message
        all_messages: List of previous messages
        organization: Organization identifier
        k: Number of resources to retrieve
    
    Returns:
        Tuple of (full_response, external_resources, raw_resource_prompt)
    """
    print(f"[Pipeline] Starting at {time.time()}")
    
    # Build message lists for parallel processing
    prompts = ['goal', 'followup_question', 'resource']
    message_lists = []
    
    for prompt_name in prompts:
        system_msg = internal_prompts[prompt_name].replace(
            "[Organization]", 
            organization
        )
        messages = (
            [{'role': 'system', 'content': system_msg}]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        message_lists.append(messages)
    
    # Parallel API calls
    with concurrent.futures.ThreadPoolExecutor() as executor:
        responses = list(executor.map(
            lambda msgs: call_chatgpt_api_all_chats(msgs, stream=False),
            message_lists
        ))
    
    print(f"[Pipeline] Initial responses at {time.time()}")
    
    # Extract resource mentions from response
    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    resource_mentions = re.findall(
        pattern, 
        str(responses[2]), 
        flags=re.DOTALL
    )
    resource_mentions.append(situation)
    
    # Retrieve resources in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resource_lists = list(executor.map(
            lambda text: extract_resources(
                embedding_model, 
                saved_indices, 
                documents, 
                text,
                {f'resource_{organization}': True},
                k=k
            ),
            resource_mentions
        ))
    
    print(f"[Pipeline] Resources retrieved at {time.time()}")
    
    # Deduplicate and refine resources
    unique_resources = deduplicate_resources(resource_lists)
    
    refined_resources = call_chatgpt_api_all_chats(
        [
            {
                'role': 'system', 
                'content': internal_prompts['refine_resources'].format(
                    organization, 
                    situation
                )
            },
            {'role': 'user', 'content': "\n".join(unique_resources)}
        ],
        stream=False
    )
    
    print(f"[Pipeline] Resources refined at {time.time()}")
    
    # Build response
    response = "\n".join([
        f"SMART Goals: {responses[0]}",
        f"Questions: {responses[1]}",
        f"Resources (use only these resources):\n{refined_resources}",
    ])
    
    # External resources (currently empty)
    external_resources = ""
    raw_resource_prompt = responses[2]
    
    return response, external_resources, raw_resource_prompt

# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def parse_goals(full_response: str) -> list:
    """Parse SMART goals from response."""
    goals = []
    match = re.search(
        r"SMART Goals:\s*(.*?)\n(Questions|Goals|Steps)", 
        full_response, 
        flags=re.DOTALL
    )
    
    if match:
        section = match.group(1).strip()
        for line in section.splitlines():
            text = line.strip().lstrip("•").strip()
            if text:
                goals.append(text)
    
    return goals

def parse_resources(full_response: str, raw_prompt: str, k: int = 25) -> list:
    """
    Parse resources from response.
    
    Args:
        full_response: The full pipeline response
        raw_prompt: Raw resource extraction output
        k: Maximum number of additional resources
    
    Returns:
        List of formatted resource strings
    """
    resources = []
    
    # Parse main resources section
    match = re.search(
        r'Resources[\s\S]*?:\s*\n([\s\S]*)',
        full_response
    )
    
    if match:
        section = match.group(1).strip()
        for line in section.splitlines():
            text = line.strip().lstrip("•").strip()
            if text:
                resources.append(text)
    
    # Parse additional resources from raw prompt
    block_re = (
        r"\[Resource\]\s*"
        r"Name:\s*(?P<name>.+?)\s*"
        r"URL:\s*(?P<url>\S+?)\s*"
        r"Action:\s*(?P<action>.+?)\s*"
        r"\[/Resource\]"
    )
    
    for match in re.finditer(block_re, raw_prompt, flags=re.DOTALL | re.IGNORECASE):
        if len(resources) >= k:
            break
            
        name = match.group("name").strip()
        url = match.group("url").strip()
        action = match.group("action").strip()
        
        entry = f"**{name}**  \n"
        if url:
            entry += f"[Link]({url})  \n"
        if action:
            entry += f"**Action:** {action}"
        
        resources.append(entry)
    
    return resources

def fetch_goals_and_resources(
    situation: str, 
    all_messages: list, 
    organization: str, 
    k: int = 25
) -> tuple:
    """
    Main entry point for goals and resources pipeline.
    
    Args:
        situation: User's current message
        all_messages: Previous conversation messages
        organization: Organization identifier
        k: Number of resources to retrieve
    
    Returns:
        Tuple of (goals, resources, full_response, external_resources, raw_prompt)
    """
    # Run pipeline
    full_response, external_resources, raw_prompt = get_questions_resources(
        situation, all_messages, organization, k=k
    )
    
    print(f"[Pipeline] Questions/resources done at {time.time()}")
    
    # Parse outputs
    goals = parse_goals(full_response)
    resources = parse_resources(full_response, raw_prompt, k=k)
    
    # Add external resources to beginning
    if external_resources:
        resources.insert(0, external_resources)
    
    print(f"[Pipeline] Parsing done at {time.time()}")
    
    return goals, resources, full_response, external_resources, raw_prompt

# ============================================================================
# RESPONSE CONSTRUCTION
# ============================================================================

def query_resources(
    query: str,
    org_key: str,
    k: int = 5
):
    """
    Search preloaded organization resources using FAISS embeddings.
    
    Args:
        query: User query string
        org_key: Organization ID (e.g., 'cspnj')
        k: Number of top results to return

    Returns:
        List of dictionaries with 'resource_text' and FAISS similarity 'score'
    """
    doc_key = f'resource_{org_key}'
    
    if doc_key not in saved_indices:
        print(f"[Warning] No resources loaded for {org_key}")
        return []
    
    # Encode the query
    query_emb = embedding_model.encode(query, convert_to_numpy=True).reshape(1, -1)
    
    # Search FAISS index
    D, I = saved_indices[doc_key].search(query_emb, k=k)
    
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx < len(documents[doc_key]):
            results.append({
                "resource_text": documents[doc_key][idx],
                "score": float(score)
            })
    
    return results

def resources_tool(query: str, organization: str, k: int = 5):
    """
    GPT-accessible tool for fetching top organization resources.
    Returns formatted string for GPT consumption.
    """
    top_resources = query_resources(query, organization.lower(), k=k)
    if not top_resources:
        return "No relevant resources found."
    
    lines = []
    for r in top_resources:
        # r['resource_text'] is already a formatted string if you used documents
        lines.append(f"- {r['resource_text']} (score: {r['score']:.2f})")
    
    return "\n".join(lines)

def library_tool(query: str, category: str, k: int = 3):
    """
    Searches specialized document libraries (e.g., 'trans', 'crisis', 'legal').
    """
    doc_key = f"cat_{category.lower()}"
    
    if doc_key not in saved_indices_peer:
        return f"Error: The category '{category}' does not exist. Available: trans, crisis, housing."
    
    # Standard FAISS search (same logic as your query_resources)
    query_emb = embedding_model.encode(query, convert_to_numpy=True).reshape(1, -1)
    D, I = saved_indices_peer[doc_key].search(query_emb, k=k)
    
    results = [documents_peer[doc_key][idx] for idx in I[0] if idx < len(documents_peer[doc_key])]
    
    if not results:
        return "No specific documents found for that query."
        
    return "\n---\n".join(results)

def directions_tool(origin: str, destination: str, mode: str = "driving"):
    """
    Get detailed, step-by-step navigation instructions.
    """
    try:
        result = gmaps.directions(origin, destination, mode=mode, departure_time="now")
        if not result:
            return "No routes found."
        leg = result[0]['legs'][0]
        full_instructions = [f"Total Trip: {leg['duration']['text']} ({leg['distance']['text']})\n"]
        for i, step in enumerate(leg['steps'], 1):
            # Clean up HTML tags (like <b>) that Google returns
            import re
            instruction = re.sub('<[^<]+?>', '', step['html_instructions'])
            duration = step['duration']['text']
            # Add specific transit details if they exist
            if step.get('travel_mode') == 'TRANSIT':
                details = step.get('transit_details', {})
                line = details.get('line', {}).get('short_name', 'Transit')
                stop = details.get('arrival_stop', {}).get('name', 'destination')
                instruction += f" (Take {line} to {stop})"
            full_instructions.append(f"{i}. {instruction} [{duration}]")
        return "\n".join(full_instructions)
    except Exception as e:
        return f"Error: {str(e)}"

def check_eligibility(program: str, household_size: int, monthly_income: float):
    """
    Checks eligibility based on official 2026 NJ income limits.
    """
    program = program.lower()
    
    # 2026 NJ SNAP Gross Income Limits (185% Federal Poverty Level)
    # Source: NJ Dept of Human Services / USDA
    snap_limits = {
        1: 2413,
        2: 3261,
        3: 4109,
        4: 4957,
        5: 5805,
        6: 6653,
        7: 7501,
        8: 8349
    }
    
    if "snap" in program or "food stamp" in program:
        # Get limit (add $848 for each person beyond 8)
        if household_size <= 8:
            limit = snap_limits.get(household_size)
        else:
            limit = 8349 + (848 * (household_size - 8))
            
        if monthly_income <= limit:
            return f"✅ LIKELY ELIGIBLE. Household income (${monthly_income}) is BELOW the NJ SNAP gross limit (${limit}) for {household_size} people."
        else:
            return f"❌ LIKELY INELIGIBLE. Household income (${monthly_income}) is ABOVE the NJ SNAP gross limit (${limit})."

    return "Error: Unknown benefit program. Currently supporting: SNAP."

def web_search_tool(query: str):
    """
    Performs a live web search for real-time information.
    """
    try:
        results = DDGS().text(query, max_results=4)
        if not results:
            return "No results found."
        # Format results nicely for the LLM
        formatted = ""
        for r in results:
            formatted += f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}\n\n"
        return formatted
    except Exception as e:
        return f"Search failed: {str(e)}"

def calculator_tool(expression: str):
    """
    A safe calculator for basic arithmetic. 
    Supports +, -, *, /, and round().
    """
    allowed_chars = "0123456789+-*/(). "
    if any(char not in allowed_chars for char in expression):
        return "Error: Invalid characters. Only numbers and basic math (+-*/) allowed."
    
    try:
        # Evaluate using a restricted scope to prevent code injection
        # (For production, consider libraries like 'simpleeval')
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"

def construct_response(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
    full_response: str,
    external_resources: str,
    raw_prompt: str
):
    # 1. Update the tool definition to the 'tools' format
    tools = [
        {
            "type": "function", # Required wrapper
            "function": {
                "name": "resources_tool",
                "description": "Search top organization resources given a user query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "User query about services"},
                        "organization": {"type": "string", "description": "Organization ID, e.g., 'cspnj'"},
                        "k": {"type": "integer", "description": "Number of top results", "default": 5}
                    },
                    "required": ["query", "organization"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "library_tool",
                "description": "Search deep-dive documents for specific topics like LGBTQ/Trans issues, Crisis intervention, or Peer Support.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The specific question to look up"},
                        "category": {
                            "type": "string", 
                            "enum": ["trans", "crisis", "peer"], # Tell GPT what's available
                            "description": "The topic area to search"
                        }
                    },
                    "required": ["query", "category"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "directions_tool",
                "description": "Get travel time and distance between two locations for driving or transit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string", "description": "Starting address or city"},
                        "destination": {"type": "string", "description": "Ending address or city"},
                        "mode": {
                            "type": "string", 
                            "enum": ["driving", "transit","walking", "bicycling"], 
                            "description": "Method of travel"
                        }
                    },
                    "required": ["origin", "destination", "mode"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculator_tool",
                "description": "Perform basic math calculations (e.g., converting hourly wage to monthly income).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "The math expression to evaluate, e.g., '15 * 35 * 4.33'"}
                    },
                    "required": ["expression"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_search_tool",
                "description": "Search the internet for real-time info, news, or broad topics not in the library.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search keywords"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_eligibility",
                "description": "Check if a user qualifies for benefits like SNAP based on income/household size.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "program": {"type": "string", "enum": ["snap"], "description": "The benefit program name"},
                        "household_size": {"type": "integer", "description": "Number of people in the household"},
                        "monthly_income": {"type": "number", "description": "Total gross monthly income"}
                    },
                    "required": ["program", "household_size", "monthly_income"]
                }
            }
        },
    ]

    orchestration_messages = [
        {"role": "system", "content": "You are a helpful assistant for CSPNJ peer providers. Use tools to fetch resources."}
    ]
    orchestration_messages += all_messages
    orchestration_messages.append({"role": "user", "content": situation})

    response = openai.chat.completions.create(
        model="gpt-5.2",
        messages=orchestration_messages,
        tools=tools,
        tool_choice="auto",
        stream=True
    )

    # NEW: Use a dictionary to track multiple tool calls by their index
    tool_calls_accum = {} 

    for event in response:
        choice = event.choices[0]
        delta = choice.delta

        # 1. Handle normal text content
        if delta.content:
            formatted_content = delta.content.replace("\n", "<br/>")
            yield f"data: {formatted_content}\n\n"

        # 2. Accumulate Tool Calls
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                
                # Initialize this tool call if it's the first time we see this index
                if idx not in tool_calls_accum:
                    tool_calls_accum[idx] = {"id": "", "name": "", "arguments": ""}
                
                if tc_delta.id:
                    tool_calls_accum[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls_accum[idx]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_accum[idx]["arguments"] += tc_delta.function.arguments

        # 3. Check if we should execute the tools
        if choice.finish_reason == "tool_calls":
            # Append the assistant's tool_calls message FIRST
            assistant_tool_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    } for tc in tool_calls_accum.values()
                ]
            }
            orchestration_messages.append(assistant_tool_msg)

            # Execute EACH tool call and append the results
            for idx, tc in tool_calls_accum.items():
                func_name = tc["name"]
                func_args = json.loads(tc["arguments"]) # Now this will only have ONE object
                
                print(f"[DEBUG] Executing {func_name} with {func_args}")
                
                if func_name == "resources_tool":
                    output = resources_tool(
                        query=func_args.get("query", ""),
                        organization=func_args.get("organization", organization)
                    )
                elif func_name == "library_tool":
                    output = library_tool(
                        query=func_args.get("query", ""),
                        category=func_args.get("category", "crisis")
                    )
                    print("Library tool output {}".format(output))
                elif func_name == "directions_tool":
                    output = directions_tool(
                        origin=func_args.get("origin", ""),
                        destination=func_args.get("destination", ""),
                        mode=func_args.get("mode", "driving")
                    )
                    print("Direction tool output {}".format(output))
                elif func_name == "calculator_tool":
                    output = calculator_tool(
                        expression=func_args.get("expression", "0"),
                    )
                    print("Calculator tool output {}".format(output))
                elif func_name == "web_search_tool":
                    output = web_search_tool(
                        query=func_args.get("query", ""),
                    )
                    print("Web Search tool output {}".format(output))
                elif func_name == "check_eligibility":
                    output = check_eligibility(
                        program=func_args.get("program", ""),
                        household_size=func_args.get("household_size", ""),
                        monthly_income=func_args.get("monthly_income",""),
                    )
                    print("Eligibility tool output {}".format(output))
                else:
                    output = "Error: Unknown tool."

                # Add each result to history
                orchestration_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": output
                })

            # 4. Final follow-up call with all results
            followup = openai.chat.completions.create(
                model="gpt-5.2",
                messages=orchestration_messages,
                stream=True
            )
            
            for f_event in followup:
                if f_event.choices[0].delta.content:
                    formatted_content = f_event.choices[0].delta.content.replace("\n", "<br/>")
                    yield f"data: {formatted_content}\n\n"

    yield "[DONE]\n\n"