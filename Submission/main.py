import streamlit as st
from place_weather import get_place_details, get_weather_forecast
from get_itinerary import get_daily_itinerary, get_nightlife_itinerary, is_place_in_location, get_place_opening_hours
from output import create_itinerary_pdf, display_itinerary, generate_df, send_to_gsheets, getAccessToken, send_email
from create_itinerary import create_travel_itinerary, create_night_itinerary
from streamlit_page import streamlit_page, streamlit_pageconfig
st.set_page_config(layout="wide")
streamlit_pageconfig()
streamlit_page()

