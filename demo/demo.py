import tkinter as tk
from tkinter import ttk, messagebox

def analyze_data():
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

        eligible_benefits = []
        explanations = []

        # Little to no income check for SSI
        low_income = False
        if marital_status == "single adult" and (income < 1971 and non_work_income < 963):
            low_income = True
        elif marital_status == "married couples who live together" and (income < 2915 and non_work_income < 1435):
            low_income = True
        elif marital_status == "an individual parent who has a child with a disability" and (income < 3897 and non_work_income < 1926):
            low_income = True
        elif marital_status == "couples who have a child with a disability" and (income < 4841 and non_work_income < 2398):
            low_income = True
        elif marital_status == "a child with disability not living with their parent" and (income < 1971 and non_work_income < 963):
            low_income = True
        
        # Little to no resources check for SSI
        low_resources = resources <= (2000 if marital_status == "single adult" else 3000)
        
        # Disability or age check for SSI
        eligible_disability_age = disability_status == "Yes" or age > 65

        # Supplemental Security Income (SSI) eligibility logic
        ssi_eligible = low_income and low_resources and eligible_disability_age
        if ssi_eligible:
            eligible_benefits.append("Supplemental Security Income (SSI)")
            explanations.append("You are eligible for SSI because you have low income, limited resources, and you are either disabled or over the age of 65.")

        # Social Security Administration (SSA) eligibility
        credits_earned = lifetime_earnings // 1730
        ssa_eligible = credits_earned >= 40
        if ssa_eligible:
            eligible_benefits.append("Social Security Administration (SSA)")
            explanations.append("You are eligible for SSA benefits because you have earned at least 40 credits from your lifetime earnings.")

        # Medicare Part A eligibility
        medicare_part_a_eligible = ssa_eligible or railroad_benefits == "Yes" or gov_employee_medicare_tax == "Yes"
        if medicare_part_a_eligible:
            eligible_benefits.append("Medicare Part A")
            explanations.append("You are eligible for Medicare Part A because you either qualify for SSA benefits, Railroad Retirement benefits, or have paid Medicare taxes as a government employee.")

        # Medicare Part B eligibility
        medicare_part_b_eligible = medicare_part_a_eligible
        if medicare_part_b_eligible:
            eligible_benefits.append("Medicare Part B")
            explanations.append("You are eligible for Medicare Part B since you are eligible for Medicare Part A.")

        # Medicare Part C (Advantage Plan) eligibility
        medicare_part_c_eligible = medicare_part_a_eligible and medicare_part_b_eligible
        if medicare_part_c_eligible:
            eligible_benefits.append("Medicare Part C (Advantage Plan)")
            explanations.append("You are eligible for Medicare Part C (Advantage Plan) since you are eligible for both Medicare Part A and Part B.")

        # Medicare Part D eligibility
        medicare_part_d_eligible = medicare_part_a_eligible or medicare_part_b_eligible
        if medicare_part_d_eligible:
            eligible_benefits.append("Medicare Part D")
            explanations.append("You are eligible for Medicare Part D because you are eligible for either Medicare Part A or Part B.")

        # SSDI eligibility
        ssdi_eligible = ssdi_covered == "Yes" and credits_earned >= 40 and (credits_earned - years_worked * 4) >= 20
        ssdi_eligible = ssdi_eligible and ssdi_sga == "Yes" and ssdi_adjustment == "Yes" and ssdi_duration == "Yes"
        if ssdi_eligible:
            eligible_benefits.append("Social Security Disability Insurance (SSDI)")
            explanations.append("You are eligible for SSDI because you have sufficient work credits, cannot perform substantial gainful activity, and your condition has lasted or is expected to last at least 12 months.")

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

for i in range(29):
    scrollable_frame.rowconfigure(i, weight=1)
scrollable_frame.columnconfigure(0, weight=1)

root.mainloop()
