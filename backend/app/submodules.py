"""Core pipeline: resource extraction, refinement, and orchestration for responses.

This module exposes `construct_response` which calls RAG extraction and OpenAI
APIs to build streaming responses.
"""

import os
import openai
import json 

from app.rag_utils import get_model_and_indices
from app.tools import *

# Initialize
openai.api_key = os.environ.get("SECRET_KEY")
# NOTE: This eagerly loads embedding models and indices on import which can be
# expensive; consider lazy-loading in production to reduce startup time.
embedding_model, saved_resources, documents_resources, saved_articles, documents_articles = get_model_and_indices()

def construct_response(
    situation: str,
    all_messages: list,
    model: str,
    organization: str,
    version: str = "new",
):
    # Route to appropriate version implementation
    if version == "new":
        # NEW VERSION: Current implementation with all tools
        return _construct_response_new(situation, all_messages, model, organization)
    elif version == "old":
        # OLD VERSION: RAG retrieval → inject into prompt → GPT call (no tools)
        return _construct_response_old(situation, all_messages, model, organization)
    elif version == "vanilla":
        # VANILLA GPT: Simple prompt → GPT call (no RAG, no tools)
        return _construct_response_vanilla(situation, all_messages, model, organization)
    else:
        # Default to new version if unknown version
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
    """Old version: RAG retrieval → inject into prompt → GPT call (no tools)."""
    from app.tools import query_resources
    
    # Retrieve top resources using RAG
    org_key = organization.lower() if organization else "cspnj"
    top_resources = query_resources(
        query=situation,
        org_key=org_key,
        k=5,
        saved_indices=saved_resources,
        documents=documents_resources,
        embedding_model=embedding_model
    )
    
    # Retrieve library articles (try different categories)
    library_content = []
    for category in ["crisis", "trans", "peer"]:
        try:
            doc_key = f"cat_{category}"
            if doc_key in saved_articles:
                query_emb = embedding_model.encode(situation, convert_to_numpy=True).reshape(1, -1)
                D, I = saved_articles[doc_key].search(query_emb, k=2)
                for idx in I[0]:
                    if idx < len(documents_articles[doc_key]):
                        library_content.append(documents_articles[doc_key][idx])
        except Exception as e:
            print(f"[Old Version] Error retrieving {category}: {e}")
    
    # Format retrieved content into prompt
    rag_context = ""
    if top_resources:
        rag_context += "\n\nRelevant Resources:\n"
        for r in top_resources:
            rag_context += f"- {r['resource_text']}\n"
    
    if library_content:
        rag_context += "\n\nRelevant Library Articles:\n"
        for i, article in enumerate(library_content[:3], 1):  # Limit to top 3
            rag_context += f"{i}. {article}\n\n"
    
    # Build messages with RAG context injected
    system_prompt = "You are a helpful assistant for CSPNJ peer providers. Use the provided resources and articles to help answer questions."
    user_message = situation + rag_context
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    messages += all_messages
    messages.append({"role": "user", "content": user_message})
    
    # Call GPT without tools
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