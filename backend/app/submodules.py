import openai 
import concurrent.futures
import re
import json 
import os 
import numpy as np
from copy import deepcopy
import time 
from app.rag_utils import get_model_and_indices


from app.eligibility_check import eligibility_check
from app.utils import (
    call_chatgpt_api_all_chats,
    stream_process_chatgpt_response,
    get_all_prompts,
    call_chatgpt_with_functions,
)
embedding_model, saved_indices, documents = get_model_and_indices()  # Ensures embeddings are loaded

openai.api_key = os.environ.get("SECRET_KEY")

internal_prompts, external_prompts = get_all_prompts()

def get_questions_resources(situation,all_messages,organization,k: int = 5):
    """Process user situation + generate questions and resources

    Arguments:
        situation: String, last message user sent
        all_messages: List of dictionaries, with all the messages

    Returns: String response, with resources and questions, 
        and a string, containing a dictionary on which 
        external resources to load """
    
    # Lazy load embeddings on first use
    print("Getting model, time={}".format(time.time()))
    
    all_message_list = []
    
    for prompt in ['goal','followup_question','resource']:#,'which_resource','benefit_extract']:
        all_message_list.append([{'role': 'system', 'content': internal_prompts[prompt].replace("[Organization]",organization)}]+all_messages+[{"role": "user", "content": situation}])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        initial_responses = list(executor.map(lambda s: call_chatgpt_api_all_chats(s, stream=False), all_message_list))
    initial_responses = deepcopy(list(initial_responses))
    print("Initial responses, Content {}, time={}".format(sum([sum([len(i['content']) for i in j]) for j in all_message_list]),time.time()))

    # Combine prompts with external information on resources
    pattern = r"\[Resource\](.*?)\[\/Resource\]"
    matches = re.findall(pattern,str(initial_responses[2]),flags=re.DOTALL)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resources = list(executor.map(lambda s: extract_resources(embedding_model, saved_indices, documents, s, {'resource_{}'.format(organization): True},k=k), matches))
    print("Match resources time={}",time.time())
    ## Debugging 10/16

    print(len(resources),len(set(resources)))

    all_lines = "\n".join(resources)
    all_lines = all_lines.split("\n")
    seen_resources = set()
    real_lines = []
    idx = 0
    while idx < len(all_lines):
        if "Resource:" in all_lines[idx] and all_lines[idx] not in seen_resources:
            seen_resources.add(all_lines[idx])
            real_lines.append(all_lines[idx])
            idx += 1
            while idx < len(all_lines) and "Resource:" not in all_lines[idx]:
                real_lines.append(all_lines[idx])
                idx += 1
        elif all_lines[idx] in seen_resources:
            idx += 1
            while idx < len(all_lines) and "Resource:" not in all_lines[idx]:
                idx += 1
        else:
            idx += 1
    

    all_resources = call_chatgpt_api_all_chats([{'role': 'system', 'content': 'You are a highly knowledgable system that assists {}, a peer support organization, with finding the correct resources. Out of this large list of resources, return a nicely formatted list, with phones/addresses (ONLY USE THE INFORMATION PROVIDED) of the most relevant and diverse resources for the following situation: {}'.format(organization,situation)},{'role': 'user', 'content': "\n".join(real_lines)}], stream=False)
    print("Resource trimming, content {}, time={}".format(len(all_resources),time.time()))
    # # Combine prompts with external information on benefits
    # pattern = r"\[Situation\](.*?)\[/Situation\]"
    # benefit_info = re.sub(
    #     pattern,
    #     lambda m: eligibility_check(m.group()),  # Pass the matched content as a string
    #     initial_responses[4],
    #     flags=re.DOTALL
    # )
    # if "Irrelevant" in benefit_info:
    #     benefit_info = ""
    # else:
    #     constructed_messages = [{'role': 'system', 'content': internal_prompts['benefit_system']}] + [{'role': 'user', 'content': i['content'][:1000]} for i in all_messages if i['role'] == 'user']
    #     constructed_messages.append({'role': 'user', 'content': situation})
    #     constructed_messages.append({'role': 'user', 'content': 'Eligible Benefits: {}'.format(benefit_info)})
    #     benefit_info = call_chatgpt_api_all_chats(constructed_messages,stream=False)

    # Call modules with additional extra information
    # which_external_resources = initial_responses[3]
    # try:
    #     which_external_resources = json.loads(which_external_resources.strip()) 
    # except:
    #     which_external_resources = {}
    # full_situation = "\n".join([i['content'] for i in all_messages if i['role'] == 'user' and len(i['content']) < 500] + [situation])
    # external_resources = extract_resources(embedding_model, saved_indices, documents, full_situation,which_external_resources,k=k)
    external_resources = ""

    # capture the raw "[Resource]...[/Resource]" output
    raw_resource_prompt = initial_responses[2]

    # build the normal response text
    sep = "\n\n\n"
    # RIGHT HERE -<<<<
    response = "\n".join([
        f"SMART Goals: {initial_responses[0]}",
        f"Questions: {initial_responses[1]}",
        "Resources (use only these resources):\n" + all_resources, #TODO: Remove this, from debugging 
        # f"Benefit Info: {benefit_info}"
    ])

    # now return three things: 
    # 1) the string we already had, 
    # 2) the RAG hits, 
    # 3) the raw resource prompt
    return response, external_resources, raw_resource_prompt

def format_resources_for_user(situation, all_messages, organization, max_items: int = 3):
    """
    Turn raw RAG lines into:
    [{"name", "url", "how_to_use", "phone", "url_phone", "address", "action"}, …]
    """
    _, raw_resources, __ = get_questions_resources(situation, all_messages, organization)
    formatted = []

    # Expect each line in raw_resources like:
    # Resource: <name>, URL: <url>, Address: <address>, Phone: <phone>, Action: <action>, Description: <how_to_use>
    pattern = (
        r"Resource:\s*(?P<name>[^,]+),\s*"
        r"URL:\s*(?P<url>[^,]+),\s*"
        r"Address:\s*(?P<address>[^,]+),\s*"
        r"Phone:\s*(?P<phone>[^,]+),\s*"
        r"Action:\s*(?P<action>[^,]+),\s*"
        r"Description:\s*(?P<how_to_use>.+)"
    )

    for entry in raw_resources.splitlines()[:max_items]:
        m = re.match(pattern, entry.strip(), flags=re.IGNORECASE)
        if m:
            formatted.append({
                "name":       m.group("name").strip(),
                "url":        m.group("url").strip(),
                "address":    m.group("address").strip(),
                "phone":      m.group("phone").strip(),
                "action":     m.group("action").strip(),
                "how_to_use": m.group("how_to_use").strip(),
            })
        else:
            # Fallback to minimal info if the line doesn't match the pattern
            formatted.append({
                "name":       entry.strip(),
                "url":        "",
                "address":    "",
                "phone":      "",
                "action":     "",
                "how_to_use": ""
            })
    return formatted



def format_additional_resources(raw_resource_prompt: str, max_items: int = 3):
    """
    Parse the raw [Resource]…[/Resource] output into a list of dicts:
      [{"name","url","action"}, …]
    """
    formatted = []
    block_re = (
        r"\[Resource\]\s*"
        r"Name:\s*(?P<name>.+?)\s*"
        r"URL:\s*(?P<url>\S+?)\s*"
        r"Action:\s*(?P<action>.+?)\s*"
        r"\[/Resource\]"
    )
    for m in re.finditer(block_re, raw_resource_prompt, flags=re.DOTALL|re.IGNORECASE):
        formatted.append({
            "name":   m.group("name").strip(),
            "url":    m.group("url").strip(),
            "action": m.group("action").strip()
        })
        if len(formatted) >= max_items:
            break
    return formatted

# ────────────────────────────────────────────────────────────────────────────
# BOXES helper: run once, returns parsed lists for front-end panels
def fetch_goals_and_resources(situation, all_messages, organization, k: int = 25):
    """
    Returns:
      - goals: List[str]            # parsed SMART goals
      - resources: List[str]        # formatted "Name — Action" strings
    """
    # 1) get the three outputs from the existing pipeline
    full_response, external_resources, raw_prompt = get_questions_resources(
        situation, all_messages, organization, k=k
    )

    print("Get questions/resources, time=",time.time())

    # 2) parse SMART Goals from the full_response blob
    goals = []
    m = re.search(r"SMART Goals:\s*(.*?)\n(Questions|Goals|Steps)", full_response, flags=re.DOTALL)

    if m:
        section = m.group(1).strip()
        for line in section.splitlines():
            text = line.strip().lstrip("•").strip()
            if text:
                goals.append(text)

    # 3) First, include the RAG-based hits from external_resources
    resources = []
    resources.append(external_resources)
    m = re.search(
        r'Resources[\s\S]*?:\s*\n([\s\S]*)',
        full_response
    )

    if m:
        section = m.group(1).strip()
        for line in section.splitlines():
            text = line.strip().lstrip("•").strip()
            if text:
                resources.append(text)

    # 4) Then append the “Additional Resources” parsed from the raw prompt
    addl = format_additional_resources(raw_prompt, max_items=k)
    for r in addl:
        label = r.get("name", "")
        url   = r.get("url", "")
        act   = r.get("action", "")
        # Bold name, link and action on separate lines
        entry = f"**{label}**  \n"
        if url:
            entry += f"[Link]({url})  \n"
        if act:
            entry += f"**Action:** {act}"
        resources.append(entry)
    print("Parsing, time=",time.time())

    return goals, resources, full_response, external_resources, raw_prompt


#NEW PLANNER APPROACH
def construct_response(situation, all_messages, model, organization,full_response, external_resources, raw_prompt):
    """
    1) Ask the model: is this a substantive request that needs SMART goals?
       -> JSON: {"needs_goals": true/false}
    2a) If false: one-shot vanilla chat (no goals).
    2b) If true: your existing SMART-goals + orchestration pipeline.
    """

    print("Intent Checker 2 {}".format(time.time()))
    # -- 1) INTENT & verbosity CHECK tiny LLM call --
    intent_and_verbosity_msgs = [
    {
        "role": "system",
        "content": (
            "You’re a request analyzer.  "
            "Given one user message, answer **strictly** in JSON with two keys:\n"
            '  • "needs_goals": true if they want advice or help or concrete next steps;\n'
            '  • "verbosity": one of "brief","medium","deep", chosen based on how much detail they implicitly want.\n'
            "\n"
            "Examples:\n"
            '- User: "How are you?" → { "needs_goals": false, "verbosity": "brief" }\n'
            '- User: "I’m struggling to pay rent, please help me." → { "needs_goals": true, "verbosity": "medium" }\n'
            '- User: "I need a detailed plan to switch careers and build new skills." → { "needs_goals": true, "verbosity": "deep" }\n'
            "Return only valid JSON, no extra commentary."
        )
    },
    {"role": "user", "content": situation}
    ]
    meta_resp = call_chatgpt_api_all_chats(
        intent_and_verbosity_msgs,
        stream=False,
        max_tokens=40
    ).strip()

    print("Resources {}".format(external_resources))

    try:
        meta = json.loads(meta_resp)
        needs_goals = meta.get("needs_goals", False)
        verbosity   = meta.get("verbosity", "medium")
    except:
        needs_goals = False
        verbosity   = "medium"

    # TODO: Think about whether this is needed/or to remove this
    needs_goals = True 
    verbosity = "medium"

    print(f"[DEBUG] needs_goals={needs_goals}, verbosity={verbosity}, time={time.time()}")

    # -- 2a) if it's just small talk, do a pure chat reply --
    if not needs_goals:
        print("[DEBUG] taking small‐talk branch")
        chat_msgs = (
            [{"role": "system", "content":
              f"You are a helpful assistant for {organization}. Reply warmly and concisely."}]
            + all_messages
            + [{"role": "user", "content": situation}]
        )
        # STREAM the response back
        chat_resp = call_chatgpt_api_all_chats(chat_msgs, stream=True, max_tokens=500)
        yield from stream_process_chatgpt_response(chat_resp)
        return


    # If they implicitly want just the headlines…
    if verbosity == "brief":
        print("[DEBUG] taking brief GOALS branch")
        prompt = (
            f"You are a concise assistant for {organization}.  "
            "Given the user’s request, produce **up to three** SMART goals as bullet points, "
            "each in one short sentence, tailored exactly to their situation."
        )
        msgs = [{"role":"system","content":prompt}] + all_messages + [{"role":"user","content":situation}]
        yield from stream_process_chatgpt_response(
            call_chatgpt_api_all_chats(msgs, stream=True, max_tokens=20)
        )
        return

    # If they want the full orchestration…
    if verbosity == "deep":
        print("[DEBUG] verbosity=deep → using full orchestration with k=50")
        full_k = 50
    else: 
        print("[DEBUG] verbosity=medium → using standard orchestration with k=5")
        full_k = 5


    # -- 2b) otherwise: we run our full SMART-goals + orchestration pipeline --

    # retaining the 'chatgpt' vs 'copilot' modes branch:
    if model == 'chatgpt':
        print("[DEBUG] model=chatgpt branch")
        msgs = (
            [{'role': 'system', 'content':
              f"You are a Co-Pilot tool for {organization}, a peer-peer support org."}]
            + all_messages
            + [{'role': 'user', 'content': situation}]
        )
        resp = call_chatgpt_api_all_chats(msgs, max_tokens=750)
        yield from stream_process_chatgpt_response(resp)
        return

    # the existing copilot pipeline:
    print("[DEBUG] copilot pipeline branch (SMART goals + orchestration), time=",time.time())
    initial_response = full_response 

    print("Initial Response {}".format(initial_response))

    print("Get questions, resource time={}".format(time.time()))


    new_message = [{'role': 'system', 'content': internal_prompts['orchestration']}]
    new_message += [{'role': 'system', 'content': external_resources}]
    new_message += all_messages + [
        {"role": "user",    "content": situation},
        {"role": "user",    "content": initial_response}
    ]

    print("Streaming Main Orchestration, Time {}".format(time.time()))
    # 1) stream the main orchestration 
    response = call_chatgpt_api_all_chats(new_message, stream=True, max_tokens=1000)
    yield from stream_process_chatgpt_response(response)




def extract_resources(embedding_model, saved_indices, documents, situation, which_indices, k=25):
    """Given a string and external resource config, retrieve most similar lines."""
    ret = []

    for i in which_indices:
        if which_indices[i]:
            query_embedding = embedding_model.encode(situation, convert_to_tensor=False)
            _, I = saved_indices[i].search(np.array([query_embedding]), k=k)
            ret += [documents[i][j] for j in I[0] if j < len(documents[i])]  
    return "\n".join(ret)




def get_benefit_demographics(user_input,all_messages):
    """Extract information from a user's input
    
    Arguments:
        user_input: Current user situation
        all_messages: All the previous messages
        
    Returns: Response, which is the extracted information"""

    new_messages = [{'role': 'system', 'content': internal_prompts['benefit_extract']}] + all_messages
    new_messages.append({'role': 'user', 'content': user_input})
    extracted_info = call_chatgpt_api_all_chats(new_messages,stream=False).strip()
    return extracted_info

def get_benefit_eligibility(situation,all_messages):
    """Given a situation and all the messages, get info on their benefits
    
    Arguments:
        situation: String, the user's current situation
        all_messages: List of previous messages
    
    Returns: String, info on their current benefit eligibilities"""
    
    extracted_info = get_benefit_demographics(situation,all_messages)

    pattern = r"\[Situation\](.*?)\[/Situation\]"
    eligibility_info = re.sub(
        pattern,
        lambda m: eligibility_check(m.group()),  # Pass the matched content as a string
        extracted_info,
        flags=re.DOTALL
    )
 
    return eligibility_info
