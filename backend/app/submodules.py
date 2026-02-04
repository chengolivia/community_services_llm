"""Core pipeline: resource extraction, refinement, and orchestration for responses.

This module exposes `construct_response` which calls RAG extraction and OpenAI
APIs to build streaming responses.
"""

import os
import re
import time
import concurrent.futures
import numpy as np
import openai
import json 
import pickle 

from app.rag_utils import get_model_and_indices
from app.utils import (
    call_chatgpt_api_all_chats,
    stream_process_chatgpt_response,
    get_all_prompts,
)
from app.tools import *
import faiss

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
                        organization=func_args.get("organization", organization),
                        saved_indices=saved_resources,
                        documents=documents_resources,
                        embedding_model=embedding_model
                    )
                elif func_name == "library_tool":
                    output = library_tool(
                        query=func_args.get("query", ""),
                        category=func_args.get("category", "crisis"),
                        saved_indices_peer=saved_indices_peer,
                        documents_peer=documents_peer,
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