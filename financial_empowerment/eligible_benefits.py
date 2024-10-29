from utils import call_chatgpt_api

def get_eligible_benefits(income, non_work_income, marital_status,
        resources, disability_status, age, years_worked, lifetime_earnings,
        railroad_benefits, gov_employee_medicare_tax, ssdi_covered, ssdi_sga,
        ssdi_adjustment, ssdi_duration):
    """Given information about a user, get the eligible benefits
    
    Arguments:
        income: Integer, their income
        non_work_income: Income from non_work sources
        ...
    
    Returns: Two lists, the first is the list of eligible benefits, second is explanations"""
    
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

    return eligible_benefits, explanations

def call_llm_check_eligibility(extracted_info, pdf_text):
    """Check what things a user is eligible for
    
    Arguments:
        user_input: What the user enters
        pdf_text: Information from the PDF, as text
        
    Returns: Response, which is the list of benefits"""

    check_sys_prompt = open("prompts/system_check_prompt.txt").read()
    prompt = open("prompts/check_propmt.txt").read().format(pdf_text,extracted_info)
    eligibility_info = call_chatgpt_api(check_sys_prompt,prompt).strip()
    return eligibility_info


