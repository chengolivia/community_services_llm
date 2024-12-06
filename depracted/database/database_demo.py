import tkinter as tk
from tkinter import ttk, scrolledtext 
import sounddevice as sd
import numpy as np
import wavio
import speech_recognition as sr
from fpdf import FPDF
from extract_resources import analyze_situation_rag, analyze_situation, translate_with_gpt

# Constants
SAMPLE_RATE = 16000  # Sampling rate for audio recording
is_recording = False
audio_data = []

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
            current_text = situation_input.get("1.0", tk.END).strip()
            new_text = current_text + " " + voice_text if current_text else voice_text
            
            # Populate the input field with the updated text
            situation_input.delete("1.0", tk.END)
            situation_input.insert(tk.END, new_text)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")

# Function to handle text analysis
def handle_analyze():
    situation = situation_input.get("1.0", tk.END).strip()  # Get the input situation
    csv_file_path = "data/all_resources.csv"
    if situation:
        response = analyze_situation_rag(situation, csv_file_path)
        
        # Append the new response to the existing content
        existing_text = result_output.get("1.0", tk.END).strip()
        updated_text = existing_text + "\n\nUser: " + situation + "\n" + "\nCo-Pilot: " + response
        result_output.delete("1.0", tk.END)  # Clear previous output
        result_output.insert(tk.END, updated_text)  # Insert updated text

        # Adjust the height dynamically based on the number of lines
        num_lines = updated_text.count("\n") + 1
        result_output.config(height=min(max(num_lines, 10), 30))

def handle_translate():
    language = language_var.get()
    original_text = result_output.get("1.0", tk.END).strip()
    
    if not original_text:
        translated_output.delete("1.0", tk.END)
        translated_output.insert(tk.END, "No text to translate.")
        return

    if language:
        translated_text = translate_with_gpt(original_text, language)
        translated_output.delete("1.0", tk.END)
        translated_output.insert(tk.END, translated_text)

def export_to_pdf():
    recommended_resources = result_output.get("1.0", tk.END).strip()
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
        
# Create the main window
window = tk.Tk()
window.title("Resource Recommendation System")
window.configure(bg="#2C2C2C")  # Dark background color

# Header
header_label = tk.Label(window, text="Resource Recommendation System", font=("Helvetica", 14, "bold"), bg="#2C2C2C", fg="white")
header_label.pack(pady=10)

# Frame for input and buttons
frame = tk.Frame(window, bg="#2C2C2C")
frame.pack(pady=10)

# Input Label and Text Box
situation_label = tk.Label(frame, text="Enter Situation:", font=("Helvetica", 12), bg="#2C2C2C", fg="white")
situation_label.grid(column=0, row=0, padx=10, pady=5, sticky="w")

situation_input = tk.Text(frame, height=5, width=50, font=("Helvetica", 10), bg="#3C3C3C", fg="white", insertbackground="white")
situation_input.grid(column=0, row=1, padx=10, pady=(0, 10), sticky="w")

# Buttons
start_button = tk.Button(frame, text="Start Recording", command=start_recording, bg="#4B4B4B", fg="black", relief="flat")
start_button.grid(column=0, row=2, padx=10, pady=5, sticky="w")

stop_button = tk.Button(frame, text="Stop Recording", command=stop_recording, bg="#4B4B4B", fg="black", relief="flat")
stop_button.grid(column=0, row=3, padx=10, pady=5, sticky="w")

analyze_button = tk.Button(frame, text="Analyze", command=handle_analyze, bg="#4B4B4B", fg="black", relief="flat")
analyze_button.grid(column=0, row=4, padx=10, pady=5, sticky="w")

# Output Label and ScrolledText
result_label = tk.Label(window, text="Recommended Resources:", font=("Helvetica", 12), bg="#2C2C2C", fg="white")
result_label.pack(pady=5)

result_output = scrolledtext.ScrolledText(window, height=10, width=60, font=("Helvetica", 10), bg="#3C3C3C", fg="white", insertbackground="white")
result_output.pack(padx=10, pady=5)

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


# Start the main loop
window.mainloop()