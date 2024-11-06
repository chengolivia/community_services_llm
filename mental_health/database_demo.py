import tkinter as tk
from tkinter import scrolledtext
from extract_resources import analyze_situation
import sounddevice as sd
import wavio
import speech_recognition as sr
from utils import read_text, write_text_pdf

all_messages = []
def handle_analyze(all_messages):
    """When the analyze button is pressed, analyze the message + update the text boxes
    
    Arguments:
        all_messages: The list of all messages, back-and-forth convo
    
    Returns: Nothing
    
    Side Effects: Runs the last message through ChatGPT"""
    situation = situation_input.get("1.0", tk.END).strip()  # Get the input situation
    if situation:
        response = analyze_situation(situation,all_messages)
        all_messages.append({"role": "system", "content": response})
        situation_input.delete("1.0", tk.END)  # Clear previous input
        result_output.insert(tk.END, "User: " +str(situation)+"\n\n")  # Insert new response
        result_output.insert(tk.END, "Co-Pilot: " +str(response)+"\n\n")  # Insert new response        

def handle_read_last():
    """When the read button is pressed, read outloud the last message
    
        Arguments: None
        
        Returns: Nothing
        
        Side Effects: Reads the last message"""

    if len(all_messages)>0:
        last_message = all_messages[-1]['content']
        read_text(last_message)

def handle_save():
    """When the save button is pressed, save all the messages
    
        Arguments: None
        
        Returns: Nothing
        
        Side Effects: Saves all the data"""

    write_text_pdf(result_output.get("1.0", tk.END).strip(),"data/all_messages.pdf")

# Create the main window
window = tk.Tk()
window.title("Activity Suggestion Tool")

# Configure the grid layout to expand as the window is resized
window.grid_columnconfigure(0, weight=1)
window.grid_rowconfigure(1, weight=1)
window.grid_rowconfigure(4, weight=1)

# Create a label for the input box
situation_label = tk.Label(window, text="Enter Situation + Goal:")
situation_label.grid(column=0, row=0, padx=10, pady=10, sticky="n")

# Create a text input box for the situation
situation_input = tk.Text(window, height=5, width=25)
situation_input.grid(column=0, row=1, padx=10, pady=10, sticky="nsew")

# Create a button to analyze the situation
analyze_button = tk.Button(window, text="Analyze", command=lambda: handle_analyze(all_messages))
analyze_button.grid(column=0, row=2, padx=10, pady=10, sticky="n")

read_button = tk.Button(window, text="Read Last Message", command=handle_read_last)
read_button.grid(column=1, row=2, padx=10, pady=10, sticky="n")

save_button = tk.Button(window, text="Save text", command=handle_save)
save_button.grid(column=2, row=2, padx=10, pady=10, sticky="n")

# Create a label for the output box
result_label = tk.Label(window, text="Recommended Activities:")
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

