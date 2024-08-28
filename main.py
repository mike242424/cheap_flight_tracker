from dotenv import load_dotenv
import os
from twilio.rest import Client
import requests

# Load environment variables
load_dotenv()

# Fetch environment variables
SHEETY_TOKEN = os.getenv('SHEETY_TOKEN')
SHEETY_API_URL = os.getenv('SHEETY_API_URL')
SERPI_API_KEY = os.getenv("SERPI_API_KEY")
SERPI_GOOGLE_FLIGHTS_BASE_URL = os.getenv("SERPI_GOOGLE_FLIGHTS_BASE_URL")
ACCOUNT_SID = os.getenv('ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
RECIPIENT_PHONE_NUMBER = os.getenv('RECIPIENT_PHONE_NUMBER')

# Set Sheety headers and make API request
sheety_headers = {"Authorization": f"Bearer {SHEETY_TOKEN}"}
sheety_response = requests.get(SHEETY_API_URL, headers=sheety_headers)
sheety_response.raise_for_status()

# Create a dictionary of IATA codes and lowest prices
flight_dictionary = {code['iataCode']: code['lowestPrice'] for code in sheety_response.json()['prices']}

# Initialize Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Iterate over each destination and check for cheaper flights
for iata_code, lowest_price in flight_dictionary.items():
    # Set parameters for SERPI API request
    params = {
        "engine": "google_flights",
        "departure_id": "CHS",
        "arrival_id": iata_code,
        "outbound_date": "2024-08-29",
        "return_date": "2024-09-04",
        "api_key": SERPI_API_KEY,
    }

    # Make SERPI API request
    response = requests.get(url=f'{SERPI_GOOGLE_FLIGHTS_BASE_URL}', params=params)
    response.raise_for_status()
    best_flights = response.json()

    # Check if 'best_flights' key exists
    if 'best_flights' not in best_flights or not best_flights['best_flights']:
        print(f"No best flights found for destination {iata_code}")
        continue

    # Flag to check if any cheaper flight was found
    cheap_flight_found = False

    # Iterate over best flights
    for flight in best_flights['best_flights']:
        if flight['price'] < lowest_price:
            cheap_flight_found = True

            # Identify the first and last flights in the itinerary
            first_flight = flight['flights'][0]
            last_flight = flight['flights'][-1]

            original_departure = first_flight['departure_airport']['name']
            final_destination = last_flight['arrival_airport']['name']

            # Collect all legs of the journey
            flight_details = []
            for single_flight in flight['flights']:
                airline = single_flight['airline']
                flight_number = single_flight['flight_number']
                duration = single_flight['duration']
                flight_details.append(f"{airline} {flight_number} ({duration} min)")

            # Send SMS with the complete flight information
            message_body = (
                    f"Cheap flight found: Departure: {original_departure}, "
                    f"Destination: {final_destination}, Total Duration: {flight['total_duration']} min.\n"
                    f"Flight Details: " + ", ".join(flight_details)
            )
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=RECIPIENT_PHONE_NUMBER,
            )

    # If no cheaper flights were found, print a message
    if not cheap_flight_found:
        print('No cheap flights today...')
