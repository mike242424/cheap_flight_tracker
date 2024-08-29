from dotenv import load_dotenv
import os
import requests
import smtplib

# Load environment variables
load_dotenv()

# Fetch environment variables
SHEETY_TOKEN = os.getenv('SHEETY_TOKEN')
SHEETY_API_URL = os.getenv('SHEETY_API_URL')
SERPI_API_KEY = os.getenv("SERPI_API_KEY")
SERPI_GOOGLE_FLIGHTS_BASE_URL = os.getenv("SERPI_GOOGLE_FLIGHTS_BASE_URL")
MY_EMAIL = os.getenv("MY_EMAIL")
MY_PASSWORD = os.getenv("MY_PASSWORD")

# Set Sheety headers and make Sheety user API request
sheety_headers = {"Authorization": f"Bearer {SHEETY_TOKEN}"}
sheety_users_response = requests.get(f'{SHEETY_API_URL}/users', headers=sheety_headers)
sheety_users_response.raise_for_status()

# Create empty email list
email_list = [item['whatIsYourEmail?'] for item in sheety_users_response.json()['users']]

# Make Sheety prices API request
sheety_price_response = requests.get(f'{SHEETY_API_URL}/prices', headers=sheety_headers)
sheety_price_response.raise_for_status()

# Create a dictionary of IATA codes and lowest prices
flight_dictionary = {code['iataCode']: code['lowestPrice'] for code in sheety_price_response.json()['prices']}

# Initialize a list to store all flight deal messages
all_flight_deals = []

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

    # Iterate over best flights
    for flight in best_flights['best_flights']:
        if flight['price'] < lowest_price:
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

            # Append the flight deal message to the all_flight_deals list
            flight_deal_message = (
                f"Cheap flight found: Departure: {original_departure}, "
                f"Destination: {final_destination}, Total Duration: {flight['total_duration']} min.\n"
                f"Flight Details: " + ", ".join(flight_details) + "\n\n"
            )
            all_flight_deals.append(flight_deal_message)

# If there are any flight deals, send an email to the users
if all_flight_deals:
    # Combine all flight deal messages into one email body
    email_body = "Here are the latest flight deals:\n\n" + "\n".join(all_flight_deals)

    # Send the email to every email in the email list
    for email in email_list:
        with smtplib.SMTP(host='smtp.gmail.com', port=587) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=MY_PASSWORD)
            connection.sendmail(
                from_addr=MY_EMAIL,
                to_addrs=email,
                msg=f'Subject: Flight Deals!\n\n{email_body}'
            )
else:
    print('No cheap flights today...')
