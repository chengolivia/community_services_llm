import concurrent.futures
import openai
import time 

openai.api_key = "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"

def generate_text(prompt):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=50
    )
    return response.choices[0].message.content

prompts = [
    "Write a poem about a cat.",
    "Tell me a joke.",
    "Generate a random fact."
]

start = time.time()
with concurrent.futures.ThreadPoolExecutor() as executor:
    results = executor.map(generate_text, prompts)


print("Took {} time".format(time.time()-start))