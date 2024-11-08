import tkinter as tk
from tkinter import scrolledtext
from extract_resources import analyze_situation_rag, analyze_situation

def handle_analyze():
    situation = situation_input.get("1.0", tk.END).strip()  # Get the input situation
    csv_file_path = "data/enhanced_resources.csv"
    if situation:
        response = analyze_situation_rag(situation, csv_file_path)
        result_output.delete("1.0", tk.END)  # Clear previous output
        result_output.insert(tk.END, response)  # Insert new response
        
        num_lines = response.count("\n") + 1
        result_output.config(height=min(max(num_lines, 10), 30))
        

# Create the main window
window = tk.Tk()
window.title("Resource Recommendation System")

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
result_label = tk.Label(window, text="Recommended Resources:")
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

