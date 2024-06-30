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
    user_data_list = []
    user_dates_set = set()  # Set to track unique user-date combinations

    for user_id, user_info in data_users.items():
        video_attendance = user_info.get('IsVideoAttended', '').lower()
        user_info['IsVideoAttended'] = 'yes' if video_attendance == 'yes' else 'no'
        
        # Avoid duplicates for the same day
        user_date = (user_info.get('name', ''), user_info.get('date', ''))
        if user_date not in user_dates_set:
            user_dates_set.add(user_date)
            user_info['location'] = get_user_location(user_id)
            user_data_list.append(user_info)
    
    return jsonify(user_data_list)

@app.route('/data_user_scores')
def get_data_user_scores():
    extracted_data = extract_user_scores_data(data_user_scores, data_users)
    return jsonify(extracted_data)

@app.route('/data_user_locations')
def get_data_user_locations():
    user_locations = []
    users_docs = firestore_db.collection('users').stream()
    for doc in users_docs:
        user_data = doc.to_dict()
        user_locations.append({
            'name': user_data.get('name', 'Unknown'),
            'location': user_data.get('location', 'Unknown')
        })
    return jsonify(user_locations)

@app.route('/chart_data')
def chart_data():
    extracted_data = extract_user_scores_data(data_user_scores, data_users)
    chart_data = {
        'labels': [data['name'] for data in extracted_data],
        'datasets': [
            {
                'label': 'Correct Count',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1,
                'hoverBackgroundColor': 'rgba(75, 192, 192, 0.4)',
                'hoverBorderColor': 'rgba(75, 192, 192, 1)',
                'data': [data['correctCount'] for data in extracted_data],
            },
            {
                'label': 'Wrong Count',
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'borderWidth': 1,
                'hoverBackgroundColor': 'rgba(255, 99, 132, 0.4)',
                'hoverBorderColor': 'rgba(255, 99, 132, 1)',
                'data': [data['wrongCount'] for data in extracted_data],
            },
        ],
    }
    return jsonify(chart_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
