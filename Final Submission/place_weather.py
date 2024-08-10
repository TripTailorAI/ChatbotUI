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
        "url": "http://maps.google.com/?q="+str(query.split(" in ")[0])  # Add a default URL
    }

    if not places:
        # print(f"No places found for query: {query}")
        return default_place

    # Filter places by minimum rating and minimum number of reviews
    filtered_places = [place for place in places if place.get('rating', 0) >= min_rating and place.get('user_ratings_total', 0) >= min_reviews]

    if not filtered_places:
        # print(f"No places found with a minimum rating of {min_rating} and a minimum of {min_reviews} reviews for query: {query}")
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