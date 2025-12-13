from datetime import datetime, timezone
from flask import Flask, request, render_template, send_file
from decimal import Decimal
import requests
import boto3 # for API calls to AWS services
import os
import json

app = Flask(__name__)
# AWS configurations
S3_BUCKET = "my-s3-weather"
S3_REGION = "eu-north-1"
S3_FILE_KEY = "sky_image.jpg"

@app.route('/save-weather', methods=['POST'])
def save_weather():
    """
    Save the weather data from session to DynamoDB.
    """
    try:
        forecast = json.loads(request.form['forecast'])
        city = request.form['city']
        country = request.form['country']

        if not forecast or not city:
            return "No weather data found in session.", 400

        # connect to DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        table = dynamodb.Table('WeatherData')
        # use convert function for DynamoDB
        forecast_decimal = convert_floats_to_decimal(forecast)
        timestamp = datetime.now(timezone.utc).isoformat()

        table.put_item(Item={
            'city': city,
            'country': country,
            'timestamp': timestamp,
            'forecast': forecast_decimal
        })

        return f"Weather data for {city} was successfully saved to DynamoDB,", 200

    except Exception as e:
        return f"Failed to save the weather data: {str(e)}", 500

@app.route('/download-sky')
def download_sky_image():
    """
    Download a sky image from S3 bucket
    """
    try:
        # create S3 client (use credentials from IAM role)
        s3 = boto3.client('s3', region_name=S3_REGION)
        local_path = "/tmp/" + S3_FILE_KEY
        s3.download_file(S3_BUCKET, S3_FILE_KEY, local_path)
        return send_file(local_path, as_attachment=True)
    except Exception as e:
        return f"Failed to download image from S3: {str(e)}", 500

@app.route('/', methods=['GET'])
def home_page():
    """
    Main route for rendering the weather app.
    Handles fetching city input, geocoding, weather data and formatting dates.
    Returns the HTML page with weather forecast or error messages.
    """
    city = request.args.get('city')    # get the city name from URL parameters
    country = ""
    weather_data = None
    forecast = None
    error_message = None

    if city:
        # get coordinates from Open-Meteo geocoding, if the city name was given
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1}   # return first match

        try:
            # make requests to Opem-Mateo geocoding API
            geo_response = requests.get(geo_url, params=geo_params, timeout=5)
            geo_response.raise_for_status()  # raise exception if HTTP status != 200
            geo_data = geo_response.json()   # parse JSON response
        except requests.exceptions.RequestException:
            error_message = "Failed to fetch the city coordinates. Please try again."
            return render_template("index.html",
                                   city=city,
                                   country=country,
                                   weather_data=weather_data,
                                   error_message=error_message)

        # if city result are no found -> return not found error
        if not geo_data.get("results"):
            error_message = f"City '{city}' not found"
            return render_template("index.html",
                                   city=city,
                                   country=country,
                                   weather_data=weather_data,
                                   error_message=error_message)
        # extract latitude and longitude from the geo response
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        country = geo_data["results"][0]["country"]

        # get the forecast data from the coordinates
        forecast = get_forecast(lat, lon)

        if "error" in forecast:
            # if API returned an error
            error_message = forecast.get("error")
        else:
            # extract the daily forecast data
            weather_data = forecast.get("daily")    # save access
            formatted_dates = []
            for date in weather_data["time"]:
                # strptime: from string to datetime
                data_type = datetime.strptime(date, "%Y-%m-%d")
                # strftime: from datetime to string
                formatted_dates.append(data_type.strftime("%A %d %b"))
            # replace the original time list with the formated dates
            weather_data["time"] = formatted_dates

            # add sunrise time (keep the original API values)
            weather_data["sunrise"] = weather_data["sunrise"]

    # return HTML with city, weather_data or error
    return render_template("index.html",
                           city=city,
                           country=country,
                           weather_data=weather_data,
                           forecast=forecast,
                           error_message=error_message)

def get_forecast(lat: float, lon: float):
    """
    Fetch 7-day forecast data from Open-Mateo API, using latitude and longitude.
    Return a dictionary with daily forecast or an error messages.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max",
                  "temperature_2m_min",
                  "relative_humidity_2m_mean",
                  "sunrise"],
        "timezone": "auto"
    }

    try:
        # make request to forecast API
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()   # raise exception if HTTP !=200
        data = response.json()
    except requests.exceptions.RequestException:
        return {"error": "Failed to fetch weather data from API"}

    if "daily" not in data:
        return {"error": "Failed to get weather data"}
    # return forecast dictionary
    return data

def convert_floats_to_decimal(obj):
    """
    RConvert all float values in a dict/list to Decimal, so they can be stored in DynamoDB.
    """
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj



if __name__ == '__main__':
    # run the app in debug mode
    app.run(debug=True)



