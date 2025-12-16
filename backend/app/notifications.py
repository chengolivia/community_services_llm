import os
import requests
from datetime import date, datetime, timedelta
from app.database import fetch_provider_checkins_by_date, fetch_providers_to_notify_checkins
 

def send_test_message(recipient="Olivia Cheng <ogc@andrew.cmu.edu>"):
    response = requests.post(
        "https://api.mailgun.net/v3/peercopilot.com/messages",
  		auth=("api", os.getenv('MAILGUN_SENDING_KEY')),
        data={
            "from": "Test <postmaster@peercopilot.com>",
            "to": recipient,
            "subject": "Hello!",
            "text": "Test message"
        }
    )
    print(f"Status: {response.status_code}")
    
def send_message_from_peercopilot(recipient, subject, text):
    response = requests.post(
        "https://api.mailgun.net/v3/peercopilot.com/messages",
  		auth=("api", os.getenv('MAILGUN_SENDING_KEY')),
        data={
            "from": "PeerCopilot <postmaster@peercopilot.com>",
            "to": recipient,
            "subject": subject,
            "text": text
        }
    )
    return response

def send_daily_check_ins(todays_checkins_for_provider, service_provider_email):
    opening = "Hello from PeerCopilot! \n Here is a reminder for today's check-ins: \n\n"
    body = "\n".join([f"- {d['service_user_name']}: {d['follow_up_message']}" for d in todays_checkins_for_provider])
    closing = "\n ---- \n"
    full_text = opening + body + closing
    subject = f"{date.today()} Check-In Reminders"
    response = send_message_from_peercopilot(service_provider_email, subject, full_text)
    return response

def notification_job():
    print("Starting notification job...")
    current_time = datetime.now()
    tolerance = timedelta(minutes=15)
    success, providers = fetch_providers_to_notify_checkins(current_time.time(), (current_time + tolerance).time())
    count_sent = 0
    if not success:
        print(f"Error fetching providers: {providers}")
        return
    for p in providers:
        success, todays_checkins = fetch_provider_checkins_by_date(p["username"], date.today())
        if success and len(todays_checkins) > 0:
            send_daily_check_ins(todays_checkins, p["email"])
            count_sent += 1
    print("Notification job finished and {count_sent} messages sent...")
    

