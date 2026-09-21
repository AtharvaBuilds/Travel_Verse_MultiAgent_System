import requests
import os
from dotenv import load_dotenv
load_dotenv()

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
access_key=os.getenv("avaiation_access_key")
def get_location(city):
    URL = "https://geocoding-api.open-meteo.com/v1/search"
    params = { "name":city, "count":1, "language":"en", "format":"json" }
    response = requests.get(URL,params)
    resp_json = response.json()
    location = resp_json.get('results')[0]
    return {
        "name":location.get('name'),
        "latitude":location.get('latitude'),
        "longitude":location.get('longitude'),
        "timezone":location.get('timezone'),
        "population":location.get('population'),
        "country":location.get('country')
    }
def get_weather(latt,longi):
    URL = "https://api.open-meteo.com/v1/forecast"
    params = { "latitude":latt, "longitude":longi, "current": "temperature_2m,relative_humidity_2m,wind_speed_10m", "daily":"temperature_2m_max,temperature_2m_min,precipitation_probability_max", "forecast_days":5,"timezone":"auto"}
    resp = requests.get(URL,params)
    return resp.json()

def display_weather(weather):
    print(weather)
    current_weather = weather["current"]
    print("\n***** CURRENT WEATHER *****")
    print("Temprature:", current_weather["temperature_2m"], "°C")
    print("Humidity:", current_weather["relative_humidity_2m"], "%")
    print("Wind Speed:", current_weather["wind_speed_10m"], "km/h")

def get_exchange_rate(base,target,amt):
    url=f'https://open.er-api.com/v6/latest/{base}'
    resp=requests.get(url)
    data=resp.json()
    rates=data["rates"]
    conversion_rate=rates[target]
    print(f"1 INR={conversion_rate}")
    print(f"{amt} INR={conversion_rate*amt} USD")
    return conversion_rate

def get_airport_iata(city):
    url = "https://api.api-ninjas.com/v1/airports"
    headers = {"X-Api-Key":API_NINJAS_KEY}
    params = {"q":city, "has_iata":"true", "sort":"passengers", "order":"desc", "limit":1}
    resp = requests.get(url,params=params, headers=headers)
    iata = resp.json()[0]["iata"]
    return iata

def search_flights(departure_airport, arrival_airport):
    url='https://api.aviationstack.com/v1/flights'
    params={"access_key":access_key,"dep_iata":departure_airport,"arr_iata":arrival_airport,"limit":5}
    resp=requests.get(url,params=params)
    print(departure_airport)
    print(arrival_airport)
    return resp.json()

def display_flight(flights):
    if flights.get('pagination').get('count')==0:
        print("No flights found")
    flights_data=flights.get('data')
    srno=1
    for flight in flights_data:
        airline=flight.get('airline').get('name')
        departure=flight.get('departure').get('airport')
        arrival=flight.get('arrival').get('airport')
        flight_number=flight.get('flight').get('number')
        dep_time=flight.get('departure').get('scheduled')
        arr_time=flight.get('arrival').get('scheduled')
        print(f"Flight Option NO :{srno}")
        print("Departure time : ",dep_time )
        print("Airline : ",airline, "-",flight_number)
        print("Journey : ",departure,"---->",arrival)
        print("Arrival time : ",arr_time)
        srno+=1
        print()

if __name__ == "__main__":
    # city = input("Enter City:")
    # loc = get_location(city)
    # wthr = get_weather(loc['latitude'], loc['longitude'])
    # display_weather(wthr)
     #get_exchange_rate("INR","USD", 96)
    city1=input("Enter City Name: ")
    city2=input("Enter City Name: ")
    dep_iata=get_airport_iata(city1)
    arr_iata=get_airport_iata(city2)
    fli=search_flights(dep_iata,arr_iata)
    display_flight(fli)
