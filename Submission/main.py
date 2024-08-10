from streamlit_page import streamlit_page, streamlit_pageconfig
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
from place_weather import get_place_details, get_weather_forecast
from get_itinerary import get_daily_itinerary, get_nightlife_itinerary
from output import create_itinerary_pdf, display_itinerary, generate_df, send_to_gsheets, getAccessToken, send_email
from create_itinerary import create_travel_itinerary, create_night_itinerary
st.set_page_config(layout="wide")

streamlit_pageconfig()

streamlit_page()

GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)
google_places_api_key = st.secrets['MAPS_API_KEY']
weather_api_key = st.secrets['WEATHER']

pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
