"""
Georgia SNAP eligibility ground truth reference.
Used as context for the prompted evaluation.
"""

GEORGIA_SNAP_CONTEXT = """
# Georgia SNAP (Food Stamps) Eligibility Requirements - Official Reference

## OVERVIEW
Georgia's SNAP program (administered by DFCS) provides food assistance to eligible low-income households.
Georgia uses Broad-Based Categorical Eligibility (BBCE), which is more generous than federal minimums.

---

## 1. INCOME LIMITS (FY2026, effective Oct 1 2025)

Georgia uses TWO income tests. Most households must pass BOTH.

### Gross Monthly Income Limits (130% Federal Poverty Level)
| Household Size | Max Gross Monthly Income |
|---|---|
| 1 | $1,696 |
| 2 | $2,292 |
| 3 | $2,888 |
| 4 | $3,483 |
| 5 | $4,079 |
| 6 | $4,675 |
| 7 | $5,271 |
| 8 | $5,867 |
| Each additional | +$596 |

### Net Monthly Income Limits (100% Federal Poverty Level)
| Household Size | Max Net Monthly Income |
|---|---|
| 1 | $1,305 |
| 2 | $1,763 |
| 3 | $2,222 |
| 4 | $2,681 |
| 5 | $3,140 |
| 6 | $3,600 |
| 7 | $4,059 |
| 8 | $4,518 |
| Each additional | +$459 |

### BBCE (Broad-Based Categorical Eligibility) - Georgia-Specific
- Georgia extends gross income limit to 200% FPL for most households
- 200% FPL Gross Limits: 1-person=$2,610, 2-person=$3,527, 3-person=$4,443, 4-person=$5,359, 5-person=$6,276, 6-person=$7,192
- Under BBCE, most households face NO asset/resource limits
- The net income test (100% FPL) still applies to all households

### Special Rules for Elderly (60+) or Disabled Households
- If ALL adult members are elderly (60+) or disabled: NO gross income test
- Only the net income test applies
- If income exceeds 200% FPL: subject to $4,500 asset limit

---

## 2. ALLOWABLE DEDUCTIONS (subtracted from gross to get net income)

1. **Earned Income Deduction**: 20% of gross earned income (wages, self-employment)
2. **Standard Deduction**:
   - 1-3 person household: $204/month
   - 4 person household: $217/month
   - 5 person household: $254/month
   - 6+ person household: $291/month
3. **Dependent Care Deduction**: Full cost of childcare/dependent care needed for work, training, or education
4. **Child Support Deduction**: Legally obligated child support payments made to non-household members
5. **Medical Expense Deduction** (elderly/disabled only): Out-of-pocket medical expenses over $35/month
6. **Excess Shelter Deduction**:
   - Rent/mortgage + utilities that exceed 50% of net income (after other deductions)
   - Cap of $744/month for non-elderly/disabled households
   - No cap for elderly/disabled households

**Net Income Formula**: Gross Income - Earned Income Deduction - Standard Deduction - Dependent Care - Child Support - Medical (elderly/disabled only) - Excess Shelter = NET INCOME

---

## 3. ASSET/RESOURCE LIMITS

Under Georgia's BBCE:
- **Most households**: NO asset limit
- **Elderly/disabled households with income over 200% FPL**: $4,500 limit
- **Categorically eligible households (TANF/SSI recipients)**: No asset limit

Assets that DON'T count: home you live in, most retirement accounts, one vehicle per household member

---

## 4. CATEGORICAL ELIGIBILITY (Automatic Qualification)

These groups are automatically eligible regardless of other income/asset tests:
- SSI (Supplemental Security Income) recipients
- TANF (Temporary Assistance for Needy Families) recipients
- TCOS (TANF Community Outreach Services) recipients

---

## 5. WHO IS NOT ELIGIBLE

- **Undocumented immigrants**: Not eligible. However, US citizen or qualified immigrant children in the same household may be eligible (household is split - ineligible member's income is partially counted).
- **Most college students**: Students enrolled at least half-time (ages 18-49) are NOT eligible UNLESS they meet an exemption:
  - Working 20+ hours per week
  - Caring for a child under 6
  - Caring for a child 6-11 when adequate childcare is unavailable
  - Receiving TANF
  - Physically or mentally unable to work
  - Enrolled in certain approved programs (SNAP E&T, etc.)
- **Strikers**: Generally not eligible (unless eligible before the strike)
- **Certain felony drug convictions**: May face restrictions (Georgia has partially lifted this ban)

---

## 6. WORK REQUIREMENTS

### General Work Registration (ages 16-59)
Must register for work unless exempt (caring for child under 6, elderly, disabled, working 30+ hrs/week already)

### ABAWD Rule (Able-Bodied Adults Without Dependents)
- Applies to: ages 18-52, no dependents, not disabled
- **IMPORTANT 2026 UPDATE**: Age range expanded to 18-64 effective February 2026
- Must work or participate in approved activities 80 hours/month
- Without meeting requirement: eligible for only 3 months out of any 36-month period
- Exceptions: waived areas (high unemployment), temporary exemptions, good cause

---

## 7. BENEFIT AMOUNTS (Monthly Maximum, FY2026)

| Household Size | Maximum Monthly Benefit |
|---|---|
| 1 | $292 |
| 2 | $536 |
| 3 | $768 |
| 4 | $975 |
| 5 | $1,158 |
| 6 | $1,390 |
| 7 | $1,536 |
| 8 | $1,756 |
| Each additional | +$219 |

Actual benefit = Maximum benefit - (net income × 0.30)

---

## 8. HOW TO APPLY IN GEORGIA

- Online: gateway.ga.gov
- Phone: 1-877-423-4746
- In-person: Local DFCS county office
- Processing time: Up to 30 days (7 days for expedited if income < $150/month or less than $100 in resources)
"""
