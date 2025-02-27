import os
import pandas as pd

DATA_FOLDER = "data"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def save_to_excel(user_id, first_name, last_name, username, group_id, group_name, survey_date, responses, survey_name):
    sanitized_name = survey_name.replace(" ", "_").replace("/", "_")
    filename = f"{DATA_FOLDER}/survey_results_{sanitized_name}.xlsx"
    
    df = pd.DataFrame({
        "User ID": [user_id] * len(responses),
        "First Name": [first_name] * len(responses),
        "Last Name": [last_name] * len(responses),
        "Username": [username] * len(responses),
        "Group ID": [group_id] * len(responses),
        "Group Name": [group_name] * len(responses),
        "Survey Date": [survey_date] * len(responses),
        "Survey Name": [survey_name] * len(responses),
        "Question": [resp.get('question', '') for resp in responses],
        "Answer": [resp.get('answer', '') for resp in responses]
    })
    
    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        df = pd.concat([existing_df, df], ignore_index=True)
    
    df.to_excel(filename, index=False)
