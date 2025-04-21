import csv

def csv_to_dictionary(file_name):
    """Given a file name string, return the corresponding
        CSV as a list of dictionaries
    
    Arguments:
        file_name: String
    
    Returns: List of dictionaries"""

    with open(file_name) as f:
        a = [{k: v for k, v in row.items()}
            for row in csv.DictReader(f, skipinitialspace=True)]
        return a


def get_all_outreach(user_name):
    """Return all the outreach for a given Peer Provider
    
    Arguments:
        user_name: String, user name for the peer provider
    
    Returns: List of dictionaries
        Each dictionary has
            Service User Name
            Last Session Date
            Check In Date
            Follow up Message"""
    
    all_users = csv_to_dictionary("data/profiles.csv")
    username_to_name = {}

    for row in all_users:
        if row['provider'] == user_name:
            username_to_name[row['service_user_id']] = row['service_user_name']
    
    current_service_user_ids = set(list(username_to_name.keys()))

    all_outreach = csv_to_dictionary("data/outreach_details.csv")
    ret = []
    for outreach in all_outreach:
        if outreach['user_name'] in current_service_user_ids:
            ret.append({'name': username_to_name[outreach['user_name']],
                        'last_session': outreach['last_session'],
                        'check_in': outreach['check_in'],
                        'follow_up_message': outreach['follow_up_message']})

    return ret 
    

def get_all_service_users(user_name):
    """Return all the services users for a given Peer Provider
    
    Arguments:
        user_name: String, user name for the peer provider
    
    Returns: List of dictionaries
        Each dictionary has
            Service User Name
            Location"""
    
    all_users = csv_to_dictionary("data/profiles.csv")
    all_outreach = csv_to_dictionary("data/outreach_details.csv")

    all_users = [i for i in all_users if i['provider'] == user_name]


    for i in all_users:
        for j in all_outreach:
            if i['service_user_id'] == j['user_name']:
                for k in ["last_session","check_in","follow_up_message"]:
                    i[k] = j[k]

    print(all_users)
    return all_users 