import tkinter as tk
from tkinter import ttk, messagebox
from extract_information import extract_information
from utils import call_chatgpt_api_all_chats
from eligible_benefits import get_eligible_benefits

system_prompt = open("prompts/system_prompt.txt").read()
chat_prompt = open("prompts/chat_prompt.txt").read()
all_chats = [{"role": "system", "content": system_prompt}, {"role": "system", "content": chat_prompt}]

def send_message():
    """Analyze the newest chat, and give a response
    
    Arguments: None
    
    Returns: Nothing
    
    Side Effects: Runs ChatGPT to analyze the message"""

    message = entry_box.get()
    if message:
        chat_box.config(state=tk.NORMAL)  # Enable writing to text box
        chat_box.insert(tk.END, "You: " + message + "\n")
        chat_box.config(state=tk.DISABLED)  # Disable text box to prevent user edits
        entry_box.delete(0, tk.END)  # Clear the entry box
        all_chats.append({'role': 'user', 'content': message})

        content = call_chatgpt_api_all_chats(all_chats)
        print(content)
        all_chats.append({'role': 'assistant', 'content': content})
        content = content.strip().split("\n")   
        content = [i.strip(",- ") for i in content]

        first_row = [idx for idx in range(len(content)) if 'age:' in content[idx].lower()]

        if len(first_row) == 0:
            other_content = "\n".join(content)
            info_content = ""
        else:
            other_content = "\n".join(content[:first_row[0]])
            info_content = "\n".join(content[first_row[0]:])

        chat_box.config(state=tk.NORMAL)  # Enable writing to text box
        chat_box.insert(tk.END, "LLM: " + other_content + "\n")
        chat_box.config(state=tk.DISABLED)  # Disable text box to prevent user edits

        if len(info_content) > 0:
            fill_form_with_extracted_info(extract_information(info_content))



# Function to fill the form with extracted data
def fill_form_with_extracted_info(extracted_info):
    """Given a list of extracted data, fill out the form with it
    
    Arguments:
        extracted_info: Dictionary with information on different fields
        
    Returns: Nothing
    
    Side Effects: Updates form with this extracted information"""

    insert_buttons = [age_entry,
        income_entry,
        non_work_income_entry,
        resources_entry,
        years_worked_entry,
        lifetime_earnings_entry]
    insert_strings = [
        "age","income_from_work","non-work_income","resources",
        "years_worked","lifetime_earnings"
    ]
    
    set_buttons = [
        marital_status_var,
        disability_var,
        railroad_var,
        gov_employee_var,
        ssdi_covered_var,
        ssdi_sga_var,
        ssdi_adjustment_var,
        ssdi_duration_var
    ]

    set_strings = [
        "marital_status","disability_status","railroad_retirement_benefits",
        "medicare_tax","ssdi_covered","sga_ability","adjustment_to_other_work",
        "condition_lasting_over_12_months"
    ]
    
    for i in range(len(insert_buttons)):
        if extracted_info.get(insert_strings[i],"") != "":
            insert_buttons[i].delete(0,tk.END)
            insert_buttons[i].insert(0,extracted_info.get(insert_strings[i],""))

    for i in range(len(set_buttons)):
        if extracted_info.get(set_strings[i],"") != "":
            set_buttons[i].set(extracted_info.get(set_strings[i],""))

def analyze_data():
    """Analyze what data was entered and what benefits are eligible
    
    Arguments: Nothing
    
    Returns: Nothing 
    
    Side Effects: Updates the prompt with the things that are eligible"""

    try:
        income = float(income_entry.get())
        non_work_income = float(non_work_income_entry.get())
        marital_status = marital_status_var.get()
        resources = float(resources_entry.get())
        disability_status = disability_var.get()
        age = int(age_entry.get())
        years_worked = int(years_worked_entry.get())
        lifetime_earnings = float(lifetime_earnings_entry.get())
        railroad_benefits = railroad_var.get()
        gov_employee_medicare_tax = gov_employee_var.get()
        ssdi_covered = ssdi_covered_var.get()
        ssdi_sga = ssdi_sga_var.get()
        ssdi_adjustment = ssdi_adjustment_var.get()
        ssdi_duration = ssdi_duration_var.get()

        eligible_benefits, explanations = get_eligible_benefits(income, 
        non_work_income, marital_status, resources, disability_status, 
        age, years_worked, lifetime_earnings,
        railroad_benefits, gov_employee_medicare_tax, ssdi_covered, ssdi_sga,
        ssdi_adjustment, ssdi_duration)
        # Building the final result message
        if eligible_benefits:
            result = "You are eligible for the following benefits:\n"
            for benefit in eligible_benefits:
                result += f"- {benefit}\n"

            result += "\nEligibility explanation:\n"
            for explanation in explanations:
                result += f"- {explanation}\n"
        else:
            result = "You are not eligible for any benefits."

        # Display results
        messagebox.showinfo("Eligibility Results", result)

    except ValueError:
        messagebox.showerror("Input Error", "Please make sure all numeric fields are correctly filled.")




root = tk.Tk()
root.title("Benefits Eligibility Checker")
root.geometry("600x600")
root.resizable(True, True)

canvas = tk.Canvas(root)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

scrollable_frame = tk.Frame(canvas)
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

scrollable_frame.columnconfigure(0, weight=1)
scrollable_frame.columnconfigure(1, weight=1)

# Show message 
def show_info(info_text):
    messagebox.showinfo("Additional Information", info_text)

conversation_label = tk.Label(root, text="Enter the conversation:")
conversation_label.pack(pady=10)
conversation_text = tk.Text(root, height=10, width=60)
conversation_text.pack(pady=10)

def extract_and_fill():
    conversation = conversation_text.get("1.0", tk.END).strip()
    extracted_info = extract_information(conversation)
    fill_form_with_extracted_info(extracted_info)

extract_button = tk.Button(root, text="Extract and Fill", command=extract_and_fill)
extract_button.pack(pady=10)

# Labels and Input Fields 
tk.Label(scrollable_frame, text="Enter your age:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
age_entry = tk.Entry(scrollable_frame, width=30)
age_entry.grid(row=1, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Select your marital status:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
marital_status_var = tk.StringVar()
marital_status_dropdown = ttk.Combobox(scrollable_frame, textvariable=marital_status_var, values=[
    "Single adult", "Married couples who live together", "Individual parent who has a child with a disability", 
    "Couples who have a child with a disability", "Child with disability not living with their parent", "Other"
], width=30)
marital_status_dropdown.grid(row=7, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Enter your monthly work income in USD (before taxes and deductions):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
income_entry = tk.Entry(scrollable_frame, width=30)
income_entry.grid(row=3, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Enter your non-work income in USD (before taxes and deductions):").grid(row=4, column=0, padx=10, pady=5, sticky="w")
non_work_income_entry = tk.Entry(scrollable_frame, width=30)
non_work_income_entry.grid(row=5, column=0, padx=10, pady=5)

info_button_non_work = tk.Button(scrollable_frame, text="?", command=lambda: show_info("Non-work income includes resources such as unemployment or pensions."))
info_button_non_work.grid(row=5, column=1, padx=5, pady=5, sticky="w")


tk.Label(scrollable_frame, text="Enter the estimated value of your resources :").grid(row=8, column=0, padx=10, pady=5, sticky="w")
resources_entry = tk.Entry(scrollable_frame, width=30)
resources_entry.grid(row=9, column=0, padx=10, pady=5)

info_button_resources = tk.Button(scrollable_frame, text="?", command=lambda: show_info("Common resources are vehicles and money in bank accounts. Generally, things that don’t count toward your resource limit include:\n- Your home and the land it’s on, as long as you live there;\n- 1 vehicle per household;\n- Most personal belongings and household goods;\n- Property you can’t use or sell."))
info_button_resources.grid(row=9, column=1, padx=5, pady=5, sticky="w")


tk.Label(scrollable_frame, text="Do you have a disability?").grid(row=10, column=0, padx=10, pady=5, sticky="w")
disability_var = tk.StringVar()
disability_dropdown = ttk.Combobox(scrollable_frame, textvariable=disability_var, values=["Yes", "No"], width=30)
disability_dropdown.grid(row=11, column=0, padx=10, pady=5)

info_button_disability = tk.Button(scrollable_frame, text="?", command=lambda: show_info("If you are under age 18, we may consider you “disabled” if you have a medically determinable physical or mental impairment, (including an emotional or learning problem) that:\n- results marked and severe functional limitations; and\n- can be expected to result in death; or\n- has lasted or can be expected to last for a continuous period of not less than 12 months.\n\nIf you are age 18 or older, we may consider you “disabled” if you have a medically determinable physical or mental impairment (including an emotional or learning problem) which:\n- results in the inability to do any substantial gainful activity; and\n- can be expected to result in death; or\n- has lasted or can be expected to last for a continuous period of not less than 12 months."))
info_button_disability.grid(row=11, column=1, padx=5, pady=5, sticky="w")


tk.Label(scrollable_frame, text="Enter your total years of work:").grid(row=12, column=0, padx=10, pady=5, sticky="w")
years_worked_entry = tk.Entry(scrollable_frame, width=30)
years_worked_entry.grid(row=13, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Enter your lifetime earnings:").grid(row=14, column=0, padx=10, pady=5, sticky="w")
lifetime_earnings_entry = tk.Entry(scrollable_frame, width=30)
lifetime_earnings_entry.grid(row=15, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Are you eligible for Railroad Retirement Board benefits?").grid(row=16, column=0, padx=10, pady=5, sticky="w")
railroad_var = tk.StringVar()
railroad_dropdown = ttk.Combobox(scrollable_frame, textvariable=railroad_var, values=["Yes", "No"], width=30)
railroad_dropdown.grid(row=17, column=0, padx=10, pady=5)

info_button_railroad = tk.Button(scrollable_frame, text="?", command=lambda: show_info("See additional information at https://www.rrb.gov/sites/default/files/2024-08/2024_Railroad_Retirement_Handbook_0.pdf"))
info_button_railroad.grid(row=17, column=1, padx=5, pady=5, sticky="w")


tk.Label(scrollable_frame, text="Are you a government employee who paid Medicare tax?").grid(row=18, column=0, padx=10, pady=5, sticky="w")
gov_employee_var = tk.StringVar()
gov_employee_dropdown = ttk.Combobox(scrollable_frame, textvariable=gov_employee_var, values=["Yes", "No"], width=30)
gov_employee_dropdown.grid(row=19, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Have you worked in jobs covered by Social Security?").grid(row=20, column=0, padx=10, pady=5, sticky="w")
ssdi_covered_var = tk.StringVar()
ssdi_covered_dropdown = ttk.Combobox(scrollable_frame, textvariable=ssdi_covered_var, values=["Yes", "No"], width=30)
ssdi_covered_dropdown.grid(row=21, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Can you perform Substantial Gainful Activity (SGA)?").grid(row=22, column=0, padx=10, pady=5, sticky="w")
ssdi_sga_var = tk.StringVar()
ssdi_sga_dropdown = ttk.Combobox(scrollable_frame, textvariable=ssdi_sga_var, values=["Yes", "No"], width=30)
ssdi_sga_dropdown.grid(row=23, column=0, padx=10, pady=5)

info_button_sga = tk.Button(scrollable_frame, text="?", command=lambda: show_info("We use the term substantial gainful activity (SGA) to describe a level of work activity and earnings that is both substantial and gainful. SGA involves performance of significant physical or mental activities, or a combination of both. For your work activity to be substantial, you do not need to work full time. Work activity performed on a part-time basis may also be SGA. If your impairment is anything other than blindness, earnings averaging over $1,550 per month or $2,590 for blind individuals (for the year 2024) generally demonstrate SGA."))
info_button_sga.grid(row=23, column=1, padx=5, pady=5, sticky="w")


tk.Label(scrollable_frame, text="Can you adjust to other work due to your condition?").grid(row=24, column=0, padx=10, pady=5, sticky="w")
ssdi_adjustment_var = tk.StringVar()
ssdi_adjustment_dropdown = ttk.Combobox(scrollable_frame, textvariable=ssdi_adjustment_var, values=["Yes", "No"], width=30)
ssdi_adjustment_dropdown.grid(row=25, column=0, padx=10, pady=5)

tk.Label(scrollable_frame, text="Has your condition lasted or is expected to last for more than 1 year?").grid(row=26, column=0, padx=10, pady=5, sticky="w")
ssdi_duration_var = tk.StringVar()
ssdi_duration_dropdown = ttk.Combobox(scrollable_frame, textvariable=ssdi_duration_var, values=["Yes", "No"], width=30)
ssdi_duration_dropdown.grid(row=27, column=0, padx=10, pady=5)

analyze_button = tk.Button(scrollable_frame, text="Analyze", command=analyze_data)
analyze_button.grid(row=28, column=0, pady=20)

chat_box = tk.Text(root, height=20, width=50, state=tk.DISABLED)
chat_box.pack(pady=10)

# Create an entry widget for input
entry_box = tk.Entry(root, width=40)
entry_box.pack(pady=5, side=tk.LEFT)

# Create a send button
send_button = tk.Button(root, text="Send", command=send_message)
send_button.pack(pady=5, side=tk.LEFT)


for i in range(29):
    scrollable_frame.rowconfigure(i, weight=1)
scrollable_frame.columnconfigure(0, weight=1)

root.mainloop()

