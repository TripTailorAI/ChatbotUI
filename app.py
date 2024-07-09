import os
import streamlit as st
import requests
import json
import pandas as pd
import random
import google.generativeai as genai
from google.colab import userdata
from datetime import datetime, timedelta

# Configure API keys
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = os.environ['MAPS_API_KEY']
weather_api_key = os.environ['WEATHER']
# Include all your existing functions here (get_place_details, get_weather_forecast, etc.)

# Chatbot function
def chatbot(user_message):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(user_message)
    return response.text

# Create the Streamlit app
st.title("MesoP Travel Chatbot")

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    if message['is_user']:
        st.write(f"You: {message['text']}")
    else:
        st.write(f"MesoP: {message['text']}")

# User input
user_input = st.text_input("You:", "")

if st.button("Send") or user_input:
    # Add user message to chat history
    st.session_state.chat_history.append({'is_user': True, 'text': user_input})
    
    # Generate chatbot response
    bot_response = chatbot(user_input)
    
    # Add bot response to chat history
    st.session_state.chat_history.append({'is_user': False, 'text': bot_response})

# Sidebar for itinerary generation
st.sidebar.title("Itinerary Generator")

# Input fields
destination = st.sidebar.text_input("Destination", "Baku")
country = st.sidebar.text_input("Country", "Azerbaijan")
start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")
hotel_name = st.sidebar.text_input("Hotel Name", "Hilton Baku")
purpose_of_stay = st.sidebar.text_input("Purpose of Stay", "Vacation")

if st.sidebar.button("Generate Itinerary"):
    try:
        itineraries = create_travel_itinerary(destination, country, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay)
        
        st.sidebar.write("Generated Itineraries:")
        for itinerary_number, itinerary in enumerate(itineraries, 1):
            st.sidebar.write(f"Itinerary {itinerary_number}")
            for day in itinerary:
                st.sidebar.write(f"Date: {day['date']}")
                st.sidebar.write(f"Weather forecast: {day['weather']}")
                for activity in day['activities']:
                    st.sidebar.write(f"   {activity['time']}: {activity['activity']} at {activity['place']['name']} | Address: {activity['place']['formatted_address']} | Status: {activity['open_status']}")
                st.sidebar.write("")
            st.sidebar.write("")
    except Exception as e:
        st.sidebar.error(f"An error occurred while creating the itinerary: {e}")

