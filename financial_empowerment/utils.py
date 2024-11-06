import openai
import PyPDF2


def call_chatgpt_api(system_prompt,prompt):
    """Run ChatGPT with the 4o-mini model for a system prompt
    
    Arguments:
        system_prompt: String, what the main system prompt is
            Tells ChatGPT the general scenario
        prompt: Specific promt for ChatGPT

    Returns: String, result from ChatGPT"""

    if openai.__version__ in ['1.44.0','1.53.0']:
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


def call_chatgpt_api_all_chats(all_chats):
    """Run ChatGPT with the 4o-mini model for a system prompt
    
    Arguments:
        system_prompt: String, what the main system prompt is
            Tells ChatGPT the general scenario
        prompt: Specific promt for ChatGPT

    Returns: String, result from ChatGPT"""

    if openai.__version__ in ['1.44.0','1.53.0']:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  
            messages=all_chats,
        )
    else:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  
            messages=all_chats,
        )
    return response.choices[0].message.content.strip()

def extract_text_from_pdf(pdf_file_path):
    """Extract some text from a PDF file path
    
    Arguments:
        pdf_file_path: String, location to the PDF file
        
    Returns: String, all the text in the file"""

    with open(pdf_file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
