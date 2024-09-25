import openai 
openai.api_key = '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'
first_prompt = prompt = "At each iteration, tell me what my name is; sometimes I will tell you what my name is (and update it over time), and sometimes I will tell you other information. To begin with, my name is John"
system_prompt = "You are a highly knowledgeable, patient, and helpful assistant that specializes in collecting user information and evaluating eligibility \
                for various social and financial benefits. Your goal is to guide the user through the process, ensuring they provide clear and accurate answers. \
                Be polite and professional in your responses. If a user’s input is unclear or incomplete, ask follow-up questions to gather the necessary details. \
                Always provide additional explanations or examples if the user appears confused. If a question involves complex terms, offer simple definitions to ensure the user understands"

def feed_chatgpt(responses):
    response = openai.chat.completions.create(model="gpt-3.5-turbo",
    messages=responses,max_tokens=150)

    return response.choices[0].message.content.strip()

all_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]

for i in range(10):
    a = input("> ")
    all_messages.append({"role": 'user', "content": a})

    response = feed_chatgpt(all_messages)
    all_messages.append({'role': 'assistant', 'content': response})
    print("ChatGPT: {}".format(response))