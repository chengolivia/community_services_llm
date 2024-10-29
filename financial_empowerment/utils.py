import openai
import PyPDF2

required_version = "0.28.0"
if openai.__version__ != required_version:
    raise ImportError(f"OpenAI version {required_version} is required, but version {openai.__version__} is installed.")

def call_chatgpt_api(system_prompt,prompt):
    """Run ChatGPT with the 4o-mini model for a system prompt
    
    Arguments:
        system_prompt: String, what the main system prompt is
            Tells ChatGPT the general scenario
        prompt: Specific promt for ChatGPT

    Returns: String, result from ChatGPT"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
    )
    return response['choices'][0]['message']['content'].strip()

def call_chatgpt_api_all_chats(all_chats):
    """Run ChatGPT with the 4o-mini model for a system prompt
    
    Arguments:
        system_prompt: String, what the main system prompt is
            Tells ChatGPT the general scenario
        prompt: Specific promt for ChatGPT

    Returns: String, result from ChatGPT"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  
        messages=all_chats
    )
    return response['choices'][0]['message']['content'].strip()

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
