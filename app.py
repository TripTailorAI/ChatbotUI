import streamlit as st
import requests
import json
import pandas as pd
import random
import google.generativeai as genai
from datetime import datetime, timedelta

# Configure API keys
GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

def get_place_details(query, location, radius=5000, min_rating=3.5):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        'query': query,
        'location': location,
        'radius': radius,
        'key': google_places_api_key
    }
    response = requests.get(url, params=params)
    places = response.json().get('results', [])

    if not places:
        print(f"No places found for query: {query}")
        return None

    # Filter places by minimum rating
    filtered_places = [place for place in places if place.get('rating', 0) >= min_rating]

    if not filtered_places:
        print(f"No places found with a minimum rating of {min_rating} for query: {query}")
        return None

    # Sort places by number of reviews and rating
    sorted_places = sorted(filtered_places, key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)), reverse=True)
    
    # Select the top place
    top_place = sorted_places[0]

    # Get details for the top place
    place_id = top_place['place_id']
    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,type,opening_hours,rating,user_ratings_total',
        'key': google_places_api_key
    }
    details_response = requests.get(details_url, params=details_params)
    details = details_response.json().get('result', {})

    return details

def get_weather_forecast(city):
    url = f"https://api.weatherapi.com/v1/forecast.json?key={weather_api_key}&q={city}&days=14"
    response = requests.get(url)
    return response.json()

def get_daily_itinerary(destination, country, date, hotel_name, purpose_of_stay, weather_forecast, day_number, trip_length, used_places):
    used_places_str = ", ".join(used_places)
    user_message = f"""
    Create a detailed itinerary for day {day_number} of a {trip_length}-day trip to {destination}, {country}.
    Date: {date}
    Staying at: {hotel_name}
    Purpose of stay: {purpose_of_stay}
    Weather forecast: {weather_forecast}

    Please provide a full day's itinerary with suggested times for each activity. Include meals, sightseeing, and any other relevant activities.
    Be specific with place names and try to suggest a variety of activities suitable for the destination and weather.
    IMPORTANT: Do not repeat any place names within the same itinerary. Each day should have unique activities.
    The following places have already been used in previous days and should not be suggested again: {used_places_str}

    Format the output as a JSON object with each entry containing:
    - time: suggested time for the activity (e.g., "09:00")
    - activity: short description of the activity
    - place: specific name of the place to visit

    Example format:
    {{
        "1": {{"time": "09:00", "activity": "Breakfast", "place": "Specific Cafe Name"}},
        "2": {{"time": "10:30", "activity": "Morning sightseeing", "place": "Specific Landmark Name"}},
        ...
    }}
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(user_message)

    try:
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_str = response_text[json_start:json_end]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error processing Gemini response: {e}")
        print(f"Response: {response}")
        return None

def is_place_in_location(place, destination, country):
    address = place['formatted_address'].lower()
    return (destination.lower() in address or country.lower() in address or
            any(destination.lower() in component['long_name'].lower() or
                country.lower() in component['long_name'].lower()
                for component in place.get('address_components', [])))

def is_place_open(place, date, time):
    if 'opening_hours' not in place or 'periods' not in place['opening_hours']:
        return None  # Unknown if open or closed

    dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    day_of_week = dt.weekday()

    for period in place['opening_hours']['periods']:
        if period['open']['day'] == day_of_week:
            open_time = datetime.strptime(period['open']['time'], "%H%M").time()
            close_time = datetime.strptime(period['close']['time'], "%H%M").time()
            if open_time <= dt.time() <= close_time:
                return True

    return False

def create_travel_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay):
    weather_forecast_data = get_weather_forecast(destination)
    num_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    all_itineraries = []
    start_date_dt = pd.to_datetime(start_date)

    for itinerary_version in range(3):
        itinerary = []
        used_places = set()  # Track used places for the entire itinerary

        for day in range(num_days):
            current_date = (start_date_dt + pd.Timedelta(days=day)).strftime('%Y-%m-%d')

            weather_summary = next((day['day'] for day in weather_forecast_data['forecast']['forecastday'] if day['date'] == current_date), None)
            if weather_summary:
                weather_summary = f"{weather_summary['condition']['text']}: {weather_summary['maxtemp_c']}°C (max), {weather_summary['mintemp_c']}°C (min)"
            else:
                weather_summary = "Weather data not available"

            daily_itinerary = get_daily_itinerary(destination, country, current_date, hotel_name, purpose_of_stay, weather_summary, day + 1, num_days, used_places)

            if daily_itinerary is None:
                print(f"Error: Failed to get itinerary from GeminiAI for {current_date}")
                print(f"Skipping this day in the itinerary.")
                continue

            verified_itinerary = []
            for item in daily_itinerary.values():
                if item['place'] in used_places:
                    print(f"Skipping repeated place: {item['place']}")
                    continue

                place_details = get_place_details(f"{item['place']} in {destination}, {country}", f"{destination}, {country}")
                if place_details:
                    selected_place = place_details[0]  # Take the first match
                    if is_place_in_location(selected_place, destination, country):
                        verified_itinerary.append({
                            'time': item['time'],
                            'activity': item['activity'],
                            'place': selected_place
                        })
                        used_places.add(item['place'])  # Add to used places
                    else:
                        print(f"Skipping {item['place']} as it might not be in {destination}, {country}")
                else:
                    print(f"No place details found for {item['place']} in {destination}, {country}")

            itinerary.append({
                'date': current_date,
                'weather': weather_summary,
                'activities': verified_itinerary
            })

        all_itineraries.append(itinerary)

    return all_itineraries

# Chatbot function
st.title("VoyagerAI")

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    st.markdown(message['text'])

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
        
        # Format and display the generated itineraries
        itinerary_message = "## Generated Itineraries\n\n"
        for itinerary_number, itinerary in enumerate(itineraries, 1):
            itinerary_message += f"### Itinerary {itinerary_number}\n\n"
            for day in itinerary:
                itinerary_message += f"**Date:** {day['date']}\n\n"
                itinerary_message += f"**Weather forecast:** {day['weather']}\n\n"
                for activity in day['activities']:
                    itinerary_message += f"- {activity['time']}: {activity['activity']} at **{activity['place']['name']}**\n"
                    itinerary_message += f"  - Address: {activity['place']['formatted_address']}\n"
                itinerary_message += "---\n\n"
        
        st.session_state.chat_history.append({'text': itinerary_message})
        st.experimental_rerun()  # Automatically rerun the app to display the updated output
    except Exception as e:
        st.sidebar.error(f"An error occurred while creating the itinerary: {str(e)}")
        st.sidebar.error(f"Exception type: {type(e)}")
        st.sidebar.error(f"Exception traceback: {traceback.format_exc()}")
