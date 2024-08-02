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

#COLAB
# from google.colab import userdata
# import logging
# logging.basicConfig(level=logging.INFO)
# Configure API keys

#COLAB
# GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
# genai.configure(api_key=GOOGLE_API_KEY)
# google_places_api_key = userdata.get('MAPS_API_KEY')
weather_api_key = userdata.get('WEATHER')

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


    default_place = {
        "name": query.split(" in ")[0],
        "formatted_address": f"{query.split(' in ')[1]}",
        "rating": "N/A",
        "user_ratings_total": "N/A",
        "url": "#"
    }

    if not places:
        print(f"No places found for query: {query}")
        return default_place


    filtered_places = [place for place in places if place.get('rating', 0) >= min_rating and place.get('user_ratings_total', 0) >= min_reviews]

    if not filtered_places:
        print(f"No places found with a minimum rating of {min_rating} and a minimum of {min_reviews} reviews for query: {query}")
        return default_place


    sorted_places = sorted(filtered_places, key=lambda x: (x.get('user_ratings_total', 0), x.get('rating', 0)), reverse=True)


    top_place = sorted_places[0]


    place_id = top_place['place_id']
    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,type,opening_hours,rating,user_ratings_total,url',
        'key': google_places_api_key
    }
    details_response = requests.get(details_url, params=details_params)
    details = details_response.json().get('result', {})


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

def get_daily_itinerary(destination, country, date, hotel_name, purpose_of_stay, weather_forecast, day_number, trip_length, used_places, mode_of_transport):
    used_places_str = ", ".join(used_places)
    user_message = f"""
    Create a detailed itinerary for day {day_number} of a {trip_length}-day trip to {destination}, {country}.
    Date: {date}
    Staying at: {hotel_name}
    Purpose of stay: {purpose_of_stay}
    Weather forecast: {weather_forecast}
    Mode of transportation: {mode_of_transport}

    Please provide a full days itinerary with suggested times for each activity. Include local meals, sightseeing, and other relevant activities.
    Be specific with place names and try to suggest a variety of activities suitable for the destination, weather, and transportation mode.

    Important guidelines:
    1. Do not include breakfast or any activities at the hotel.
    2. Start the itinerary with the first activity outside the hotel.
    3. Do not repeat any place names within the same itinerary. Each day should have unique activities.
    4. The following places have already been used in previous days and should not be suggested again: {used_places_str}
    5. Ensure all suggested places are within {destination}. Do not suggest places in other cities.
    6. Consider the mode of transportation when suggesting places. If the mode is walking, keep destinations closer together.

    Format the output as a JSON object with each entry containing:
    - time: suggested time for the activity (e.g., "09:00")
    - activity: short description of the activity
    - place: specific name of the place to visit

    Example format:
    {{
        "1": {{"time": "09:30", "activity": "Morning walk", "place": "Specific Park Name"}},
        "2": {{"time": "11:00", "activity": "Visit museum", "place": "Specific Museum Name"}},
        ...
    }}
    """


    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(user_message)
    # print(response)
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

def get_place_opening_hours(place, date):
    if 'opening_hours' not in place or 'periods' not in place['opening_hours']:
        return "N/A"

    dt = datetime.strptime(date, "%Y-%m-%d")
    day_of_week = dt.weekday()

    for period in place['opening_hours']['periods']:
        if period['open']['day'] == day_of_week:
            open_time = datetime.strptime(period['open']['time'], "%H%M").strftime("%I:%M %p")
            if 'close' not in period:
                # Place might be open 24/7
                return f"{open_time} - Open 24 hours"
            close_time = datetime.strptime(period['close']['time'], "%H%M").strftime("%I:%M %p")
            return f"{open_time} - {close_time}"

    return "Closed"
    
def create_travel_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay, mode_of_transport):
    weather_forecast_data = get_weather_forecast(destination)
    num_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    all_itineraries = []
    start_date_dt = pd.to_datetime(start_date)
    all_used_places = set()

    for itinerary_version in range(3):
        itinerary = []
        used_places = set()

        for day in range(num_days):
            current_date = (start_date_dt + pd.Timedelta(days=day)).strftime('%Y-%m-%d')

            weather_summary = next((day['day'] for day in weather_forecast_data['forecast']['forecastday'] if day['date'] == current_date), None)
            if weather_summary:
                weather_summary = f"{weather_summary['condition']['text']}: {weather_summary['maxtemp_c']}°C (max), {weather_summary['mintemp_c']}°C (min)"
            else:
                weather_summary = "Weather data not available"

            daily_itinerary = get_daily_itinerary(destination, country, current_date, hotel_name, purpose_of_stay, weather_summary, day + 1, num_days, all_used_places, mode_of_transport)

            if daily_itinerary is None:
                print(f"Error: Failed to get itinerary for {current_date}")
                continue

            verified_itinerary = []
            for item in daily_itinerary.values():
                if item['place'] in all_used_places:
                    print(f"Skipping repeated place: {item['place']}")
                    continue

                place_details = get_place_details(f"{item['place']} in {destination}, {country}", f"{destination}, {country}")
                opening_hours = get_place_opening_hours(place_details, current_date)
                verified_itinerary.append({
                    'time': item['time'],
                    'activity': item['activity'],
                    'place': place_details,
                    'opening_hours': opening_hours
                })
                all_used_places.add(item['place'])
                used_places.add(item['place'])

            for i in range(len(verified_itinerary) - 1):
                origin = verified_itinerary[i]['place']['formatted_address']
                destination = verified_itinerary[i + 1]['place']['formatted_address']
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&mode={mode_of_transport}&key={google_places_api_key}"
                response = requests.get(url)
                distance_data = response.json()

                if distance_data["status"] == "OK":
                    if (distance_data.get("rows") and
                        distance_data["rows"][0].get("elements") and
                        distance_data["rows"][0]["elements"][0].get("status") == "OK"):

                        element = distance_data["rows"][0]["elements"][0]
                        if "duration" in element:
                            duration = element["duration"]["text"]
                            duration_value = element["duration"]["value"]
                            verified_itinerary[i]['duration_to_next'] = duration
                            verified_itinerary[i]['duration_to_next_value'] = duration_value
                        else:
                            verified_itinerary[i]['duration_to_next'] = "Unable to calculate duration"
                            verified_itinerary[i]['duration_to_next_value'] = float('inf')
                    else:
                        verified_itinerary[i]['duration_to_next'] = "Route not found"
                        verified_itinerary[i]['duration_to_next_value'] = float('inf')
                else:
                    verified_itinerary[i]['duration_to_next'] = f"API Error: {distance_data['status']}"
                    verified_itinerary[i]['duration_to_next_value'] = float('inf')

            itinerary.append({
                'date': current_date,
                'weather': weather_summary,
                'activities': verified_itinerary
            })

        all_itineraries.append(itinerary)
    logging.info(f"Distance Matrix API response: {distance_data}")

    return all_itineraries

def print_itineraries(itineraries):
    for itinerary_number, itinerary in enumerate(itineraries, 1):
        print(f"Itinerary {itinerary_number}")
        print("=" * 50)
        for day in itinerary:
            print(f"Date: {day['date']}")
            print(f"Weather forecast: {day['weather']}")
            print()
            for i, activity in enumerate(day['activities'], 1):
                #print(f"{i}. {activity['time']}: {activity['activity']} at {activity['place']['name']}")
                print(f"- {activity['time']}: {activity['activity']} at [{activity['place']['name']}]({activity['place']['url']})\n")
                print(f"  - Address: {activity['place']['formatted_address']}\n")
                print(f"  - Opening Hours: {activity['opening_hours']}\n")

                if 'duration_to_next' in activity:
                    print(f"   Travel time to next location: {activity['duration_to_next']}")
                print()
            print("-" * 30)
        print("\n")

# Example usage
destination = "Baku"
country = "Azerbaijan"
start_date = "2024-08-01"
end_date = "2024-08-02"
hotel_name = "Hilton"
purpose_of_stay = "Vacation"
mode_of_transport = "Transit"

try:
    itineraries = create_travel_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay, mode_of_transport)
    print_itineraries(itineraries)
except Exception as e:
    print(f"An error occurred while creating the itinerary: {str(e)}")
    print(f"Exception type: {type(e)}")
    print(f"Exception traceback: {traceback.format_exc()}")