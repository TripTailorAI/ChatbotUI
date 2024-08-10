import streamlit as st
from place_weather import get_place_details, get_weather_forecast
from get_itinerary import get_daily_itinerary, get_nightlife_itinerary, is_place_in_location, get_place_opening_hours
from output import create_itinerary_pdf, display_itinerary, generate_df, send_to_gsheets, getAccessToken, send_email
import time
import pandas as pd

@st.cache_data(ttl=3600)
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
                                
                                # Check if the duration is very short (less than 2 minutes)
                                if duration_value < 120:
                                    verified_itinerary[i]['duration_to_next'] = "Nearby"
                                    verified_itinerary[i]['duration_to_next_value'] = 0
                                else:
                                    verified_itinerary[i]['duration_to_next'] = duration
                                    verified_itinerary[i]['duration_to_next_value'] = duration_value
                            else:
                                verified_itinerary[i]['duration_to_next'] = "Nearby"
                                verified_itinerary[i]['duration_to_next_value'] = 0
                        else:
                            verified_itinerary[i]['duration_to_next'] = "Nearby"
                            verified_itinerary[i]['duration_to_next_value'] = 0
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
    return all_itineraries

@st.cache_data(ttl=3600)
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
                continue

            verified_itinerary = []
            for item in daily_itinerary.values():
                if item['place'] in all_used_places:
                    continue

                place_details = get_place_details(f"{item['place']} in {destination}, {country}", f"{destination}, {country}")
                selected_place = place_details
                opening_hours = get_place_opening_hours(selected_place, current_date)
                verified_itinerary.append({
                    'time': item['time'],
                    'activity': item['activity'],
                    'place': place_details,
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
    return all_itineraries
