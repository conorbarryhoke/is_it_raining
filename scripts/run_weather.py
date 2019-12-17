import os, sys
cwd = os.getcwd()
sys.path.append(cwd)
from importlib import import_module
import_module("my_bigq")
from my_bigq import bigquery_handler

import requests, json, datetime



def kelvin_converter(deg_k):
    return (deg_k - 273.15) * 9/5 + 32


def get_weather(city_name="Austin"):
    weather_data_path = "http://storage.googleapis.com/twitter-weather/weather-data/"

    with open('../info/weather_key.txt', "r") as file:
        api_key_weather = file.read().replace('\n', '')

    # https://www.geeksforgeeks.org/python-find-current-weather-of-any-city-using-openweathermap-api/

    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + api_key_weather + "&q=" + city_name

    response = requests.get(complete_url)
    x = response.json()

    return x

def process_weather(x):

    # declare vars
    weather_main = None
    weather_description = None
    temp_K = None
    temp_F = None
    pressure = None
    humidity = None
    temp_min = None
    temp_max = None
    sea_level = None
    grnd_level = None
    visibility = None
    wind_speed = None
    wind_deg = None
    rain_type = None
    rain_list = None
    clouds = None
    city_name = None

    try:
        city_name = x['name']
    except:
        print('bad var city')
    try:
        weather_main = x['weather'][0]['main']
    except:
        print('bad var weather_main')

    try:
        weather_description = x['weather'][0]['description']
    except:
        print('bad var weather_description')

    try:
        temp_K = x['main']['temp']
        temp_F = kelvin_converter(temp_K)
    except:
        print('bad var temp_K')

    try:
        pressure = x['main']['pressure']
    except:
        print('bad var pressure')

    try:
        humidity = x['main']['humidity']
    except:
        print('bad var humidity')

    try:
        temp_min = x['main']['temp_min']
    except:
        print('bad var temp_min')

    try:
        temp_max = x['main']['temp_max']
    except:
        print('bad var temp_max')

    try:
        sea_level = x['main']['sea_level']
    except:
        print('bad var sea_level')

    try:
        grnd_level = x['main']['grnd_level']
    except:
        print('bad var grnd_level')

    try:
        visibility = x['visibility']
    except:
        print('bad var visibility')

    try:
        wind_speed = x['wind']['speed']
    except:
        print('bad var wind_speed')

    try:
        wind_deg = x['wind']['deg']
    except:
        print('bad var wind_deg')

    try:
        rain_type = list(x['rain'].keys())[0]
    except:
        print('bad var rain_type')

    try:
        rain_list = x['rain'][rain_type]
    except:
        print('bad var rain_list')

    try:
        clouds = x['clouds']['all']
    except:
        print('bad var clouds')


    timestamp = datetime.datetime.now()

    data_dict = {
        'timestamp': timestamp,
        'weather_main' :weather_main,
        'weather_description'  :weather_description ,
        'temp_K'  :temp_K ,
        'temp_F'  :temp_F ,
        'pressure'  :pressure ,
        'humidity'  : humidity,
        'temp_min'  :temp_min ,
        'temp_max'  :temp_max ,
        'sea_level' : sea_level,
        'grnd_level' : grnd_level,
        'visibility' : visibility,
        'wind_speed' :wind_speed ,
        'wind_deg' : wind_deg,
        'rain_type': rain_type,
        'rain_list': rain_list,
        'clouds':clouds ,
        'city_name':city_name,
    }

    return data_dict

def send_to_table(data_dict):


    q_base = """
        INSERT INTO metridaticsmain.webscrapes.weather_data (
        timestamp, weather_main, weather_description, temp_K, temp_F, pressure,
        humidity, temp_min, temp_max, sea_level, grnd_level, visibility, wind_speed,
        wind_deg, rain_type, rain_list, clouds, city_name
        )
        VALUES ('{}', '{}', '{}', {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, '{}', {}, {}, '{}')
        ;
        """.format(
            data_dict['timestamp'], data_dict['weather_main'], data_dict['weather_description'],
            data_dict['temp_K'], data_dict['temp_F'], data_dict['pressure'],
            data_dict['humidity'], data_dict['temp_min'], data_dict['temp_max'],
            data_dict['sea_level'], data_dict['grnd_level'], data_dict['visibility'],
            data_dict['wind_speed'], data_dict['wind_deg'], data_dict['rain_type'],
            data_dict['rain_list'], data_dict['clouds'],data_dict['city_name']
            ).replace('\n', '').replace("None","NULL").replace("'NULL'", "NULL")

    return bigquery_handler(q_base=q_base).run_query()

def run_city(city):
    x = get_weather(city)
    data_dict = process_weather(x)
    send_to_table(data_dict)

def run_main():
    run_city("Austin")
    run_city("Seattle")


if __name__ == "__main__":
    run_main()

