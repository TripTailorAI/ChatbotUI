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
import pygsheets
import json
from google.oauth2.service_account import Credentials
#COLAB
# from google.colab import userdata
# import logging
# logging.basicConfig(level=logging.INFO)
# Configure API keys
GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

#COLAB
# GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
# genai.configure(api_key=GOOGLE_API_KEY)
# google_places_api_key = userdata.get('MAPS_API_KEY')
# weather_api_key = userdata.get('WEATHER')

# Initialize session state for message history
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'generated_itineraries' not in st.session_state:
    st.session_state.generated_itineraries = None

if 'all_generated_itineraries' not in st.session_state:
    st.session_state.all_generated_itineraries = []

if 'itinerary_set_count' not in st.session_state:
    st.session_state.itinerary_set_count = 0

# List of all countries
countries = sorted([country.name for country in pycountry.countries])

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=3600)
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
        
def get_nightlife_itinerary(destination, country, date, hotel_name, purpose_of_stay, weather_forecast, day_number, trip_length, used_places, mode_of_transport, custom_preferences):
    used_places_str = ", ".join(used_places)
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
@st.cache_data(ttl=86400)
def is_place_in_location(place, destination, country):
    address = place['formatted_address'].lower()
    return (destination.lower() in address or country.lower() in address or
            any(destination.lower() in component['long_name'].lower() or
                country.lower() in component['long_name'].lower()
                for component in place.get('address_components', [])))

@st.cache_data(ttl=86400)
def get_place_opening_hours(place, date):
    if 'opening_hours' not in place or 'periods' not in place['opening_hours']:
        return "N/A"  # Opening hours not available

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

def create_travel_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay, mode_of_transport, custom_preferences):
    weather_forecast_data = get_weather_forecast(destination)
    num_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    all_itineraries = []
    start_date_dt = pd.to_datetime(start_date)
    all_used_places = set()  # Track used places across all itineraries

    for itinerary_version in range(3):
        itinerary = []
        used_places = set()  # Track used places for this itinerary

        for day in range(num_days):
            current_date = (start_date_dt + pd.Timedelta(days=day)).strftime('%Y-%m-%d')

            weather_summary = next((day['day'] for day in weather_forecast_data['forecast']['forecastday'] if day['date'] == current_date), None)
            if weather_summary:
                weather_summary = f"{weather_summary['condition']['text']}: {weather_summary['maxtemp_c']}°C (max), {weather_summary['mintemp_c']}°C (min)"
            else:
                weather_summary = "Weather data not available"

            daily_itinerary = get_daily_itinerary(destination, country, current_date, hotel_name, purpose_of_stay, weather_summary, day + 1, num_days, all_used_places, mode_of_transport, custom_preferences)

            if daily_itinerary is None:
                # print(f"Error: Failed to get itinerary from GeminiAI for {current_date}")
                print(f"Skipping this day in the itinerary.")
                continue

            verified_itinerary = []
            for item in daily_itinerary.values():
                if item['place'] in all_used_places:
                    # print(f"Skipping repeated place: {item['place']}")
                    continue

                place_details = get_place_details(f"{item['place']} in {destination}, {country}", f"{destination}, {country}")
                selected_place = place_details
                opening_hours = get_place_opening_hours(selected_place, current_date)
                verified_itinerary.append({
                    'time': item['time'],
                    'activity': item['activity'],
                    'place': selected_place,
                    'opening_hours': opening_hours,
                    'time_int': item['time_int'],
                    'approx_distance': item['approx_distance']
                })
                all_used_places.add(item['place'])  # Add to all used places
                used_places.add(item['place'])

            # Only process travel times if there are activities
            if verified_itinerary:
                for i in range(len(verified_itinerary) - 1):
                    origin = verified_itinerary[i]['place']['formatted_address']
                    destination = verified_itinerary[i + 1]['place']['formatted_address']
                    dep_time = verified_itinerary[i + 1]['time_int']
                    act_time = verified_itinerary[i + 1]['time']
                    date_time = current_date+' '+act_time+':00'
                    pattern = '%Y-%m-%d %H:%M:%S'
                    epoch = int(time.mktime(time.strptime(date_time, pattern)))
                    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&mode={mode_of_transport}&key={google_places_api_key}&departure_time={epoch}"
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

                # Set the last activity's duration to "N/A" only if there are activities
                verified_itinerary[-1]['duration_to_next'] = "N/A"
                verified_itinerary[-1]['duration_to_next_value'] = 0

            itinerary.append({
                'date': current_date,
                'weather': weather_summary,
                'activities': verified_itinerary
            })

        all_itineraries.append(itinerary)
    print(all_itineraries)
    return all_itineraries

def create_night_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay, mode_of_transport, custom_preferences):
    weather_forecast_data = get_weather_forecast(destination)
    num_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
    all_itineraries = []
    start_date_dt = pd.to_datetime(start_date)
    all_used_places = set()  # Track used places across all itineraries

    for itinerary_version in range(3):
        itinerary = []
        used_places = set()  # Track used places for this itinerary

        for day in range(num_days):
            current_date = (start_date_dt + pd.Timedelta(days=day)).strftime('%Y-%m-%d')

            weather_summary = next((day['day'] for day in weather_forecast_data['forecast']['forecastday'] if day['date'] == current_date), None)
            if weather_summary:
                weather_summary = f"{weather_summary['condition']['text']}: {weather_summary['maxtemp_c']}°C (max), {weather_summary['mintemp_c']}°C (min)"
            else:
                weather_summary = "Weather data not available"

            daily_itinerary = get_nightlife_itinerary(destination, country, current_date, hotel_name, purpose_of_stay, weather_summary, day + 1, num_days, all_used_places, mode_of_transport, custom_preferences)

            if daily_itinerary is None:
                print(f"Error: Failed to get itinerary from GeminiAI for {current_date}")
                # print(f"Skipping this day in the itinerary.")
                continue

            verified_itinerary = []
            for item in daily_itinerary.values():
                if item['place'] in all_used_places:
                    # print(f"Skipping repeated place: {item['place']}")
                    continue

                place_details = get_place_details(f"{item['place']} in {destination}, {country}", f"{destination}, {country}")
                selected_place = place_details
                opening_hours = get_place_opening_hours(selected_place, current_date)
                verified_itinerary.append({
                    'time': item['time'],
                    'activity': item['activity'],
                    'place': selected_place,
                    'opening_hours': opening_hours,
                    'time_int': item['time_int'],
                    'approx_distance': item['approx_distance']
                })
                all_used_places.add(item['place'])  # Add to all used places
                used_places.add(item['place'])

            # Only process travel times if there are activities
            if verified_itinerary:
                for i in range(len(verified_itinerary) - 1):
                    origin = verified_itinerary[i]['place']['formatted_address']
                    destination = verified_itinerary[i + 1]['place']['formatted_address']
                    dep_time = verified_itinerary[i + 1]['time_int']
                    act_time = verified_itinerary[i + 1]['time']
                    date_time = current_date+' '+act_time+':00'
                    pattern = '%Y-%m-%d %H:%M:%S'
                    epoch = int(time.mktime(time.strptime(date_time, pattern)))
                    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&mode={mode_of_transport}&key={google_places_api_key}&departure_time={epoch}"
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

                # Set the last activity's duration to "N/A" only if there are activities
                verified_itinerary[-1]['duration_to_next'] = "N/A"
                verified_itinerary[-1]['duration_to_next_value'] = 0

            itinerary.append({
                'date': current_date,
                'weather': weather_summary,
                'activities': verified_itinerary
            })

        all_itineraries.append(itinerary)
    print(all_itineraries)
    return all_itineraries

# #COLAB
# def print_itineraries(itineraries):
#     for itinerary_number, itinerary in enumerate(itineraries, 1):
#         print(f"Itinerary {itinerary_number}")
#         print("=" * 50)
#         for day in itinerary:
#             print(f"Date: {day['date']}")
#             print(f"Weather forecast: {day['weather']}")
#             print()
#             for i, activity in enumerate(day['activities'], 1):
#                 #print(f"{i}. {activity['time']}: {activity['activity']} at {activity['place']['name']}")
#                 print(f"- {activity['time']}: {activity['activity']} at [{activity['place']['name']}]({activity['place']['url']})\n")
#                 print(f"  - Address: {activity['place']['formatted_address']}\n")
#                 print(f"  - Opening Hours: {activity['opening_hours']}\n")

#                 if 'duration_to_next' in activity:
#                     print(f"   Travel time to next location: {activity['duration_to_next']}")
#                 print()
#             print("-" * 30)
#         print("\n")

# # Example usage
# destination = "Baku"
# country = "Azerbaijan"
# start_date = "2024-08-01"
# end_date = "2024-08-02"
# hotel_name = "Hilton"
# purpose_of_stay = "Vacation"
# mode_of_transport = "Transit"

# try:
#     itineraries = create_travel_itinerary(destination, country, start_date, end_date, hotel_name, purpose_of_stay, mode_of_transport)
#     print_itineraries(itineraries)
# except Exception as e:
#     print(f"An error occurred while creating the itinerary: {str(e)}")
#     print(f"Exception type: {type(e)}")
#     print(f"Exception traceback: {traceback.format_exc()}")

#--------------------------------------------------------------------------------------------#
def display_itinerary(itinerary, set_number, itinerary_number, mode_of_transport):
    itinerary_message = ""
    day_data = []
    for day in itinerary:
        date = day['date']
        weather = day['weather']
        itinerary_message += f"**Date:** {date}\n\n"
        itinerary_message += f"**Weather forecast:** {weather}\n\n"
        for i, activity in enumerate(day['activities']):
            time = activity['time']
            activity_name = activity['activity']
            place_name = activity['place']['name']
            address = activity['place']['formatted_address']
            opening_hours = activity.get('opening_hours', 'N/A')
            
            itinerary_message += f"- {time}: {activity_name} at [{place_name}]({activity['place'].get('url', '#')})\n"
            itinerary_message += f"  - Address: {address}\n"
            itinerary_message += f"  - Opening Hours: {opening_hours}\n"
            if i < len(day['activities']) - 1:
                duration_value = activity.get('duration_to_next_value', float('inf'))
                duration_text = activity.get('duration_to_next', 'N/A')
                if duration_value <= 1800:  # 30 minutes or less
                    color = 'green'
                elif duration_value <= 3600:  # 1 hour or less
                    color = 'yellow'
                else:
                    color = 'red'
                itinerary_message += f"  - :clock3: Travel time to next location ({mode_of_transport[:-8]}): <font color='{color}'>{duration_text}</font>\n"
            
            day_data.append([date, weather, time, activity_name, place_name, address, opening_hours])
        
        itinerary_message += "---\n\n"
    
    st.markdown(itinerary_message, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Export Itinerary {itinerary_number} as PDF 📄", key=f"export_pdf_{set_number}_{itinerary_number}"):
            # Implement PDF export logic here
            st.success(f"Itinerary {itinerary_number} from Set {set_number} exported as PDF.")
    with col2:
        if st.button(f"Send Itinerary {itinerary_number} via Email 📧", key=f"send_email_{set_number}_{itinerary_number}"):
            send_to_gsheets()
            st.success(f"Itinerary {itinerary_number} from Set {set_number} sent via email.")
    
    return day_data

def generate_df(all_itineraries):
    itinerary_data =[]
    columns = ['itinerary_version','date','weather','time','activity','place','MapsLink','Address','Hours']
    for i, itinerary in enumerate(all_itineraries, 1):
        for day in itinerary:
            for j, activity in enumerate(day['activities'], 1):
                itinerary_data.append([i,day['date'],day['weather']
                                        ,activity['time'],activity['activity']
                                        ,activity['place']['name'],activity['place']['url'],activity['place']['formatted_address']
                                        ,activity['opening_hours']])
    df = pd.DataFrame(itinerary_data)
    df.columns = columns
    return df

def send_to_gsheets():
    if st.session_state.all_generated_itineraries:
        most_recent_set = st.session_state.all_generated_itineraries[-1]
        df = generate_df(most_recent_set)
        
        service_account_info = st.secrets["gcp_service_account"]
        
        # Create credentials object
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        
        # Authorize with pygsheets using the credentials
        gc = pygsheets.authorize(custom_credentials=credentials)
        
        # Rest of your function remains the same
        sheet_id = '1Mw_kkGf8Z5qN2RGhOzIM04zEN30cZIznrOfjWPwNluc'
        worksheet_name = 'Base_Day'
        sh = gc.open_by_key(sheet_id)
        wks = sh.worksheet_by_title(worksheet_name)  # Select the first sheet
        start_cell = 'C2'
        end_cell = 'K500'
        wks.clear(start=start_cell, end=end_cell)
        wks.set_dataframe(df, (1, 3))
        worksheet_name = 'Master'
        wks = sh.worksheet_by_title(worksheet_name)  # Select the first sheet
        wks.update_value("B1", email_address)
        wks.update_value("B2", destination)
        wks.update_value("B3", start_date.strftime("%Y-%m-%d"))
        wks.update_value("B4", end_date.strftime("%Y-%m-%d"))
        return True
    else:
        return False
    
# Streamlit app
st.title("VoyagerAI🌎")
# Short instructions
st.write("""
💡 **How to use VoyagerAI:**
1. Fill in your trip details in the sidebar
2. Add any custom preferences
3. Click 'Generate Itinerary'
4. Review and export your personalized travel plans!
""")

# Sidebar for itinerary generation
st.sidebar.title("Itinerary Generator")

# Input fields
# Email address input
email_address = st.sidebar.text_input("📧 Email Address", "Enter your email address here")
country = st.sidebar.selectbox("🏳️ Country", countries)
destination = st.sidebar.text_input("🏙️ Destination", "")
hotel_name = st.sidebar.text_input("🏨 Hotel Name", "")
start_date = st.sidebar.date_input("🗓️ Start Date")
end_date = st.sidebar.date_input("🗓️ End Date")
purpose_of_stay = st.sidebar.selectbox("🎯 Purpose of Stay", ["Vacation", "Business"])
transport_modes = {
    "🚗 Driving": "driving",
    "🚶 Walking": "walking",
    "🚲 Bicycling": "bicycling",
    "🚊 Transit": "transit"
}
mode_of_transport = st.sidebar.selectbox("🚀 Mode of Transportation", list(transport_modes.keys()))
mode_of_transport_value = transport_modes[mode_of_transport]

# Custom preferences input
custom_preferences = st.sidebar.text_area("✨ Custom Preferences", 
    "Enter any special requirements or preferences for your trip here.")
generate_nightlife = st.sidebar.checkbox("🌙 Generate Nightlife Itinerary", value=False)


if st.sidebar.button("Generate Itinerary"):
    with st.spinner("Generating itinerary, please wait..."):
        try:
            new_day_itineraries = create_travel_itinerary(
                destination, country, start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay, 
                mode_of_transport_value, custom_preferences
            )
            
            new_night_itineraries = None
            if generate_nightlife:
                new_night_itineraries = create_night_itinerary(
                    destination, country, start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay, 
                    mode_of_transport_value, custom_preferences
                )
            
            st.session_state.all_generated_itineraries.append({
                'day': new_day_itineraries,
                'night': new_night_itineraries
            })
            st.session_state.itinerary_set_count += 1
            st.success(f"Itinerary set {st.session_state.itinerary_set_count} generated successfully!")
        except Exception as e:
            st.sidebar.error(f"An error occurred while creating the itinerary: {str(e)}")
            st.sidebar.error(f"Exception type: {type(e)}")
            st.sidebar.error(f"Exception traceback: {traceback.format_exc()}")

if st.session_state.all_generated_itineraries:
    st.subheader("VoyagerAI's Response")
    
    # Create the table data
    table_data = []
    
    # Display the most recently generated itinerary set
    most_recent_set = st.session_state.all_generated_itineraries[-1]
    st.write("## Most Recent Itinerary Set")
    
    day_itineraries = most_recent_set['day']
    night_itineraries = most_recent_set['night']

    for itinerary_number, day_itinerary in enumerate(day_itineraries, 1):
        with st.expander(f"Itinerary {itinerary_number}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("#### Day Itinerary")
                day_data = display_itinerary(day_itinerary, st.session_state.itinerary_set_count, itinerary_number, mode_of_transport)
                table_data.extend(day_data)
            
            with col2:
                st.write("#### Night Itinerary")
                if night_itineraries and itinerary_number <= len(night_itineraries):
                    night_itinerary = night_itineraries[itinerary_number - 1]
                    night_data = display_itinerary(night_itinerary, st.session_state.itinerary_set_count, itinerary_number, mode_of_transport)
                    table_data.extend(night_data)
                else:
                    st.write("No nightlife itinerary for this day.")

    # Display all previously generated itinerary sets in reverse order
    if len(st.session_state.all_generated_itineraries) > 1:
        st.write("## Previously Generated Itinerary Sets")
        for set_number, itinerary_set in reversed(list(enumerate(st.session_state.all_generated_itineraries[:-1], 1))):
            st.write(f"### Itinerary Set {set_number}")
            day_itineraries = itinerary_set['day']
            night_itineraries = itinerary_set['night']
            
            for itinerary_number, day_itinerary in enumerate(day_itineraries, 1):
                with st.expander(f"Itinerary {itinerary_number}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("#### Day Itinerary")
                        day_data = display_itinerary(day_itinerary, set_number, itinerary_number, mode_of_transport)
                        table_data.extend(day_data)
                    
                    with col2:
                        st.write("#### Night Itinerary")
                        if night_itineraries and itinerary_number <= len(night_itineraries):
                            night_itinerary = night_itineraries[itinerary_number - 1]
                            night_data = display_itinerary(night_itinerary, set_number, itinerary_number, mode_of_transport)
                            table_data.extend(night_data)
                        else:
                            st.write("No nightlife itinerary for this day.")

    # Create the DataFrame
    dfi = pd.DataFrame(table_data, columns=['Date', 'Weather', 'Time', 'Activity', 'Place', 'Address', 'Opening Hours'])
    
    # Add the generated itineraries to the message history
    if st.session_state.all_generated_itineraries:
        total_itineraries = sum(len(itinerary_set['day']) for itinerary_set in st.session_state.all_generated_itineraries)
        if generate_nightlife:
            total_itineraries += sum(len(itinerary_set['night']) for itinerary_set in st.session_state.all_generated_itineraries if itinerary_set['night'])
        
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Generated {len(st.session_state.all_generated_itineraries)} set(s) of itineraries for {destination}, {country}. Total itineraries: {total_itineraries}."
    })

   
