"""Core pipeline: resource extraction, refinement, and orchestration for responses.

This module exposes `construct_response` which calls RAG extraction and OpenAI
APIs to build streaming responses.
"""

import os
import openai
import json 
import re
import time
import concurrent.futures
import numpy as np

from app.rag_utils import get_model_and_indices
from app.tools import *
from app.utils import (
    call_chatgpt_api_all_chats,
    stream_process_chatgpt_response,
    get_all_prompts,
)

# Initialize
openai.api_key = os.environ.get("SECRET_KEY")
# NOTE: This eagerly loads embedding models and indices on import which can be
# expensive; consider lazy-loading in production to reduce startup time.
embedding_model, saved_resources, documents_resources, saved_articles, documents_articles = get_model_and_indices()
internal_prompts, external_prompts = get_all_prompts()


# ============================================================================
# Legacy RAG pipeline helpers (used for the "Old Version")
# ============================================================================

def extract_resources(
    embedding_model,
    saved_indices,
    documents,
    situation: str,
    which_indices: dict,
    k: int = 25,
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
            convert_to_tensor=False,
        )

        # Search index
        _, indices = saved_indices[index_name].search(
            np.array([query_embedding]),
            k=k,
        )

        # Collect results
        doc_list = documents[index_name]
        results.extend(
            [doc_list[j] for j in indices[0] if j < len(doc_list)]
        )

    return "\n".join(results)


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


def get_questions_resources(
    situation: str,
    all_messages: list,
    organization: str,
    k: int = 5,
) -> tuple:
    """
    Process user situation and generate goals, questions, and resources.

    This reproduces the legacy "old" pipeline behavior.
    """
    print(f"[Pipeline] Starting at {time.time()}")

    # Build message lists for parallel processing
    prompts = ["goal", "followup_question", "resource"]
    message_lists = []

    for prompt_name in prompts:
        system_msg = internal_prompts[prompt_name].replace(
            "[Organization]",
            organization,
        )
        messages = (
            [{"role": "system", "content": system_msg}]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        message_lists.append(messages)

    # Parallel API calls
    with concurrent.futures.ThreadPoolExecutor() as executor:
        responses = list(
            executor.map(
                lambda msgs: call_chatgpt_api_all_chats(msgs, stream=False),
                message_lists,
            )
        )

    print(f"[Pipeline] Initial responses at {time.time()}")

    # Extract resource mentions from response
    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    resource_mentions = re.findall(
        pattern,
        str(responses[2]),
        flags=re.DOTALL,
    )
    resource_mentions.append(situation)

    # Retrieve resources in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resource_lists = list(
            executor.map(
                lambda text: extract_resources(
                    embedding_model,
                    saved_resources,
                    documents_resources,
                    text,
                    {f"resource_{organization}": True},
                    k=k,
                ),
                resource_mentions,
            )
        )

    print(f"[Pipeline] Resources retrieved at {time.time()}")

    # Deduplicate and refine resources
    unique_resources = deduplicate_resources(resource_lists)

    refined_resources = call_chatgpt_api_all_chats(
        [
            {
                "role": "system",
                "content": internal_prompts["refine_resources"].format(
                    organization,
                    situation,
                ),
            },
            {"role": "user", "content": "\n".join(unique_resources)},
        ],
        stream=False,
    )

    print(f"[Pipeline] Resources refined at {time.time()}")

    # Build response
    response = "\n".join(
        [
            f"SMART Goals: {responses[0]}",
            f"Questions: {responses[1]}",
            f"Resources (use only these resources):\n{refined_resources}",
        ]
    )

    # External resources (legacy behavior: currently empty)
    external_resources = ""
    raw_resource_prompt = responses[2]

    return response, external_resources, raw_resource_prompt


def parse_goals(full_response: str) -> list:
    """Parse SMART goals from response."""
    goals = []
    match = re.search(
        r"SMART Goals:\s*(.*?)\n(Questions|Goals|Steps)",
        full_response,
        flags=re.DOTALL,
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
        r"Resources[\s\S]*?:\s*\n([\s\S]*)",
        full_response,
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
    k: int = 25,
) -> tuple:
    """
    Main entry point for legacy goals and resources pipeline.

    Returns:
        Tuple of (goals, resources, full_response, external_resources, raw_prompt)
    """
    # Run pipeline
    full_response, external_resources, raw_prompt = get_questions_resources(
        situation,
        all_messages,
        organization,
        k=k,
    )

    print(f"[Pipeline] Questions/resources done at {time.time()}")

    # Parse outputs
    goals = parse_goals(full_response)
    resources = parse_resources(full_response, raw_prompt, k=k)

    # Add external resources to beginning (kept for compatibility)
    if external_resources:
        resources.insert(0, external_resources)

    print(f"[Pipeline] Parsing done at {time.time()}")

    return goals, resources, full_response, external_resources, raw_prompt


def _legacy_construct_response(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
    full_response: str,
    external_resources: str,
    raw_prompt: str,
):
    """
    Legacy response generation with streaming.

    This is essentially the original `construct_response` implementation.
    """
    print(f"[Response] Starting at {time.time()}")

    # For the "old version" path we always use the full copilot orchestration.
    needs_goals = True
    verbosity = "medium"

    # Small talk branch (kept for completeness, but not used in practice)
    if not needs_goals:
        chat_msgs = (
            [
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful assistant for {organization}. "
                        "Reply warmly and concisely."
                    ),
                }
            ]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        response = call_chatgpt_api_all_chats(
            chat_msgs,
            stream=True,
            max_tokens=500,
        )
        yield from stream_process_chatgpt_response(response)
        return

    # Brief goals only branch (kept for completeness)
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
        response = call_chatgpt_api_all_chats(
            msgs,
            stream=True,
            max_tokens=200,
        )
        yield from stream_process_chatgpt_response(response)
        return

    # ChatGPT mode branch (not used in current integration, but retained)
    if model == "chatgpt":
        msgs = (
            [
                {
                    "role": "system",
                    "content": (
                        f"You are a Co-Pilot tool for {organization}, "
                        "a peer-peer support org."
                    ),
                }
            ]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        response = call_chatgpt_api_all_chats(
            msgs,
            stream=True,
            max_tokens=750,
        )
        yield from stream_process_chatgpt_response(response)
        return

    # Full copilot orchestration (main path)
    print(f"[Response] Full orchestration at {time.time()}")

    orchestration_messages = [
        {"role": "system", "content": internal_prompts["orchestration"]},
        {"role": "system", "content": external_resources},
    ]
    orchestration_messages += all_messages
    orchestration_messages += [
        {"role": "user", "content": situation},
        {"role": "user", "content": full_response},
    ]

    print(f"[Response] Streaming orchestration at {time.time()}")
    response = call_chatgpt_api_all_chats(
        orchestration_messages,
        stream=True,
        max_tokens=1000,
    )
    yield from stream_process_chatgpt_response(response)


def construct_response(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
    version: str = "new",
):
    # Route to appropriate version implementation
    print(f"[construct_response] Version received: {version}")  # Add this
    if version == "new":
        # NEW VERSION: Current implementation with all tools
        print("[construct_response] Routing to NEW VERSION")  # Add this
        return _construct_response_new(situation, all_messages, model, organization)
    elif version == "old":
        # OLD VERSION: RAG retrieval → inject into prompt → GPT call (no tools)
        print("[construct_response] Routing to OLD VERSION")  # Add this
        return _construct_response_old(situation, all_messages, model, organization)
    elif version == "vanilla":
        # VANILLA GPT: Simple prompt → GPT call (no RAG, no tools)
        print("[construct_response] Routing to VANILLA VERSION")  # Add this
        return _construct_response_vanilla(situation, all_messages, model, organization)
    else:
        # Default to new version if unknown version
        print("[construct_response] Routing to NEW VERSION (default)")  # Add this
        return _construct_response_new(situation, all_messages, model, organization)

def _construct_response_new(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
):
    """New version: Current implementation with all tools."""
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

    prompt = """You are PeerCoPilot, a supportive AI assistant for peer providers at {}.
    Use peer-friendly, non-clinical language grounded in CSPNJ-aligned values: mutuality, respect, shared humanity, choice, and self-direction. Speak with peers, not at them. Avoid jargon unless the peer uses it first.
    Prioritize safety and accuracy. Do not invent facts, resources, policies, or services. If you are unsure, say so and ask a clarifying question or suggest checking together. Never guess.
    When helpful, think intentionally about which tools to use and orchestrate across multiple tools to surface the most relevant, practical information. Use tools only when they add value, and clearly synthesize what you find.
    Keep responses concise, supportive, and actionable. Focus on what’s most useful right now rather than covering everything.
    Whenever appropriate, offer natural next steps—such as follow-up questions, related resources, or another way PeerCoPilot could support the peer—without being directive or pushy.""".format(organization)

    orchestration_messages = [
        {"role": "system", "content": prompt}
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
                        organization=func_args.get("organization", organization),
                        saved_indices=saved_resources,
                        documents=documents_resources,
                        embedding_model=embedding_model
                    )
                elif func_name == "library_tool":
                    output = library_tool(
                        query=func_args.get("query", ""),
                        category=func_args.get("category", "crisis"),
                        saved_indices_peer=saved_articles,
                        documents_peer=documents_articles,
                        embedding_model=embedding_model
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

def _construct_response_old(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
):
    """
    Old version: recreate the legacy goals/questions/resources pipeline
    and orchestration behavior (no tools).
    """
    # 1) Run the legacy questions/resources pipeline
    #    This uses internal prompts, RAG over resources, and refinement.
    goals, resources, full_response, external_resources, raw_prompt = fetch_goals_and_resources(
        situation=situation,
        all_messages=all_messages,
        organization=organization,
        k=25,
    )

    # 2) Stream the final response using the legacy orchestration logic.
    #    We explicitly pass model="copilot" to take the full orchestration path.
    return _legacy_construct_response(
        situation=situation,
        all_messages=all_messages,
        model="copilot",
        organization=organization,
        full_response=full_response,
        external_resources=external_resources,
        raw_prompt=raw_prompt,
    )

def _construct_response_vanilla(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
):
    """Vanilla GPT: Simple prompt → GPT call (no RAG, no tools)."""
    # Build messages with simple system prompt
    system_prompt = "You are a helpful assistant for CSPNJ peer providers. Answer questions based on your general knowledge."
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    messages += all_messages
    messages.append({"role": "user", "content": situation})
    
    # Call GPT without tools, without RAG
    response = openai.chat.completions.create(
        model="gpt-5.2",
        messages=messages,
        stream=True
    )
    
    for event in response:
        if event.choices[0].delta.content:
            formatted_content = event.choices[0].delta.content.replace("\n", "<br/>")
            yield f"data: {formatted_content}\n\n"
    
    yield "[DONE]\n\n"