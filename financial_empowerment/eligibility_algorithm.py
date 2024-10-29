from typing import Dict, Optional, List

# Define weighted constraints for each benefit
benefit_constraints = {
    "SSI": {
        "age": {"constraint": lambda age: age >= 65, "weight": 0.4, "description": "Age should be 65 or older"},
        "monthly_income": {"constraint": lambda income: income < 1971, "weight": 0.3, "description": "Monthly income should be less than $1971"},
        "resources": {"constraint": lambda resources: resources <= 2000, "weight": 0.2, "description": "Resources should be $2000 or less"},
        "disability_status": {"constraint": lambda disability: disability, "weight": 0.1, "description": "User should be disabled"}
    },
    "SSA": {
        "age": {"constraint": lambda age: age >= 62, "weight": 0.3, "description": "Age should be 62 or older"},
        "work_credits": {"constraint": lambda credits: credits >= 40, "weight": 0.4, "description": "User should have 40 or more work credits"}
    },
    "Medicare": {
        "age": {"constraint": lambda age: age >= 65, "weight": 0.4, "description": "Age should be 65 or older"},
        "work_credits": {"constraint": lambda credits: credits >= 40, "weight": 0.2, "description": "User or spouse should have 40 or more work credits"},
        "disability_status": {"constraint": lambda disability: disability, "weight": 0.1, "description": "User should be disabled"},
        "social_security_eligibility": {"constraint": lambda eligible: eligible, "weight": 0.3, "description": "Eligible for Social Security or Railroad Retirement benefits"}
    },
    "SSDI": {
        "work_credits": {"constraint": lambda credits: credits >= 20, "weight": 0.4, "description": "User should have 20 or more recent work credits"},
        "disability_status": {"constraint": lambda disability: disability, "weight": 0.3, "description": "User should be disabled"},
        "sg_activity": {"constraint": lambda sga: not sga, "weight": 0.3, "description": "User should not be engaged in substantial gainful activity"}
    }
}

# Function to calculate eligibility score and explanations for a given benefit
def calculate_eligibility_score(benefit: str, user_info: Dict[str, Optional[int]]) -> Dict[str, any]:
    constraints = benefit_constraints.get(benefit, {})
    score = 0.0
    total_weight = sum(c["weight"] for c in constraints.values())
    met_constraints: List[str] = []
    unmet_constraints: List[str] = []
    missing_constraints: List[str] = []

    for criterion, data in constraints.items():
        constraint_func = data["constraint"]
        weight = data["weight"]
        description = data["description"]
        user_value = user_info.get(criterion)

        if user_value is None:
            # Data is missing, assign half weight and add to missing constraints
            score += weight * 0.5
            missing_constraints.append(description)
        elif constraint_func(user_value):
            # Constraint is met
            score += weight
            met_constraints.append(description)
        else:
            # Constraint is unmet
            unmet_constraints.append(description)

    # Normalize score by dividing by total possible weight (to get a %)
    normalized_score = score / total_weight * 100
    category = categorize_eligibility(normalized_score)

    return {
        "score": normalized_score,
        "category": category,
        "met_constraints": met_constraints,
        "unmet_constraints": unmet_constraints,
        "missing_constraints": missing_constraints
    }

# Function to categorize eligibility based on score
def categorize_eligibility(score: float) -> str:
    if score >= 90:
        return "100% eligible"
    elif score >= 70:
        return "Likely eligible"
    elif score >= 40:
        return "Maybe eligible"
    else:
        return "Not eligible"

# Function to check eligibility for all benefits with explanations
def check_all_benefits(user_info: Dict[str, Optional[int]]) -> Dict[str, Dict[str, any]]:
    results = {}
    for benefit in benefit_constraints.keys():
        eligibility_info = calculate_eligibility_score(benefit, user_info)
        results[benefit] = eligibility_info
    return results

# Function to format the output in natural language
def generate_output(results: Dict[str, Dict[str, any]]) -> str:
    output = ""
    for benefit, result in results.items():
        output += f"Benefit: {benefit}\n"
        output += f"  Category: {result['category']}\n"
        output += f"  Score: {result['score']:.2f}%\n"
        output += f"  Met Constraints: {', '.join(result['met_constraints'])}\n"
        output += f"  Unmet Constraints: {', '.join(result['unmet_constraints'])}\n"
        output += f"  Missing Constraints: {', '.join(result['missing_constraints'])}\n\n"
    return output

# Example function to run the full eligibility check and return natural language output
def run_eligibility_check(extracted_info: Dict[str, Optional[int]]) -> str:
    results = check_all_benefits(extracted_info)
    return generate_output(results)
