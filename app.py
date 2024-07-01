import os
import json
from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, db, firestore

app = Flask(__name__)

# Read the credential JSON string from the environment variable
cred_json = os.getenv('FIREBASE_CREDENTIALS')
if not cred_json:
    raise ValueError("No Firebase credentials provided")

# Convert the JSON string to a dictionary
cred_dict = json.loads(cred_json)

# Initialize Firebase Admin SDK
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://vivify-technocrats-default-rtdb.firebaseio.com/'
})

# Initialize Firestore
firestore_db = firestore.client()

# Reference to the Firebase databases
ref_users = db.reference('Users2')
ref_user_scores = db.reference('UserScores')

# Retrieve data
data_users = ref_users.get()
data_user_scores = ref_user_scores.get()

# Function to fetch user location from Firestore
def get_user_location(user_id):
    doc = firestore_db.collection('users').document(user_id).get()
    if doc.exists:
        return doc.to_dict().get('location', 'Unknown')
    return 'Unknown'

# Function to extract relevant fields from nested objects in UserScores
def extract_user_scores_data(user_scores_data, data_users):
    extracted_data = []
    scores_set = set()  # Set to track unique scores per user
    for user_id, sessions in user_scores_data.items():
        for session_id, session_data in sessions.items():
            user_name = session_data.get('userName', 'Unknown')
            correct_count = session_data.get('correctCount', 0)
            wrong_count = session_data.get('wrongCount', 0)
            
            # Match user_id with Users2 to get the IsVideoAttended status
            is_video_attended = 'no'  # Default to 'no'
            if user_id in data_users:
                user_info = data_users[user_id]
                is_video_attended = 'yes' if user_info.get('IsVideoAttended', '').lower() == 'yes' else 'no'

            score_tuple = (user_name, correct_count, wrong_count, is_video_attended)
            if score_tuple not in scores_set:
                scores_set.add(score_tuple)
                extracted_data.append({
                    'name': user_name,
                    'correctCount': correct_count,
                    'wrongCount': wrong_count,
                    'IsVideoAttended': is_video_attended,
                })
    return extracted_data

@app.route('/')
def index():
    return open('index2.html').read()

@app.route('/data')
def get_data():
    merged_data = []
    user_dates_set = set()  # Set to track unique user-date combinations

    for user_id, user_info in data_users.items():
        user_name = user_info.get('name', '')
        video_attendance = user_info.get('IsVideoAttended', '').lower()
        user_info['IsVideoAttended'] = 'yes' if video_attendance == 'yes' else 'no'
        user_info['location'] = get_user_location(user_id)
        
        # Avoid duplicates for the same day
        user_date = (user_name, user_info.get('date', ''))
        if user_date not in user_dates_set:
            user_dates_set.add(user_date)
            merged_data.append({
                'date': user_info.get('date', ''),
                'helmet': user_info.get('helmet', ''),
                'name': user_name,
                'shoe': user_info.get('shoe', ''),
                'time': user_info.get('time', ''),
                'correctCount': 0,
                'wrongCount': 0,
                'IsVideoAttended': user_info.get('IsVideoAttended', ''),
                'location': user_info.get('location', 'Unknown')
            })

    # Merge with UserScores data
    for score in extract_user_scores_data(data_user_scores, data_users):
        for user in merged_data:
            if user['name'] == score['name']:
                user['correctCount'] = score['correctCount']
                user['wrongCount'] = score['wrongCount']
                user['IsVideoAttended'] = score['IsVideoAttended']

    return jsonify(merged_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
