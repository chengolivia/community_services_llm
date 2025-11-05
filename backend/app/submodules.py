import os
import re
import time
import concurrent.futures

import numpy as np
import openai

from app.rag_utils import get_model_and_indices
from app.utils import (
    call_chatgpt_api_all_chats,
    stream_process_chatgpt_response,
    get_all_prompts,
)

# Initialize
openai.api_key = os.environ.get("SECRET_KEY")
embedding_model, saved_indices, documents = get_model_and_indices()
internal_prompts, external_prompts = get_all_prompts()

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

def construct_response(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
    full_response: str,
    external_resources: str,
    raw_prompt: str
):
    """
    Main response generation with streaming.
    
    Args:
        situation: Current user message
        all_messages: Previous messages
        model: Model type ('chatgpt' or 'copilot')
        organization: Organization identifier
        full_response: Pre-computed goals/questions/resources
        external_resources: External resource text
        raw_prompt: Raw resource extraction output
    
    Yields:
        Response chunks for streaming
    """
    print(f"[Response] Starting at {time.time()}")
    
    # Check if goals are needed (currently always true)
    needs_goals = True
    verbosity = "medium"
    
    # Small talk branch (unused for now)
    if not needs_goals:
        chat_msgs = (
            [{
                "role": "system", 
                "content": f"You are a helpful assistant for {organization}. "
                          "Reply warmly and concisely."
            }]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        response = call_chatgpt_api_all_chats(chat_msgs, stream=True, max_tokens=500)
        yield from stream_process_chatgpt_response(response)
        return
    
    # Brief goals only
    if verbosity == "brief":
        prompt = (
            f"You are a concise assistant for {organization}. "
            "Given the user's request, produce **up to three** SMART goals "
            "as bullet points, each in one short sentence, tailored exactly "
            "to their situation."
        )
        msgs = (
            [{"role": "system", "content": prompt}]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        response = call_chatgpt_api_all_chats(msgs, stream=True, max_tokens=200)
        yield from stream_process_chatgpt_response(response)
        return
    
    # ChatGPT mode
    if model == 'chatgpt':
        msgs = (
            [{
                'role': 'system', 
                'content': f"You are a Co-Pilot tool for {organization}, "
                          "a peer-peer support org."
            }]
            + all_messages
            + [{'role': 'user', 'content': situation}]
        )
        response = call_chatgpt_api_all_chats(msgs, max_tokens=750)
        yield from stream_process_chatgpt_response(response)
        return
    
    # Full copilot orchestration
    print(f"[Response] Full orchestration at {time.time()}")
    
    orchestration_messages = [
        {'role': 'system', 'content': internal_prompts['orchestration']},
        {'role': 'system', 'content': external_resources}
    ]
    orchestration_messages += all_messages
    orchestration_messages += [
        {"role": "user", "content": situation},
        {"role": "user", "content": full_response}
    ]
    
    print(f"[Response] Streaming orchestration at {time.time()}")
    response = call_chatgpt_api_all_chats(
        orchestration_messages, 
        stream=True, 
        max_tokens=1000
    )
    yield from stream_process_chatgpt_response(response)