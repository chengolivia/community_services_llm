import tkinter as tk
from tkinter import scrolledtext
from utils import extract_text_from_pdf
from eligible_benefits import call_llm_check_eligibility
from extract_information import call_llm_update, call_llm_extract, translate_with_gpt
from python_constraint_checker import eligibility_check
import numpy as np
import sounddevice as sd
import wavio
from fpdf import FPDF
import speech_recognition as sr

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
    extracted_info = call_llm_extract(user_input)

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
    # pdf_text = extract_text_from_pdf(pdf_file_path)
    
    # eligibility_info = call_llm_check_eligibility(extracted_info, pdf_text)
    
    eligibility_info = eligibility_check(extracted_info)
    
    eligibility_output.config(state=tk.NORMAL)
    eligibility_output.delete(1.0, tk.END)
    eligibility_output.insert(tk.END, eligibility_info)
    
    # Adjust the text field size based on the eligibility content
    adjust_text_field_size(eligibility_output, eligibility_info)
    
    eligibility_output.config(state=tk.DISABLED)
    
# Parameters for recording
SAMPLE_RATE = 16000  # Sample rate in Hz
audio_data = []  # Initialize a list to store audio chunks
is_recording = False  # Flag to track recording state

# Function to handle the start of recording
def start_recording():
    global is_recording, audio_data
    is_recording = True
    audio_data = []  # Reset the audio data list

    def callback(indata, frames, time, status):
        if is_recording:
            audio_data.append(indata.copy())  # Store audio chunks

    # Open the input stream
    stream = sd.InputStream(callback=callback, channels=1, samplerate=SAMPLE_RATE, dtype='int16')
    stream.start()
    
    # Store the stream in the global context to stop it later
    window.audio_stream = stream
    print("Recording started...")

# Function to handle the stop of recording
def stop_recording():
    global is_recording
    is_recording = False
    print("Recording stopped.")
    
    # Stop the audio stream
    if hasattr(window, 'audio_stream'):
        window.audio_stream.stop()
        window.audio_stream.close()
    
    # Convert the audio data to a NumPy array and save it
    if audio_data:
        full_audio_data = np.concatenate(audio_data)
        wavio.write("temp_audio.wav", full_audio_data, SAMPLE_RATE, sampwidth=2)
        transcribe_audio()

# Function to transcribe the recorded audio
def transcribe_audio():
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile("temp_audio.wav") as source:
            audio = recognizer.record(source)
            voice_text = recognizer.recognize_google(audio)
            print(f"Voice input captured: {voice_text}")
            
            # Append the transcribed voice input to the existing content in the input field
            current_text = input_field.get("1.0", tk.END).strip()
            new_text = current_text + " " + voice_text if current_text else voice_text
            
            # Populate the input field with the updated text
            input_field.delete("1.0", tk.END)
            input_field.insert(tk.END, new_text)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        
def handle_translate():
    language = language_var.get()
    original_text = eligibility_output.get("1.0", tk.END).strip()
    
    if not original_text:
        translated_output.delete("1.0", tk.END)
        translated_output.insert(tk.END, "No text to translate.")
        return

    if language:
        translated_text = translate_with_gpt(original_text, language)
        translated_output.delete("1.0", tk.END)
        translated_output.insert(tk.END, translated_text)

def export_to_pdf():
    recommended_resources = eligibility_output.get("1.0", tk.END).strip()
    translated_text = translated_output.get("1.0", tk.END).strip()
    
    if not recommended_resources and not translated_text:
        print("No content to export.")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Exported Results", ln=True, align="C")
    
    if recommended_resources:
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 10, txt="Recommended Resources:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=recommended_resources)
        pdf.ln(5)
    
    if translated_text:
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 10, txt="Translated Output:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, txt=translated_text)
    
    pdf_output_path = "exported_results.pdf"
    pdf.output(pdf_output_path)
    print(f"Results exported to {pdf_output_path}.")


# Set up the main application window
window = tk.Tk()
window.title("Benefit Eligibility Checker")

# Input field for user input (e.g., conversation or self-introduction)
input_label = tk.Label(window, text="Enter client's information:")
input_label.pack()

input_field = scrolledtext.ScrolledText(window, height=5, width=60)
input_field.pack()

# Add the "Start Recording" button to the GUI
start_button = tk.Button(window, text="Start Recording", command=start_recording)
start_button.pack()

# Add the "Stop Recording" button to the GUI
stop_button = tk.Button(window, text="Stop Recording", command=stop_recording)
stop_button.pack()

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

# Language Selection Dropdown
language_frame = tk.Frame(window, bg="#2C2C2C")
language_frame.pack(pady=10)

language_label = tk.Label(language_frame, text="Select Language for Translation:", font=("Helvetica", 12), bg="#2C2C2C", fg="white")
language_label.grid(column=0, row=0, padx=10, pady=5, sticky="w")

language_var = tk.StringVar()
language_dropdown = tk.OptionMenu(language_frame, language_var, "Spanish", "French", "German", "Chinese", "Japanese")
language_dropdown.config(bg="#4B4B4B", fg="white", relief="flat")
language_dropdown.grid(column=1, row=0, padx=10, pady=5)

# Translate Button
translate_button = tk.Button(language_frame, text="Translate", command=handle_translate, bg="#4B4B4B", fg="black", relief="flat")
translate_button.grid(column=2, row=0, padx=10, pady=5)

# Translated Output Label and ScrolledText
translated_label = tk.Label(window, text="Translated Output:", font=("Helvetica", 12), bg="#2C2C2C", fg="white")
translated_label.pack(pady=5)

translated_output = scrolledtext.ScrolledText(window, height=10, width=60, font=("Helvetica", 10), bg="#3C3C3C", fg="white", insertbackground="white")
translated_output.pack(padx=10, pady=5)

# Export button
export_button = tk.Button(window, text="Export Current Results", command=export_to_pdf, bg="#4B4B4B", fg="black", relief="flat")
export_button.pack(pady=10)
# Run the GUI application
window.mainloop()
