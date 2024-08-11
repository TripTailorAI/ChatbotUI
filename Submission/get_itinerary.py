import streamlit as st
import json
import google.generativeai as genai
from datetime import datetime
import traceback


GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

@st.cache_data(ttl=3600,show_spinner=False)
def get_daily_itinerary(destination, country, date, hotel_name, purpose_of_stay, weather_forecast, day_number, trip_length, used_places, mode_of_transport, custom_preferences):
    used_places_str = ", ".join(used_places)
    user_message = f"""
    Create a detailed itinerary for day {day_number} of a {trip_length}-day trip to {destination}, {country}.
    Date: {date}
    Staying at: {hotel_name}
    Purpose of stay: {purpose_of_stay}
    Weather forecast: {weather_forecast}
    Mode of transportation: {mode_of_transport}
    Custom preferences: {custom_preferences}

    Please provide a full days itinerary with suggested times for each activity. Include local meals, sightseeing, and other relevant activities.
    Be specific with place names and try to suggest a variety of activities suitable for the destination, weather, and transportation mode.

    Important guidelines:
    1. Do not include breakfast or any activities at the hotel.
    2. Start the itinerary with the first activity outside the hotel.
    3. Do not repeat any place names within the same itinerary. Each day should have unique activities.
    4. The following places have already been used in previous days and should not be suggested again: {used_places_str}
    5. Ensure all suggested places are within {destination}. Do not suggest places in other cities or more than 2 hours away from the city.
    6. Consider the mode of transportation when suggesting places. If the mode is walking, keep destinations closer together.
    7. Take into account the custom preferences provided by the user.
    8. End the itinerary with going back to the place the person is staying at.
    9. The person will always be staying at the hotel that is within the same city of destination. If you cannot find a hotel by that name in the same city, assume that the person is staying somewhere within the city centre main station.
    10. Aim for a diverse range of activities across the entire trip. If a specific activity or cuisine is requested in custom preferences, include it once or twice during the trip, not every day.
    11. Consider the {trip_length} when distributing activitiec.
    12. If a specific food or cuisine is mentioned in the custom preferences, suggest it for one meal, but vary other meal suggestions, do not suggest the same meal for multiple days in a row.
    13. For multi-day trips, try to group activities by area each day to minimize travel time.

    Format the output as a JSON object with each entry containing:
    - time: suggested time for the activity on date: {date} in the local timezone of the place (for example 09:00)
    - activity: short description of the activity
    - place: specific name of the place to visit
    - time_int: suggested time for the activity on date: {date} in the local timezone of the place (for example 09:00) but as an integer in seconds since midnight, January 1, 1970 UTC
    - approx_distance : approximate distance in kms from the main train station

    Example format:
    {{
        "1": {{"time": "09:30", "activity": "Morning walk", "place": "Specific Park Name","time_int":"1722562818","approx_distance":"2.6 kms"}},
        "2": {{"time": "11:00", "activity": "Visit museum", "place": "Specific Museum Name","time_int":"1722572818","approx_distance":"2.6 kms"}},
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
        
@st.cache_data(ttl=3600,show_spinner=False)
def get_nightlife_itinerary(destination, country, date, hotel_name, purpose_of_stay, weather_forecast, day_number, trip_length, used_places, mode_of_transport, custom_preferences):
    # used_places_str = ", ".join(used_places)
    user_message = f"""
    Create a daily nightlife itinerary starting for day {day_number} of a {trip_length}-day trip to {destination}, {country}.
    It should start from 22:00 on {date} and end at 04:00 the next day
    Date: {date}
    Staying at: {hotel_name}
    Purpose of stay: {purpose_of_stay}
    Weather forecast: {weather_forecast}
    Mode of transportation: {mode_of_transport}
    Custom preferences: {custom_preferences}

    Please provide the nightlife itinerary with suggested times for each place. Be specific with place names and try to suggest special events if any.

    Important guidelines:
    1. Do not repeat any place names within the same itinerary. Each day should have unique places.
    2. Include atleast 1 local pub or bar
    3. Check if events exist at Resident Advisor Guide in the city.
    5. Ensure all suggested places are within {destination}. Do not suggest places in other cities or more than 2 hours away from the city.
    6. Ignore the mode of transportation when suggesting places.
    7. Take into account the custom preferences provided by the user.
    8. End the itinerary with going back to the place the person is staying at around 03:30 in the morning next day.
    9. The person will always be staying at the hotel that is within the same city of destination. If you cannot find a hotel by that name in the same city, assume that the person is staying somewhere within the city centre main station.

    Format the output as a JSON object with each entry containing:
    - time: suggested time for the activity on date: {date} in the local timezone of the place (for example 09:00)
    - activity: short description of the activity
    - place: specific name of the place to visit
    - time_int: suggested time for the activity on date: {date} in the local timezone of the place (for example 09:00) but as an integer in seconds since midnight, January 1, 1970 UTC
    - approx_distance : approximate distance in kms from the main train station

    Example format:
    {{
        "1": {{"time": "09:30", "activity": "Morning walk", "place": "Specific Park Name","time_int":"1722562818","approx_distance":"2.6 kms"}},
        "2": {{"time": "11:00", "activity": "Visit museum", "place": "Specific Museum Name","time_int":"1722572818","approx_distance":"2.6 kms"}},
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

@st.cache_data(ttl=3600,show_spinner=False)
def is_place_in_location(place, destination, country):
    address = place['formatted_address'].lower()
    return (destination.lower() in address or country.lower() in address or
            any(destination.lower() in component['long_name'].lower() or
                country.lower() in component['long_name'].lower()
                for component in place.get('address_components', [])))

@st.cache_data(ttl=3600,show_spinner=False)
def get_place_opening_hours(place, date):
    if 'opening_hours' not in place or 'periods' not in place['opening_hours']:
        return "Opening hours not available" 

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