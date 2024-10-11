import openai
import tkinter as tk
from tkinter import scrolledtext
import PyPDF2

# Set up your OpenAI API key here
openai.api_key = 'sk-vcluRbh8_Y_LTW4rYNJZ_OIe0AG5iZOKBaj99sEmn0T3BlbkFJmyNWqmOrh3BkZ-YrMHcyuzUgCU26oHqPNhGTPo3LAA'

# Single variable to store the PDF file path
pdf_file_path = 'Benefits & Eligibility.pdf'

# Extract text from PDF function
def extract_text_from_pdf(pdf_file_path):
    with open(pdf_file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

# LLM API call to extract eligibility information from user input
def call_llm_extract(user_input, pdf_text):
    prompt = f"Extract the relevant personal information from the following user input and present it in a structured format. Pay attention to the attributes that are mention in the text :{pdf_text} Here is just an example of the structure. You may extract additional attributes if you see fit: \n" \
             f"Age: [extracted value]\n" \
             f"Monthly Income: [extracted value]\n" \
             f"Resources: [extracted value]\n" \
             f"Disability Status: [extracted value]\n" \
             f"Family Status: [extracted value]\n" \
             f"Here is the user input: {user_input}"
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    extracted_info = response['choices'][0]['message']['content'].strip()
    return extracted_info


# LLM API call to update the extracted information
def call_llm_update(original_info, update_request, pdf_text):
    prompt = f"Please read the following text extracted from a pdf file :{pdf_text} containing benefits and eligibility criteria. \n" \
             f"Original information: {original_info} \n" \
             f"User update request: {update_request} \n" \
             f"Please update the original information based on the request and present it in a structured format."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    updated_info = response['choices'][0]['message']['content'].strip()
    return updated_info

# LLM API call to check eligibility for benefits based on extracted information
def call_llm_check_eligibility(extracted_info, pdf_text):
    prompt = f"Please read the following text extracted from a pdf file :{pdf_text} containing benefits and eligibility criteria. \n" \
             f"Based on the extracted user information: {extracted_info}, \n" \
             f"Determine if the user is 100% eligible, likely eligible, maybe eligible, or not eligible for any benefits. Provide the reasoning for each in the following structure:\n" \
             f"- 100% eligible:\n[List of benefits]\n" \
             f"- Likely eligible:\n[List of benefits and missing requirements]\n" \
             f"Reason: [Explanation of the missing requirement(s)]\n" \
             f"- Maybe eligible:\n[List of benefits and partially met requirements]\n" \
             f"Reason: [Explanation of partially met requirements]\n" \
             f"- Not eligible:\n[List of benefits and unmet requirements]\n" \
             f"Reason: [Explanation of unmet requirements]."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    eligibility_info = response['choices'][0]['message']['content'].strip()
    return eligibility_info

# Function to dynamically adjust the size of the text fields
def adjust_text_field_size(text_widget, content):
    num_lines = content.count('\n') + 1  # Count the number of lines in the content
    max_lines = 15  # Define a maximum number of lines to prevent the text field from growing too large
    widget_height = min(num_lines, max_lines)  # Set the height based on the number of lines
    text_widget.config(height=widget_height)

# Function to extract information from the input text and adjust field size
def extract_info():
    user_input = input_field.get("1.0", tk.END).strip()
    pdf_text = extract_text_from_pdf(pdf_file_path)
    extracted_info = call_llm_extract(user_input, pdf_text)
    
    output_field_1.config(state=tk.NORMAL)
    output_field_1.delete(1.0, tk.END)
    output_field_1.insert(tk.END, extracted_info)
    
    # Adjust the text field size based on the extracted content
    adjust_text_field_size(output_field_1, extracted_info)
    
    output_field_1.config(state=tk.DISABLED)

# Function to update the extracted information and adjust field size
def update_info():
    original_info = output_field_1.get("1.0", tk.END).strip()
    update_request = update_field.get("1.0", tk.END).strip()
    pdf_text = extract_text_from_pdf(pdf_file_path)
    updated_info = call_llm_update(original_info, update_request, pdf_text)
    
    output_field_1.config(state=tk.NORMAL)
    output_field_1.delete(1.0, tk.END)
    output_field_1.insert(tk.END, updated_info)
    
    # Adjust the text field size based on the updated content
    adjust_text_field_size(output_field_1, updated_info)
    
    output_field_1.config(state=tk.DISABLED)

# Function to check eligibility and adjust field size
def check_eligibility():
    extracted_info = output_field_1.get("1.0", tk.END).strip()
    pdf_text = extract_text_from_pdf(pdf_file_path)
    eligibility_info = call_llm_check_eligibility(extracted_info, pdf_text)
    
    eligibility_output.config(state=tk.NORMAL)
    eligibility_output.delete(1.0, tk.END)
    eligibility_output.insert(tk.END, eligibility_info)
    
    # Adjust the text field size based on the eligibility content
    adjust_text_field_size(eligibility_output, eligibility_info)
    
    eligibility_output.config(state=tk.DISABLED)


# Set up the main application window
window = tk.Tk()
window.title("Benefit Eligibility Checker")

# Input field for user input (e.g., conversation or self-introduction)
input_label = tk.Label(window, text="Enter your information:")
input_label.pack()

input_field = scrolledtext.ScrolledText(window, height=5, width=60)
input_field.pack()

# Button to extract information
extract_button = tk.Button(window, text="Extract", command=extract_info)
extract_button.pack()

# Output field 1 to display extracted information
output_label_1 = tk.Label(window, text="Extracted Information:")
output_label_1.pack()

output_field_1 = scrolledtext.ScrolledText(window, height=5, width=60, state=tk.DISABLED)
output_field_1.pack()

# Update field for users to input corrections
update_label = tk.Label(window, text="Update Information (if necessary):")
update_label.pack()

update_field = scrolledtext.ScrolledText(window, height=2, width=60)
update_field.pack()

# Button to update the information
update_button = tk.Button(window, text="Update", command=update_info)
update_button.pack()

# Button to check eligibility
check_eligibility_button = tk.Button(window, text="Check Eligibility", command=check_eligibility)
check_eligibility_button.pack()

# Output field to display eligibility results
eligibility_label = tk.Label(window, text="Eligibility Results:")
eligibility_label.pack()

eligibility_output = scrolledtext.ScrolledText(window, height=10, width=60, state=tk.DISABLED)
eligibility_output.pack()

# Run the GUI application
window.mainloop()
