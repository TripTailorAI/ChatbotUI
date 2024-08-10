import streamlit as st
import pycountry
from datetime import datetime, timedelta, date
import traceback
from io import BytesIO
from place_weather import get_place_details, get_weather_forecast
from get_itinerary import get_daily_itinerary, get_nightlife_itinerary
from output import create_itinerary_pdf, display_itinerary, generate_df, send_to_gsheets, getAccessToken, send_email
from create_itinerary import create_travel_itinerary, create_night_itinerary
import time
import pandas as pd

def streamlit_pageconfig():
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'generated_itineraries' not in st.session_state:
        st.session_state.generated_itineraries = None

    if 'all_generated_itineraries' not in st.session_state:
        st.session_state.all_generated_itineraries = []

    if 'itinerary_set_count' not in st.session_state:
        st.session_state.itinerary_set_count = 0

    if 'custom_preferences' not in st.session_state:
        st.session_state.custom_preferences = ""

    if 'email_address' not in st.session_state:
        st.session_state.email_address = ""

    if 'country' not in st.session_state:
        st.session_state.country = ""
    if 'destination' not in st.session_state:
        st.session_state.destination = ""
        
    if 'hotel_name' not in st.session_state:
        st.session_state.hotel_name = ""
        
    if 'start_date' not in st.session_state:
        st.session_state.start_date = date.today() + timedelta(days=1)
        
    if 'end_date' not in st.session_state:
        st.session_state.end_date = date.today() + timedelta(days=1)
        
    if 'purpose_of_stay' not in st.session_state:
        st.session_state.purpose_of_stay = "Vacation"
        
    if 'mode_of_transport' not in st.session_state:
        st.session_state.mode_of_transport = "🚗 Driving"
        
    if 'custom_preferences' not in st.session_state:
        st.session_state.custom_preferences = ""

    # List of all countries

countries = sorted([country.name for country in pycountry.countries])

def streamlit_page():
    # Streamlit app
    st.title("TripTailorAI🌎")
    # Short instructions
    st.write("""
    💡 **How to use TripTailorAI:**
    1. Fill in your trip details in the sidebar
    2. Add any custom preferences
    3. Click 'Generate Itineraries'
    4. Review and export your personalized travel plans!
    """)

    # Sidebar for itinerary generation
    st.sidebar.title("Itinerary Generator")

    # Input fields
    # Email address input
    email_address = st.sidebar.text_input(
        "📧 Email Address",
        value=st.session_state.email_address,
        key="email_input",
    )
    st.session_state.email_address = email_address

    country = st.sidebar.selectbox("🏳️ Country", countries, index=countries.index(st.session_state.country) if st.session_state.country in countries else 0)
    st.session_state.country = country

    destination = st.sidebar.text_input("🏙️ Destination", value=st.session_state.destination)
    st.session_state.destination = destination

    hotel_name = st.sidebar.text_input("🏨 Hotel Name", value=st.session_state.hotel_name)
    st.session_state.hotel_name = hotel_name

    today = date.today()
    tomorrow = today + timedelta(days=1)

    start_date = st.sidebar.date_input("🗓️ Start Date", min_value=tomorrow, value=st.session_state.start_date)
    st.session_state.start_date = start_date

    end_date = st.sidebar.date_input("🗓️ End Date", min_value=tomorrow, value=st.session_state.end_date)
    st.session_state.end_date = end_date

    purpose_of_stay = st.sidebar.selectbox("🎯 Purpose of Stay", ["Vacation", "Business"], index=["Vacation", "Business"].index(st.session_state.purpose_of_stay))
    st.session_state.purpose_of_stay = purpose_of_stay

    transport_modes = {
        "🚗 Driving": "driving",
        "🚶 Walking": "walking",
        "🚲 Bicycling": "bicycling",
        "🚊 Transit": "transit"
    }
    mode_of_transport = st.sidebar.selectbox("🚀 Mode of Transportation", list(transport_modes.keys()))
    st.session_state.mode_of_transport = mode_of_transport
    mode_of_transport_value = transport_modes[mode_of_transport]

    custom_preferences = st.sidebar.text_input("✨ Custom Preferences", 
        value=st.session_state.custom_preferences,
        key="custom_pref_input",
        help="Enter any special requirements or preferences for your trip here.")

    st.session_state.custom_preferences = custom_preferences

    if 'generate_nightlife' not in st.session_state:
        st.session_state.generate_nightlife = False

    # In the sidebar, where you create the checkbox:
    st.sidebar.checkbox(
        "🌙 Generate Nightlife Itinerary",
        key="generate_nightlife"
    )


    if st.sidebar.button("✍ Generate Itineraries"):
        with st.spinner("Generating itinerary, please wait..."):
            try:
                start_time = time.time()
                new_day_itineraries = create_travel_itinerary(
                    destination, country, start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay, 
                    mode_of_transport_value, custom_preferences
                )
                day_time = time.time() - start_time

                new_night_itineraries = None
                if st.session_state.generate_nightlife:
                    new_night_itineraries = create_night_itinerary(
                        destination, country, start_date.strftime("%Y-%m-%d"), 
                        end_date.strftime("%Y-%m-%d"), hotel_name, purpose_of_stay, 
                        mode_of_transport_value, custom_preferences
                    )
                
                st.session_state.all_generated_itineraries.append({
                    'trip_details': {
                        'destination': destination,
                        'country': country,
                        'start_date': start_date.strftime("%Y-%m-%d"),
                        'end_date': end_date.strftime("%Y-%m-%d"),
                        'hotel_name': hotel_name,
                        'purpose_of_stay': purpose_of_stay,
                        'mode_of_transport': mode_of_transport,
                    },
                    'day': new_day_itineraries,
                    'night': new_night_itineraries
                })
                st.session_state.itinerary_set_count += 1
                end_time = time.time()  # Stop the timer
                elapsed_time = end_time - start_time  # Calculate elapsed time
                #st.markdown(elapsed_time)
                st.success(f"Itinerary set {st.session_state.itinerary_set_count} generated successfully!")
            except Exception as e:
                st.sidebar.error(f"An error occurred while creating the itinerary: {str(e)}")
                st.sidebar.error(f"Exception type: {type(e)}")
                st.sidebar.error(f"Exception traceback: {traceback.format_exc()}")


    if st.session_state.all_generated_itineraries:
        st.subheader("TripTailorAI's Response")
        # Create the table data
        table_data = []        
        # Display the most recently generated itinerary set
        most_recent_set = st.session_state.all_generated_itineraries[-1]
        st.write("## Most Recent Itineraries")
        if isinstance(most_recent_set, dict):
            day_itineraries = most_recent_set.get('day', [])
            night_itineraries = most_recent_set.get('night') if st.session_state.generate_nightlife else None
        else:
            day_itineraries = most_recent_set
            night_itineraries = None

        for itinerary_number, day_itinerary in enumerate(day_itineraries, 1):
            with st.expander(f"Itinerary {itinerary_number}", expanded=True):
                if st.session_state.generate_nightlife:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("#### 🌇 Day Itinerary")
                        day_data = display_itinerary(day_itinerary, st.session_state.itinerary_set_count, itinerary_number, mode_of_transport)
                        table_data.extend(day_data)
                    
                    with col2:
                        st.write("#### 🌃 Night Itinerary ")
                        if night_itineraries and itinerary_number <= len(night_itineraries):
                            night_itinerary = night_itineraries[itinerary_number - 1]
                            night_data = display_itinerary(night_itinerary, st.session_state.itinerary_set_count, itinerary_number, mode_of_transport)
                            table_data.extend(night_data)
                        else:
                            st.write("No nightlife itinerary for this day.")
                else:
                    st.write("#### Day Itinerary")
                    day_data = display_itinerary(day_itinerary, st.session_state.itinerary_set_count, itinerary_number, mode_of_transport)
                    table_data.extend(day_data)

        # Display all previously generated itinerary sets in reverse order
        if len(st.session_state.all_generated_itineraries) > 1:
            st.write("## Previously Generated Itineraries")
            for set_number, itinerary_set in reversed(list(enumerate(st.session_state.all_generated_itineraries[:-1], 1))):
                trip_details = itinerary_set.get('trip_details')
                st.write(f"#### Trip Destination: {trip_details['destination']}, {trip_details['country']}")
                st.write(f"#### Date: {trip_details['start_date']} - {trip_details['end_date']}")
            
                if isinstance(itinerary_set, dict):
                    day_itineraries = itinerary_set.get('day', [])
                    night_itineraries = itinerary_set.get('night') if st.session_state.generate_nightlife else None
                else:
                    day_itineraries = itinerary_set
                    night_itineraries = None
                
                for itinerary_number, day_itinerary in enumerate(day_itineraries, 1):
                    with st.expander(f"Itinerary {itinerary_number}", expanded=False):
                        if st.session_state.generate_nightlife:
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
                        else:
                            st.write("#### Day Itinerary")
                            day_data = display_itinerary(day_itinerary, set_number, itinerary_number, mode_of_transport)
                            table_data.extend(day_data)

        # Create the DataFrame
        dfi = pd.DataFrame(table_data, columns=['Date', 'Weather', 'Time', 'Activity', 'Place', 'Address', 'Opening Hours'])
        
        # Add the generated itineraries to the message history
        if st.session_state.all_generated_itineraries:
            total_itineraries = sum(len(itinerary_set) for itinerary_set in st.session_state.all_generated_itineraries)
            
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Generated {len(st.session_state.all_generated_itineraries)} set(s) of itineraries for {destination}, {country}. Total itineraries: {total_itineraries}."
        })

        if st.sidebar.button("Email All Itineraries", key="export_all_itineraries"):
            if send_to_gsheets():
                arguments = ['V1','V2','V3']
                send_email(arguments)
                st.sidebar.success("Most recent itinerary set exported successfully!")
            else:
                st.sidebar.error("No itineraries to export. Please generate an itinerary first.")


        # Add the generated itineraries to the message history
        if st.session_state.all_generated_itineraries:
            total_itineraries = sum(len(itinerary_set) for itinerary_set in st.session_state.all_generated_itineraries)
            
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Generated {len(st.session_state.all_generated_itineraries)} set(s) of itineraries for {destination}, {country}. Total itineraries: {total_itineraries}."
        })