import tkinter as tk
from tkinter import scrolledtext
from utils import extract_text_from_pdf
from eligible_benefits import call_llm_check_eligibility
from extract_information import call_llm_update, call_llm_extract

pdf_file_path = 'assets/benefits.pdf'

def adjust_text_field_size(text_widget, content):
    """Adjust the text field size based on the input
    
    Arguments:
        text_Width: Which thing we're trying to adjust
        content: String, the multi-line content
    
    Returns: Nothing
    
    Side Effects: Resizes text_widget"""

    num_lines = content.count('\n') + 1  # Count the number of lines in the content
    max_lines = 15  # Define a maximum number of lines to prevent the text field from growing too large
    widget_height = min(num_lines, max_lines)  # Set the height based on the number of lines
    text_widget.config(height=widget_height)

# Function to extract information from the input text and adjust field size
def extract_info():
    """Get the information and extract it via LLM
    
    Arguments: None
    
    Returns: None
    
    Side Effects: Calls the LLM to extract information"""

    user_input = input_field.get("1.0", tk.END).strip()
    pdf_text = extract_text_from_pdf(pdf_file_path)
    extracted_info = call_llm_extract(user_input, pdf_text)
    
    output_field_1.config(state=tk.NORMAL)
    output_field_1.delete(1.0, tk.END)
    output_field_1.insert(tk.END, extracted_info)
    
    # Adjust the text field size based on the extracted content
    adjust_text_field_size(output_field_1, extracted_info)
    
    output_field_1.config(state=tk.DISABLED)

def update_info():
    """Update the information from a user prompt
    
    Arguments: None
    
    Returns: None
    
    Side Effects: Calls the LLM to update the info"""

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
    """Checks the eligiblity via an LLM
    
    Arguments: None
    
    Returns: None
    
    Side Effects: Call the check eligibility and update the info"""

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
