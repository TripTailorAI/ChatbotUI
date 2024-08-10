# from streamlit_page import streamlit_page, streamlit_pageconfig
# from streamlit_config import streamlit_pageconfig
import streamlit as st
import requests
import json
import pandas as pd
import random
import google.generativeai as genai
from datetime import datetime, timedelta, date
import traceback
import time
import pycountry
import pygsheets
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
import google.auth.transport.requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

@st.cache_data(ttl=3600,show_spinner=False)
def get_place_details(query, location, radius=5000, min_rating=2.5, min_reviews=5):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': query,
        'location': location,
        'radius': radius,
        'key': google_places_api_key
    }
    response = requests.get(url, params=params)
    places = response.json().get('results', [])

    # Create a default place details dictionary
    default_place = {
        "name": query.split(" in ")[0],
        "formatted_address": f"{query.split(' in ')[1]}",
        "rating": "N/A",
        "user_ratings_total": "N/A",
        "url": "http://maps.google.com/?q="+str(query.split(" in ")[0])  # Add a default URL
    }

    if not places:
        # print(f"No places found for query: {query}")
        return default_place

    # Filter places by minimum rating and minimum number of reviews
    filtered_places = [place for place in places if place.get('rating', 0) >= min_rating and place.get('user_ratings_total', 0) >= min_reviews]

    if not filtered_places:
        # print(f"No places found with a minimum rating of {min_rating} and a minimum of {min_reviews} reviews for query: {query}")
        return default_place

    # Sort places by number of reviews and rating
    sorted_places = sorted(filtered_places, key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)), reverse=True)
    
    # Select the top place
    top_place = sorted_places[0]

    # Get details for the top place
    # place_id = top_place['place_id']
    # details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    # details_params = {
    #     'place_id': place_id,
    #     'fields': 'name,formatted_address,type,opening_hours,rating,user_ratings_total,url',
    #     'key': google_places_api_key
    # }
    # details_response = requests.get(details_url, params=details_params)
    # details = details_response.json().get('result', {})
    # MODIFIED BELOW
    details = {
        "name": top_place['name'],
        "formatted_address": top_place['formatted_address'],
        "type": top_place['type'],
        "opening_hours": top_place['opening_hours'],
        "rating": top_place['rating'],
        "user_ratings_total": top_place['user_ratings_total'],
        'url': f"https://www.google.com/maps/search/{top_place['formatted_address']}" if 'url' in top_place else None
    }

    # Ensure all required fields are present
    for key in default_place.keys():
        if key not in details:
            details[key] = default_place[key]

    return details

@st.cache_data(ttl=3600,show_spinner=False)
def get_weather_forecast(city):
    url = f"https://api.weatherapi.com/v1/forecast.json?key={weather_api_key}&q={city}&days=14"
    response = requests.get(url)

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error decoding JSON response from weather API for city: {city}")
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        raise e