import openai

def call_chatgpt_api(system_prompt,prompt):
    """Run ChatGPT with the 4o-mini model for a system prompt
    
    Arguments:
        system_prompt: String, what the main system prompt is
            Tells ChatGPT the general scenario
        prompt: Specific promt for ChatGPT

    Returns: String, result from ChatGPT"""

    if openai.__version__[0] == '1':
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
        )
    else:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
        )
    return response.choices[0].message.content
