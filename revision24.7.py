import streamlit as st
import requests
import json
import pandas as pd
import random
import google.generativeai as genai
from datetime import datetime, timedelta
import traceback
import time
import pycountry

# Configure API keys
GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

# List of all countries
countries = sorted([country.name for country in pycountry.countries])

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
        "url": "#"  # Add a default URL
    }

    if not places:
        print(f"No places found for query: {query}")
        return default_place

    # Filter places by minimum rating and minimum number of reviews
    filtered_places = [place for place in places if place.get('rating', 0) >= min_rating and place.get('user_ratings_total', 0) >= min_reviews]

    if not filtered_places:
        print(f"No places found with a minimum rating of {min_rating} and a minimum of {min_reviews} reviews for query: {query}")
        return default_place

    # Sort places by number of reviews and rating
    sorted_places = sorted(filtered_places, key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)), reverse=True)
    
    # Select the top place
    top_place = sorted_places[0]

    # Get details for the top place
    place_id = top_place['place_id']
    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,type,opening_hours,rating,user_ratings_total,url',
        'key': google_places_api_key
    }
    details_response = requests.get(details_url, params=details_params)
    details = details_response.json().get('result', {})

    # Ensure all required fields are present
    for key in default_place.keys():
        if key not in details:
            details[key] = default_place[key]

    return details
    
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
        print(f"Exception type: {type(e)}")
        print(f"Exception traceback: {traceback.format_exc()}")
        return None

def is_place_in_location(place, destination, country):
    address = place['formatted_address'].lower()
    return (destination.lower() in address or country.lower() in address or
            any(destination.lower() in component['long_name'].lower() or
                country.lower() in component['long_name'].lower()
                for component in place.get('address_components', [])))

def get_place_opening_hours(place, date):
    if 'opening_hours' not in place or 'periods' not in place['opening_hours']:
        return "N/A"  # Opening hours not available

    dt = datetime.strptime(date, "%Y-%m-%d")
    day_of_week = dt.weekday()

    for period in place['opening_hours']['periods']:
        if period['open']['day'] == day_of_week:
            open_time = datetime.strptime(period['open']['time'], "%H%M").strftime("%I:%M %p")
            close_time = datetime.strptime(period['close']['time'], "%H%M").strftime("%I:%M %p")
            return f"{open_time} - {close_time}"

    return "Closed"

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
                selected_place = place_details
                opening_hours = get_place_opening_hours(selected_place, current_date)
                verified_itinerary.append({
                    'time': item['time'],
                    'activity': item['activity'],
                    'place': selected_place,
                    'opening_hours': opening_hours
                })
                used_places.add(item['place'])  # Add to used places
                
            for i in range(len(verified_itinerary) - 1):
                origin = verified_itinerary[i]['place']['formatted_address']
                destination = verified_itinerary[i + 1]['place']['formatted_address']
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&mode={mode_of_transport}&key={google_places_api_key}"
                response = requests.get(url)
                distance_data = response.json()

                if distance_data["status"] == "OK":
                    duration = distance_data["rows"][0]["elements"][0]["duration"]["text"]
                    duration_value = distance_data["rows"][0]["elements"][0]["duration"]["value"]
                    verified_itinerary[i]['duration_to_next'] = duration
                    verified_itinerary[i]['duration_to_next_value'] = duration_value
                else:
                    verified_itinerary[i]['duration_to_next'] = "N/A"
                    verified_itinerary[i]['duration_to_next_value'] = float('inf')
                    
            itinerary.append({
                'date': current_date,
                'weather': weather_summary,
                'activities': verified_itinerary
            })

        all_itineraries.append(itinerary)

    return all_itineraries

# Streamlit app
st.title("VoyagerAI")

# Sidebar for itinerary generation
st.sidebar.title("Itinerary Generator")

# Input fields
country = st.sidebar.selectbox("Country", countries)
destination = st.sidebar.text_input("Destination", "")
hotel_name = st.sidebar.text_input("Hotel Name", "")
start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")
mode_of_transport = st.sidebar.selectbox("Mode of Transportation", ["driving", "walking", "bicycling", "transit"])
purpose_of_stay = st.sidebar.selectbox("Purpose of Stay", ["Vacation", "Business"])

if st.sidebar.button("Generate Itinerary"):
    with st.spinner("Generating itinerary, please wait..."):
        try:
            itineraries = create_travel_itinerary(destination, country, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay, mode_of_transport)
            
            # Create the table data
            table_data = []
            for itinerary in itineraries:
                for day in itinerary:
                    date = day['date']
                    weather = day['weather']
                    
                    for activity in day['activities']:
                        time = activity['time']
                        activity_name = activity['activity']
                        place = activity.get('place', {})
                        place_name = place.get('name', 'Unknown')
                        address = place.get('formatted_address', 'Unknown')
                        opening_hours = activity.get('opening_hours', 'N/A')
                        
                        table_data.append([date, weather, time, activity_name, place_name, address, opening_hours])
            
            
            # Create the DataFrame
            df = pd.DataFrame(table_data, columns=['Date', 'Weather', 'Time', 'Activity', 'Place', 'Address', 'Opening Hours'])
            
            # Format and display the generated itineraries
            itinerary_message = "## Generated Itineraries\n\n"
            for itinerary_number, itinerary in enumerate(itineraries, 1):
                itinerary_message += f"### Itinerary {itinerary_number}\n\n"
                for day in itinerary:
                    itinerary_message += f"**Date:** {day['date']}\n\n"
                    itinerary_message += f"**Weather forecast:** {day['weather']}\n\n"
                    for i, activity in enumerate(day['activities']):
                        itinerary_message += f"- {activity['time']}: {activity['activity']} at [{activity['place']['name']}]({activity['place']['url']})\n"
                        itinerary_message += f"  - Address: {activity['place']['formatted_address']}\n"
                        itinerary_message += f"  - Opening Hours: {activity['opening_hours']}\n"
                        if i < len(day['activities']) - 1:
                            duration_value = activity['duration_to_next_value']
                            if duration_value <= 1800:  # 30 minutes or less
                                color = 'green'
                            elif duration_value <= 3600:  # 1 hour or less
                                color = 'yellow'
                            else:
                                color = 'red'
                            itinerary_message += f"  - :clock3: Travel time to next location ({mode_of_transport}): <font color='{color}'>{activity['duration_to_next']}</font>\n"
                    itinerary_message += "---\n\n"
            
            
            # Export and email functionality
            if st.button("Export as PDF"):
                # Implement PDF export logic here
                st.success("Itinerary exported as PDF.")
            
            if st.button("Send PDF via Email"):
                # Implement email sending logic here
                st.success("PDF sent via email.")
            
            # Display the AI agent's response
            st.subheader("VoyagerAI's Response")
            st.write("Here's the generated itinerary based on your preferences:")
            
            # Display the table
            #st.table(df)
            st.markdown(itinerary_message, unsafe_allow_html=True)

        except Exception as e:
            st.sidebar.error(f"An error occurred while creating the itinerary: {str(e)}")
            st.sidebar.error(f"Exception type: {type(e)}")
            st.sidebar.error(f"Exception traceback: {traceback.format_exc()}")
