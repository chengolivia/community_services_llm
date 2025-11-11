import psycopg
import os 
import openai 
import uuid
import json 
from datetime import datetime, timedelta
from app.utils import call_chatgpt_api_all_chats
from app.database import CONNECTION_STRING

openai.api_key = os.environ.get("SECRET_KEY")


def generate_followup_message(messages):
    """Given a set of messages, create a dictionary with recommended followups
    
    Arguments:
        messages: List of dictionaries with sender and text keys
        
    Returns: Dictionary, with two keys: follow_up_message and follow_up date"""

    all_message_list = [{'role': 'system', 'content': 'You are a Co-Pilot tool for {}, a peer-peer mental health organization. Please provider 1) A followup message (if applicable) and a followup date (if applicabe). Do this in a JSON format: {"follow_up_message": "Hello", "follow_up_date": "2024-01-31"}'}]
    prior_messages = []
    for m in messages:
        prior_messages.append({'role': m['sender'],'content': m['text']})
    all_message_list += prior_messages
    response = call_chatgpt_api_all_chats(all_message_list,max_tokens=750,stream=False,response_format={"type": "json_object"})
    return json.loads(response)

def load_messages_for_conversation(conversation_id):
    """Loads all messages for a given conversation_id in chronological order.

    Arguments:
        conversation_id: String, conversation_id 
    
    Returns: List of dictionaries with sender, text, and created_at

    """
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT sender, text, created_at FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC
    ''', (conversation_id,))

    messages = cursor.fetchall()
    conn.close()
    return [{"sender": sender, "text": text, "created_at": created_at} for sender, text, created_at in messages]


def generate_check_ins_standard(service_user_id: str, conversation_summary: str = ""):
    """Generate and insert 3 check-ins at 1, 2, and 3 weeks"""
    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    try:
        # Get service user name and last_session date
        cursor.execute(
            """SELECT p.service_user_name, o.last_session 
               FROM profiles p
               LEFT JOIN outreach_details o ON p.service_user_id = o.service_user_id
               WHERE p.service_user_id = %s
                 AND o.last_session IS NOT NULL
                 AND o.last_session != ''
               ORDER BY o.created_at DESC 
               LIMIT 1""",
            (service_user_id,)
        )
        result = cursor.fetchone()
        
        if not result or not result[0]:
            # Try just getting the profile
            cursor.execute(
                "SELECT service_user_name FROM profiles WHERE service_user_id = %s",
                (service_user_id,)
            )
            profile_result = cursor.fetchone()
            if not profile_result:
                return False, "Service user not found"
            
            service_user_name = profile_result[0]
            last_session = None
        else:
            service_user_name = result[0]
            last_session = result[1]
        
        # Determine base date
        if last_session:
            try:
                base_date = datetime.strptime(last_session, "%Y-%m-%d")
            except (ValueError, TypeError):
                base_date = datetime.now()
        else:
            base_date = datetime.now()
        
        last_session_str = base_date.strftime("%Y-%m-%d")
        
        # Generate and insert 3 check-ins
        check_ins = []
        for weeks in [1, 2, 3]:
            check_in_date = base_date + timedelta(weeks=weeks)
            check_in_str = check_in_date.strftime("%Y-%m-%d")
            
            # Personalized message with user's name
            follow_up = f"Hey {service_user_name}, I wanted to see how things were going"
            
            cursor.execute('''
                INSERT INTO outreach_details 
                (service_user_id, last_session, check_in, follow_up_message)
                VALUES (%s, %s, %s, %s)
            ''', (service_user_id, last_session_str, check_in_str, follow_up))
            
            check_ins.append({
                'date': check_in_str,
                'message': follow_up
            })
        
        conn.commit()
        return True, check_ins
        
    except Exception as e:
        conn.rollback()
        print(f"[DB Error] {e}")
        return False, str(e)
    finally:
        conn.close()


def autogenerate_conversations(username):
    """Find all conversations without corresponding outreach generated
    
    Arguments:
        username: string, provider's usernaem
    
    Returns: Nothing
    
    Side Effects: Writes new outreach events to the calendar"""

    conn = psycopg.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM conversations
        WHERE username = %s AND outreach_generated = FALSE
    ''', (username,))
    conversation_ids = cursor.fetchall()

    for conv_id in conversation_ids:
        conv_id = conv_id[0]
        messages = load_messages_for_conversation(conv_id)
        followup = generate_followup_message(messages)
        service_user_id = f"User-{uuid.uuid4().hex[:8]}"
        if followup['follow_up_date'] and followup['follow_up_message']:
            cursor.execute('''
                    INSERT INTO profiles (service_user_id, service_user_name, provider, location, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (service_user_id) DO NOTHING
            ''', (service_user_id, service_user_id, username, "Freehold, NJ", "Active"))
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('''
                INSERT INTO outreach_details (service_user_id, last_session, check_in, follow_up_message)
                VALUES (%s, %s, %s, %s)
            ''', (
                service_user_id,
                today_str,
                followup['follow_up_date'],  # This will insert NULL if it's None
                followup['follow_up_message']
            ))

        cursor.execute('''
            UPDATE conversations
            SET outreach_generated = TRUE
            WHERE id = %s
        ''', (conv_id,))

    conn.commit()
    conn.close()