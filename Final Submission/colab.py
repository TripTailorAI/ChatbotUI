
# To be used when running code in Google Colab

#COLAB
# from google.colab import userdata
# import logging
# logging.basicConfig(level=logging.INFO)
# Configure API keys

#COLAB
# GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
# genai.configure(api_key=GOOGLE_API_KEY)
# google_places_api_key = userdata.get('MAPS_API_KEY')
# weather_api_key = userdata.get('WEATHER')

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