import streamlit as st
from datetime import datetime, timedelta, date
@st.cache_data(ttl=3600)
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