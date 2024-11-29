import streamlit as st
import json
import yaml
import streamlit_authenticator as stauth
import pandas as pd
import pickle
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Load the YAML configuration file
with open("allowed_users.yaml") as file:
    config = yaml.safe_load(file)

# Load the trained Voting Classifier model
with open("voting_classifier_mov_pred_1.pkl", "rb") as file:
    voting_classifier_mov_pred_1 = pickle.load(file)

# Load the preprocessor used during training (if applicable)
with open("preprocessor_mov_pred_1.pkl", "rb") as file:
    preprocessor_mov_pred_1 = pickle.load(file)

# Set up Google Sheets integration
def init_google_sheet():
    # Define the scope
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Load the credentials from Streamlit Secrets
    service_account_info = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scope)

    client = gspread.authorize(creds)
    
    # Open the Google Sheet by name
    sheet = client.open("Streamlit_login_track").movie_app  # Adjust the sheet name as needed

    return sheet

def log_user_login(username):
    sheet = init_google_sheet()  # Initialize the sheet
    login_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = [username, login_time]  # Add any additional columns as needed
    sheet.append_row(new_row)  # Append the new row at the bottom

# Set cookie expiry to 7 days
authenticator = stauth.Authenticate(
    config['credentials'],
    'news_app_cookie_test',  # Replace with your own cookie name
    'abc123',  # Replace with your own signature key
    cookie_expiry_days=7  # Cookie expires after 7 days
)

# Add Login Form

login_result = authenticator.login()

if st.session_state['authentication_status']:
    # Log the user login data to Google Sheets
    log_user_login(st.session_state["username"])
    
    authenticator.logout()
    st.write(f'Welcome *{st.session_state["name"]}*')
    
    # Genre options and other dropdown selections

    studio_options = sorted([
        "Dimension Films", "DreamWorks", "Paramount Pictures", "Universal Pictures", 
        "Marvel Studios", "Sony Pictures", "New Line Cinema", "20th Century Fox", 
        "China Film Co. / China based", "Walt Disney", "Summit Entertainment", 
        "Pixar Animation Studios", "Warner Bros.", "Columbia Pictures", "Others", 
        "Screen Gems", "MGM", "Lionsgate", "TriStar Pictures"
    ])
    
    genre_options = sorted([
        "Animation", "Action", "Others (Mystery_family_romance_war)", "Fantasy", 
        "Sci-Fi", "Horror", "Comedy", "Adventure", "Crime/Thriller", 
        "Drama", "Biography/Documentary"
    ])
    
    dur_mins_options = [
    "Less than or equal to 80 mins", "81-90 mins", "91-100 mins", "101-110 mins", "111-120 mins", 
    "121-130 mins", "131-140 mins", "141-150 mins", "151 mins and above"]
    
    production_year_options = ["Pre 1980", "1980s", "1990s", "2000s", "2010s", "2020s"]

    us_Box_Office_mn_usd_options = [
    "Less than or equal to 100", "101-300", "301-500", "501-700", 
    "701-900", "Greater than 901"]

        
    # Streamlit app interface
    st.title("English Movies Rating Prediction based on Machine Learning model")
    
    # Collect user inputs via Streamlit input elements
    dur_mins = st.selectbox("Select Duration in mins of the movie:", dur_mins_options)
    studio = st.selectbox("Select Studio:", studio_options)
    production_year = st.selectbox("Select Production year of the movie:", production_year_options)
    genre_primary = st.selectbox("Select Genre:", genre_options)
    movie_rating_imdb = st.slider("Enter Movie Rating basis IMDB (0-10):", min_value=0.0, max_value=10.0, step=0.1)
    actor_famous_1 = st.radio("Is the main actor famous? (0 (Not famous) or 1 (Famous)):", options=[0, 1])
    actress_famous_1 = st.radio("Is the main actress famous? (0 (Not famous) or 1 (Famous)):", options=[0, 1])
    franchise_yes_1 = st.radio("Is it part of a franchise? (0 (Not a franchise) or 1 (Franchise)):", options=[0, 1])
    us_box_office_mn_usd = st.selectbox("Select US Box office revenue in USD Milllions:", us_Box_Office_mn_usd_options)
    
    # Collect the inputs into a DataFrame when the user clicks the button
    if st.button("Submit"):
        # Store the input data in session state
        st.session_state['user_inputs'] = [dur_mins, studio, production_year, genre_primary, movie_rating_imdb, actor_famous_1, actress_famous_1, franchise_yes_1, us_box_office_mn_usd]

        new_data_show_case = pd.DataFrame([st.session_state['user_inputs']], columns=[
            'Dur mins', 'Studio', 'Production_year', 'Genre_primary', 
            'Movie Rating imdb', 'Actor_Famous_1', 'Actress_Famous_1', 
            'Franchise_yes_1', 'US_Box_Office_mn_usd'
        ])

        # Display the DataFrame in Streamlit app
        st.write("User Input Data:")
        st.dataframe(new_data_show_case)

    # Button to trigger prediction
    if 'user_inputs' in st.session_state and st.button("Predict Rating Tier"):
        new_data_show_case = pd.DataFrame([st.session_state['user_inputs']], columns=[
            'Dur mins', 'Studio', 'Production_year', 'Genre_primary', 
            'Movie Rating imdb', 'Actor_Famous_1', 'Actress_Famous_1', 
            'Franchise_yes_1', 'US_Box_Office_mn_usd'
        ])
        
        # Preprocessing: Transform the new data using the preprocessor fitted on the training data
        new_data_transformed_show_case = preprocessor_mov_pred_1.transform(new_data_show_case)
    
        # Convert the sparse matrix to a dense matrix (if applicable)
        if hasattr(new_data_transformed_show_case, "toarray"):
            new_data_transformed_dense_show_case = new_data_transformed_show_case.toarray()
        else:
            new_data_transformed_dense_show_case = new_data_transformed_show_case
    
        # Make a prediction using the trained voting classifier model
        new_predictions_show_case = voting_classifier_mov_pred_1.predict(new_data_transformed_dense_show_case)
    
        # Define the function to categorize Predicted TVTs
        def categorize_tier(tier):
            if tier == 0:
                return 'T1 >4.5'
            elif tier == 1:
                return 'T2 between 2.9 and 4.5'
            else:
                return 'T3 less than 2.9'
    
        # Convert the numerical prediction to the categorized tier
        predicted_value_tier = categorize_tier(new_predictions_show_case[0])
    
        # Display the result
        st.write(f"Predicted Rating Category: {predicted_value_tier}")

        # Note with Markdown formatting
        note = (
            "The predicted value tier is determined based on a three-point scale, ranging from highest to lowest. "
            "The tiers are categorized as follows:\n\n"
            "• **T1**: Greater than 4.5 TVTs  \n"
            "• **T2**: Between 2.9 and 4.5 TVTs  \n"
            "• **T3**: Less than 2.9 TVTs  \n"
        )
        st.markdown(note)

# Add the explanatory note for unsuccessful login

elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')

# Add the professional note at the end of the app
st.write("""
---
### Note:
This app leverages machine learning to predict movie ratings, offering insights based on historical data. 
Predictions should be combined with domain expertise. The developer is not responsible for outcomes based solely on the app's predictions. 
For technical details on ML models employed and error metrics, contact:  
**Puneet Sah**  
Mobile: 9820615085  
Email: puneet2k21@gmail.com
""")
