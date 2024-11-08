import re
from copy import deepcopy
import openai
from utils import call_chatgpt_api
from secret import naveen_key as key 
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import time
import cloudscraper
import json 

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
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
scraper = cloudscraper.create_scraper()
def get_text_from_url(url):
    # Send a request to the URL
    response = requests.get(url,headers=headers,timeout=5)
    
    # Check if the request was successful
    if response.status_code != 200:
        response = scraper.get(url,timeout=5)
        if response.status_code != 200:
            return "Error"
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract all text and clean it up
    page_text = soup.get_text(separator='\n', strip=True)
    return page_text[:100000]


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

data = open("data/all_resources.txt").read().strip().split("\n")

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

num_error = 0
tot = 0
print("There are {} entries".format(len(all_entries)))
resources_by_description_phone = {}
for idx,i in enumerate(all_entries):
    print("On {} of {}, have {}".format(idx+1,len(all_entries),tot))
    resources_by_description_phone[i['name']] = {
        'description': '',
        'url': '',
        'phone': '',
        'url_phone': '',
    }
    try:
        url = list(search(i['name']+' Phone Number New Jersey',num_results=1))[0]
        all_text = get_text_from_url(url)
    except:
        continue 

    if all_text != 'Error':
        resources_by_description_phone[i['name']]['phone'] = call_chatgpt_api("You are a helpful assistant that helps users find a phone number from the text from a website. Return only the phone number, nothing else","Please find the phone number (and return only the phone number, no dashes) for the following. Use only the text, and if no phone number is found, return an empty string: {}".format(all_text))
        resources_by_description_phone[i['name']]['url_phone'] = url

    try:
        url = list(search(i['name']+' New Jersey',num_results=1))[0]
        all_text = get_text_from_url(url)
    except:
        continue 

    if all_text != 'Error':
        resources_by_description_phone[i['name']]['description'] = call_chatgpt_api("You are a helpful assistant that helps users summarize the text from a website. Return only the description, nothing else","Please summarize the information from the following website. Make sure you capture the location, operating hours, and whether there are prerequisites to using this (e.g. need a form of identification, etc.). If no information is found, return an empty string: {}".format(all_text))
        resources_by_description_phone[i['name']]['url'] = url
        tot += 1

print("Writing")
json.dump(resources_by_description_phone,open("data/all_resources_raw.json","w"))