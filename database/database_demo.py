import tkinter as tk
from tkinter import scrolledtext
import pandas as pd
import openai

openai.api_key = 'sk-vcluRbh8_Y_LTW4rYNJZ_OIe0AG5iZOKBaj99sEmn0T3BlbkFJmyNWqmOrh3BkZ-YrMHcyuzUgCU26oHqPNhGTPo3LAA'

system_prompt = "You are a helpful assistant that recommends appropriate hotline services based on the given situation. You will analyze the list of available hotlines and select the most suitable one for each user query, providing the hotline name, phone number, and a reason for the choice."

def create_prompt(situation, hotlines_df):
    services = ", ".join(hotlines_df["Service"].tolist())
    prompt = f"""
    I have a list of hotline services: {services}. Based on the situation "{situation}", which hotlines should I call? 
    Return a few appropriate hotline names, number, and why they are the appropriate choices for this situation. Make sure you provide more than one hotline if they can help even just a little.
    """
    return prompt

def call_chatgpt_api(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o",  
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response['choices'][0]['message']['content'].strip()

def analyze_situation(situation, csv_file_path):
    hotlines_df = pd.read_csv(csv_file_path)
    prompt = create_prompt(situation, hotlines_df)   
    response = call_chatgpt_api(prompt)
    return response

# Function to handle button click and update the output
def handle_analyze():
    situation = situation_input.get("1.0", tk.END).strip()  # Get the input situation
    csv_file_path = "enhanced_hotlines.csv"
    if situation:
        response = analyze_situation(situation, csv_file_path)
        result_output.delete("1.0", tk.END)  # Clear previous output
        result_output.insert(tk.END, response)  # Insert new response
        
        num_lines = response.count("\n") + 1
        result_output.config(height=min(max(num_lines, 10), 30))
        

# Create the main window
window = tk.Tk()
window.title("Hotline Recommendation System")

# Configure the grid layout to expand as the window is resized
window.grid_columnconfigure(0, weight=1)
window.grid_rowconfigure(1, weight=1)
window.grid_rowconfigure(4, weight=1)

# Create a label for the input box
situation_label = tk.Label(window, text="Enter Situation:")
situation_label.grid(column=0, row=0, padx=10, pady=10, sticky="n")

# Create a text input box for the situation
situation_input = tk.Text(window, height=5, width=50)
situation_input.grid(column=0, row=1, padx=10, pady=10, sticky="nsew")

# Create a button to analyze the situation
analyze_button = tk.Button(window, text="Analyze", command=handle_analyze)
analyze_button.grid(column=0, row=2, padx=10, pady=10, sticky="n")

# Create a label for the output box
result_label = tk.Label(window, text="Recommended Hotlines:")
result_label.grid(column=0, row=3, padx=10, pady=10, sticky="n")

# Create a scrolled text output box to display the response
result_output = scrolledtext.ScrolledText(window, height=10, width=50)
result_output.grid(column=0, row=4, padx=10, pady=10, sticky="nsew")

# Adjusting the grid rows and columns to stretch based on window size
window.grid_rowconfigure(1, weight=1)  # Input text area stretches
window.grid_rowconfigure(4, weight=1)  # Output text area stretches
window.grid_columnconfigure(0, weight=1)  # All elements centered and expand horizontally

# Start the main loop
window.mainloop()

