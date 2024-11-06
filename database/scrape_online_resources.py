import re
from copy import deepcopy
import openai
from utils import call_chatgpt_api
from secret import naveen_key as key 

openai.api_key = key 
system_prompt = "You are a helpful assistant that reformats information on resources for mental health and other community services. You will return information in the format provided"
general_prompt = open("prompts/scrape_data.txt").read().strip()
csv_header = "Service,Phone Number,Description,Website Link,Responsible Region,Operating Hours,Category\n"

def is_date(line):
    """Determine if a line is in the date format MM/DD/YYYY
    Arguments:
        line: String
    
    Returns: Boolean, whether the line is a date"""

    return re.match(r"\d{2}/\d{2}/\d{4}", line)

def format_entry(entry):
    """Format a dictionary, with fields in some order, into a list of strings
    For example {'a': 1, 'b': 2} is 
    a: 1
    b: 2
    
    Arguments:
        entry: Dictionary
    
    Returns: String, the dictionary formatted on a line-by-line"""

    s = []
    for field in all_fields:
        if field in entry and entry[field] != '':
            s.append("{}: {}".format(field,entry[field]))
        

    return "\n".join(s)

def format_gpt(entry):
    """Format a ChatGPT entry that enters CSV info line-by-line
    
    Arguments"""
    entry = entry.strip() 
    entry = entry.split("\n")
    entry = ['"{}"'.format(i.strip()) for i in entry if len(i) == 0 or i[0] != '"']
    entry = entry[:7]

    if entry[-1].lower().replace('"','').strip() not in wellness_dimensions:
        entry[-1] = '""'

    return ",".join(entry)

data = open("data/all_resources.txt").read().strip().split("\n")[:10]

all_counties = {"atlantic","bergen","burlington","camden",
            "cape may","cumberland","essex","gloucester","hudson","hunterdon",
            "mercer","middlesex","monmouth","morris","ocean","passaic",
            "salem","somerset","sussex","union","warren"}
wellness_dimensions = {'emotional', 'financial', 'intellectual', 'occupational', 
                       'physical', 'social', 'spiritual', 'environmental'}
all_fields = ['name','county','city','last updated','wellness dimension']
default_curr_entry = {'name': '','county': '', 'city': '','last updated': '', 'wellness dimension': ''}

all_entries = []
curr_entry = {}
curr_field_idx = 0

for line in data:
    line = line.strip()

    if is_date(line):
        curr_field_idx = 3
    elif line.lower() in wellness_dimensions:
        curr_field_idx = 4
    elif line.lower() in all_counties:
        curr_field_idx = 1
    else:
        if curr_field_idx == 1:
            curr_field_idx = 2
        elif curr_field_idx == 4:
            all_entries.append(curr_entry)
            curr_entry = deepcopy(default_curr_entry)
            curr_field_idx = 0

    curr_entry[all_fields[curr_field_idx]] = line
    curr_field_idx += 1
    if curr_field_idx == len(all_fields):
        all_entries.append(curr_entry)
        curr_entry = deepcopy(default_curr_entry)
        curr_field_idx = 0

print(all_entries)

# new_csv = []
# for i in range(len(all_entries)):
#     try:
#         formatted_prompt = general_prompt.format(all_entries[i])
#         gpt_info = call_chatgpt_api(system_prompt,formatted_prompt)
#         formatted_csv = format_gpt(gpt_info)
#         new_csv.append(formatted_csv)
#         print("Succesfully processed resource {} of {}".format(i+1,len(all_entries)))
#     except:
#         print("Error with entry {} of {}".format(i+1,len(all_entries)))
#         continue 
    
# w = open("data/enhanced_resources.csv","w")
# w.write(csv_header)
# w.write("\n".join(list(set(new_csv))))
# w.close()