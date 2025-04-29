import openai
from utils import call_chatgpt_api
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import cloudscraper
import os
import pandas as pd
import argparse 

openai.api_key = os.environ.get("SECRET_KEY")

parser = argparse.ArgumentParser()
parser.add_argument('--location',         '-l', help='location', type=str, default="New Jersey")
parser.add_argument('--org_name',         '-o', help='organization', type=str, default="cspnj")
args = parser.parse_args()
location      = args.location
org_name = args.org_name

def get_text_from_url(url):
    response = requests.get(url,headers=headers,timeout=5)
    if response.status_code != 200:
        response = scraper.get(url,timeout=5)
        if response.status_code != 200:
            return "Error"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    page_text = soup.get_text(separator='\n', strip=True)
    return page_text[:100000]

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
scraper = cloudscraper.create_scraper()
all_entries = open("data/{}_resources.txt".format(org_name),"r").read().strip().split("\n")

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
        url = next(search(i['name']+' Phone Number {}'.format(location), num = 1,stop=1))
        all_text = get_text_from_url(url)
    except Exception as e:
        print(e) 
        
    if all_text != 'Error':
        resources_by_description_phone[i['name']]['phone'] = call_chatgpt_api("You are a helpful assistant that helps users find a phone number from the text from a website. Return only the phone number, nothing else","Please find the phone number (and return only the phone number, no dashes) for the following. Use only the text, and if no phone number is found, return an empty string: {}".format(all_text),stream=False)
        resources_by_description_phone[i['name']]['url_phone'] = url
    try:
        url = next(search(i['name']+' {}'.format(location),num=1,stop=1))
        all_text = get_text_from_url(url)
    except Exception as e:
        print(e) 
    if all_text != 'Error':
        resources_by_description_phone[i['name']]['description'] = call_chatgpt_api("You are a helpful assistant that helps users summarize the text from a website. Return only the description, nothing else","Please summarize the information from the following website. Make sure you capture the location, operating hours, and whether there are prerequisites to using this (e.g. need a form of identification, etc.). If no information is found, return an empty string: {}".format(all_text),stream=False)
        resources_by_description_phone[i['name']]['url'] = url
        tot += 1

formatted_data = []

for name, details in resources_by_description_phone.items():
    entry = {"service": name}
    entry.update(details) 
    formatted_data.append(entry)

df = pd.DataFrame(formatted_data)
df.to_csv('data/{}.csv'.format(org_name), index=False)