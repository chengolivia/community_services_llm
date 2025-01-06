import openai 
from utils import *
from secret import gao_key as key 
from typing import Dict, Optional, List
import re
import ast
import inspect
import time 


openai.api_key = key

system_prompt = open("benefits/prompts/system_prompt.txt").read()

def eligibility_check(user_info: Dict[str, Optional[int]]) -> str:
    """
    Determines eligibility for various government benefits based on user information.
    Returns a formatted string with eligibility results and explanations.
    
    Parameters:
    user_info (dict): A dictionary containing user data (e.g., age, income, family status).

    Returns:
    str: Eligibility results with explanations for each benefit.
    """
    match = re.search(r"{.*}", user_info, re.DOTALL) 
    if match: cleaned_output = match.group(0) 
    
    if "}," in cleaned_output:
        cleaned_output = cleaned_output.split("},")
        cleaned_output[0] = cleaned_output[0] + "}"
        cleaned_output = [i.strip() for i in cleaned_output]
    else:
        cleaned_output = [cleaned_output]
    
    all_user_info = [ast.literal_eval(i) for i in cleaned_output]


    # Define benefit constraints with dynamic SSI conditions based on family and marital status
    benefit_constraints = {
        "SSI": {
            "single_adult": {
                "income": {"constraint": lambda income: income < 1971, "weight": 0.3, "description": "Income should be less than $1971 for single adults"},
                "non_work_income": {"constraint": lambda income: income < 963, "weight": 0.3, "description": "Non-work income should be less than $963 for single adults"},
                "resources": {"constraint": lambda resources: resources <= 2000, "weight": 0.2, "description": "Resources should be $2000 or less for individuals"}
            },
            "married_couple": {
                "income": {"constraint": lambda income: income < 2915, "weight": 0.3, "description": "Income should be less than $2915 for married couples"},
                "non_work_income": {"constraint": lambda income: income < 1435, "weight": 0.3, "description": "Non-work income should be less than $1435 for married couples"},
                "resources": {"constraint": lambda resources: resources <= 3000, "weight": 0.2, "description": "Resources should be $3000 or less for couples"}
            },
            "individual_parent_disabled_child": {
                "income": {"constraint": lambda income: income < 3897, "weight": 0.3, "description": "Income should be less than $3897 for an individual parent with a disabled child"},
                "non_work_income": {"constraint": lambda income: income < 1926, "weight": 0.3, "description": "Non-work income should be less than $1926 for an individual parent with a disabled child"},
                "resources": {"constraint": lambda resources: resources <= 2000, "weight": 0.2, "description": "Resources should be $2000 or less for individuals"}
            },
            "general": {
                "age_or_disability": {"constraint": lambda age, disability: age >= 65 or disability, "weight": 0.4, "description": "Age over 65 or has a disability"}
            }
        },
        "SSA": {
            "work_credits": {"constraint": lambda credits: credits >= 40, "weight": 0.5, "description": "Must have at least 40 work credits"},
            "age_for_retirement": {"constraint": lambda age: age >= 62, "weight": 0.3, "description": "Age 62 or older for early retirement benefits"}
        },
        "Medicare": {
            "eligibility_social_security": {"constraint": lambda eligible: eligible, "weight": 0.3, "description": "Eligible if they qualify for Social Security or Railroad Retirement benefits"},
            "age_or_work_history": {"constraint": lambda age, work_credits: age >= 65 or work_credits >= 40, "weight": 0.3, "description": "Age over 65 or eligible based on work history"},
            "disability_medical": {"constraint": lambda disability, condition: disability or condition in ['kidney_failure'], "weight": 0.3, "description": "Eligible based on disability or specific medical conditions like kidney failure"}
        },
        "SSDI": {
            "work_credits": {"constraint": lambda credits: credits >= 20, "weight": 0.4, "description": "At least 20 recent work credits"},
            "disability_prevents_sga": {"constraint": lambda disability, sga: disability and not sga, "weight": 0.3, "description": "Medical condition prevents substantial gainful activity"},
            "specific_condition": {"constraint": lambda condition: condition in ['terminal_illness', 'serious_condition'], "weight": 0.3, "description": "Eligible if diagnosed with a terminal or serious condition"}
        }
    }

    def categorize_eligibility(score: float) -> str:
        if score >= 90:
            return "Highly likely eligible"
        elif score >= 70:
            return "Likely eligible"
        elif score >= 40:
            return "Maybe eligible"
        else:
            return "Not eligible"

    def calculate_eligibility_score(user_info,benefit: str) -> Dict[str, any]:
        score = 0.0
        met_constraints: List[str] = []
        unmet_constraints: List[str] = []
        missing_constraints: List[str] = []

        # Select constraints based on family and marital status for SSI
        if benefit == "SSI":
            marital_status = user_info.get("marital_status", "single_adult")
            family_status = user_info.get("family_status", "general")
            constraints = benefit_constraints[benefit].get(family_status, benefit_constraints[benefit]["single_adult"])
            general_constraints = benefit_constraints[benefit]["general"]
        else:
            constraints = benefit_constraints.get(benefit, {})
            general_constraints = {}

        total_weight = sum(c["weight"] for c in constraints.values()) + sum(general_constraints[c]["weight"] for c in general_constraints)

        for criterion, data in {**constraints, **general_constraints}.items():
            constraint_func = data["constraint"]
            weight = data["weight"]
            description = data["description"]

            # Get the expected argument names for the constraint function
            expected_args = inspect.signature(constraint_func).parameters.keys()
            # Filter user_info to match the expected arguments for this constraint
            filtered_user_info = {arg: user_info.get(arg) for arg in expected_args}

            if any(value is None for value in filtered_user_info.values()):
                score += weight * 0.5
                missing_constraints.append(description)
            elif constraint_func(**filtered_user_info):
                score += weight
                met_constraints.append(description)
            else:
                unmet_constraints.append(description)

        normalized_score = score / total_weight * 100
        category = categorize_eligibility(normalized_score)

        return {
            "score": normalized_score,
            "category": category,
            "met_constraints": met_constraints,
            "unmet_constraints": unmet_constraints,
            "missing_constraints": missing_constraints
        }

    def generate_output(results: Dict[str, Dict[str, any]]) -> str:
        output = ""

        sorted_results = sorted(results.items(),key=lambda k: k[1]['score'],reverse=True)
        for benefit, result in sorted_results:
            output += f"Benefit: {benefit}\n"
            output += f"  Category: {result['category']}\n"
            output += f"  Met Constraints: {', '.join(result['met_constraints'])}\n"
            output += f"  Unmet Constraints: {', '.join(result['unmet_constraints'])}\n"
            output += f"  Missing Constraints: {', '.join(result['missing_constraints'])}\n\n"
        return output

    results = []
    for user_info in all_user_info:
        temp_result = {}
        for benefit in benefit_constraints.keys():
            temp_result[benefit] = calculate_eligibility_score(user_info,benefit)
        results.append(temp_result)
    outputs = [generate_output(r) for r in results]

    return str(user_info) + "\n" + "\n".join(outputs)

def call_llm_extract(user_input,all_messages):
    """Extract information from a user's input
    
    Arguments:
        user_input: What the user enters
        pdf_text: Information from the PDF, as text
        
    Returns: Response, which is the extracted information"""
    start = time.time()
    system_prompt = open("benefits/prompts/system_prompt_extract.txt").read()

    full_situation = "\n".join(["Message {} {}: ".format(idx+1,i['content']) for idx,i in enumerate([j for j in (all_messages+[{'role': 'user', 'content': user_input}]) if j['role'] == 'user'])])

    prompt = open("benefits/prompts/uncertain_prompt.txt").read().format(full_situation)

    new_messages = [{'role': 'system', 'content': system_prompt}] + all_messages
    new_messages.append({'role': 'user', 'content': prompt})
    print("Pre-GPT {}".format(time.time()-start))
    extracted_info = call_chatgpt_api_all_chats(new_messages,stream=False).strip()
    print("GPT {}".format)
    return extracted_info

def analyze_benefits_non_stream(situation, all_messages):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    extracted_info = call_llm_extract(situation,all_messages)

    eligibility_info = eligibility_check(extracted_info)

    prompt = (
        f"The center member is eligible for the following benefits {eligibility_info}"
        f"The last message is {situation}"
        "Can you respond with the following: "
        "1. If the center member is asking a question in the last message, please only answer the question; no need to state the benefit eligibilities"
        "2. If the center member is not asking a question, provide a nicely formatted version of the benefits, which states which things the center member MAY be eligible for, which things they're not, etc. and why not. Sort this from most likely eligible to least, and provide explanations as well. Also state what additional information might be helpful to determine eligibilities and why."
        "3. What additional information might be helpful to further help determine eligibilities"
        "4. Any next steps or links for applying for benefits. The SSI website is: https://www.ssa.gov/apply/ssi. The SSA website is: https://www.ssa.gov/apply. The medicare website is: https://www.ssa.gov/medicare/sign-up. You can apply for SSDI here: https://secure.ssa.gov/iClaim/dib. Can you state the type of documentation needed to apply as well"
        "Make sure you're conversational and as collegial as possible; note that all benefit programs should be addressed toward the center member, whom the provider is aiming to assist."
    )

    all_messages = [{'role': 'system', 'content': system_prompt}] + all_messages
    all_messages.append({'role': 'user', 'content': prompt})

    response = call_chatgpt_api_all_chats(all_messages,stream=False)
    all_messages = all_messages[1:-1]

    return response

def analyze_benefits(situation, all_messages,model):
    """Given a situation and a CSV, get the information from the CSV file
    Then create a prompt
    
    Arguments:
        situation: String, what the user requests
        csv_file_path: Location with the database
        
    Returns: A string, the response from ChatGPT"""

    if model == 'chatgpt':
        print("Using ChatGPT")
        all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for CSPNJ, a peer-peer mental health organization. Please provide information on benefit eligibility'}] + all_messages + [{'role': 'user', 'content': situation}]
        # Add a sleep time, so the time taken doesn't bias responses
        time.sleep(4)

        response = call_chatgpt_api_all_chats(all_message_list)

        for event in response:
            if event.choices[0].delta.content != None:
                current_response = event.choices[0].delta.content
                current_response = current_response.replace("\n","<br/>")
                yield "data: " + current_response + "\n\n"
        return 

    extracted_info = call_llm_extract(situation,all_messages)

    print("The extracted info is {}".format(extracted_info))


    pattern = r"\[Situation\](.*?)\[/Situation\]"
    eligibility_info = re.sub(
        pattern,
        lambda m: eligibility_check(situation, m.group()),  # Pass the matched content as a string
        extracted_info,
        flags=re.DOTALL
    )

    print("The client is eligible for {}".format(eligibility_check))

    constructed_messages = [{'role': 'system', 'content': system_prompt}] + all_messages
    constructed_messages.append({'role': 'user', 'content': 'Eligible Benefits: {}'.format(eligibility_info)})

    response = call_chatgpt_api_all_chats(constructed_messages,stream=True,max_tokens=500)
 
    for event in response:
        if event.choices[0].delta.content != None:
            current_response = event.choices[0].delta.content
            current_response = current_response.replace("\n","<br/>")
            yield "data: " + current_response + "\n\n"
