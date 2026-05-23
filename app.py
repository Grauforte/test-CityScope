from flask import Flask, render_template, request
import requests
from datetime import date, datetime, timedelta

app = Flask(__name__)


# ============================================================
# HELPER FUNCTION 1
# Returns a short text description of the weather based on the
# code returned by Open-Meteo (WMO weather code standard).
# ============================================================
def get_weather_description(code):
    if code == 0:
        return 'Clear'
    if code <= 3:
        return 'Cloudy'
    if code <= 48:
        return 'Foggy'
    if code <= 67:
        return 'Rain'
    if code <= 77:
        return 'Snow'
    if code <= 86:
        return 'Showers'
    return 'Storm'


# ============================================================
# HELPER FUNCTION 2
# Joins a list (or dict values) into a single string with commas.
# Returns a default text if the list is empty.
# Example: ['A','B','C'] -> "A, B, C"
# ============================================================
def join_with_default(items, default):
    items = list(items)
    if not items:
        return default
    return ', '.join(items)


# ============================================================
# MAIN ROUTE
# Handles both the empty page (GET) and the search (POST).
# ============================================================
@app.route('/', methods=['GET', 'POST'])
def home():

    # Date picker limits:
    # up to 5 years in the past and up to 15 days into the future.
    today = date.today()
    min_date = (today - timedelta(days=5 * 365)).isoformat()
    max_date = (today + timedelta(days=15)).isoformat()

    # Default values passed to the HTML template.
    # If the user submits the form, we update these with what they typed.
    context = {
        'today': today.isoformat(),
        'min_date': min_date,
        'max_date': max_date,
        'search_type': 'country',
        'search_term': '',
    }

    # If it is a GET request, just show the empty page.
    if request.method != 'POST':
        return render_template('index.html', **context)

    # ----------------------------------------------------------
    # STEP 1 - Read what the user typed in the form
    # ----------------------------------------------------------
    search_type = request.form.get('search_type', 'country')   # 'country' or 'city'
    search_term = request.form.get('search_term', '').strip()
    weather_date = request.form.get('weather_date') or today.isoformat()

    # Save the user's choices so the form stays filled after submit.
    context['search_type'] = search_type
    context['search_term'] = search_term

    if not search_term:
        return render_template('index.html',
                               error="Please type something to search.",
                               **context)

    # ----------------------------------------------------------
    # STEP 2 - Find the location
    # We follow two different paths based on the search type.
    # Both paths end with the same variables:
    #     country (dict), lat, lon, display_name
    # ----------------------------------------------------------
    if search_type == 'city':
        # 2a. Use the Geocoding API to turn a city name into coordinates
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_response = requests.get(geo_url, params={'name': search_term, 'count': 1}).json()

        if not geo_response.get('results'):
            return render_template('index.html',
                                   error="City not found. Please try another name.",
                                   **context)

        city = geo_response['results'][0]
        display_name = city['name']
        lat = city['latitude']
        lon = city['longitude']
        country_code = city.get('country_code', '')

        # 2b. Look up the country using its 2-letter code
        country_response = requests.get(f"https://restcountries.com/v3.1/alpha/{country_code}")

        if country_response.status_code != 200:
            return render_template('index.html',
                                   error="Country information not found.",
                                   **context)
        country = country_response.json()[0]

    else:
        # Search by country name directly
        country_response = requests.get(f"https://restcountries.com/v3.1/name/{search_term}")

        if country_response.status_code != 200:
            return render_template('index.html',
                                   error="Country not found. Please try again.",
                                   **context)

        country = country_response.json()[0]
        display_name = country.get('name', {}).get('common', search_term)
        lat, lon = country.get('latlng', [0, 0])

    # ----------------------------------------------------------
    # STEP 3 - Extract the country information
    # ----------------------------------------------------------
    country_name = country.get('name', {}).get('common', '')
    official_name = country.get('name', {}).get('official', display_name)
    capital = country.get('capital', ['Unknown'])[0]
    population = country.get('population', 0)
    region = country.get('region', 'Unknown')
    subregion = country.get('subregion', '')
    area = country.get('area', 0)
    flag = country.get('flags', {}).get('png', '')

    # Currency: take the first code and its name (example: "Euro (EUR)")
    currencies = country.get('currencies', {})
    if currencies:
        first_code = list(currencies.keys())[0]
        currency_name = currencies[first_code].get('name', '')
        currency = f"{currency_name} ({first_code})"
    else:
        currency = 'Unknown'

    # Turn lists into simple comma-separated text
    languages = join_with_default(country.get('languages', {}).values(), 'Unknown')
    timezones = join_with_default(country.get('timezones', []), 'Unknown')
    borders = join_with_default(country.get('borders', []), 'None')

    # ----------------------------------------------------------
    # STEP 4 - Get the weather for the chosen date
    # We pick a different API depending on whether the date is in
    # the past, today, or in the future.
    # ----------------------------------------------------------
    chosen_date = datetime.strptime(weather_date, '%Y-%m-%d').date()

    if chosen_date < today:
        weather_type = 'historical'
        weather_url = "https://archive-api.open-meteo.com/v1/archive"
    elif chosen_date == today:
        weather_type = 'current'
        weather_url = "https://api.open-meteo.com/v1/forecast"
    else:
        weather_type = 'forecast'
        weather_url = "https://api.open-meteo.com/v1/forecast"

    # Both APIs accept the same parameters
    weather_params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': weather_date,
        'end_date': weather_date,
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode',
        'timezone': 'auto',
    }
    weather_data = requests.get(weather_url, params=weather_params).json().get('daily', {})

    # The API returns lists with one value each (because we asked for one day)
    weather = {
        'type': weather_type,
        'date': weather_date,
        'temp_max': weather_data.get('temperature_2m_max', ['N/A'])[0],
        'temp_min': weather_data.get('temperature_2m_min', ['N/A'])[0],
        'precipitation': weather_data.get('precipitation_sum', ['N/A'])[0],
        'wind': weather_data.get('windspeed_10m_max', ['N/A'])[0],
        'description': get_weather_description(weather_data.get('weathercode', [0])[0]),
    }

    # ----------------------------------------------------------
    # STEP 5 - Get the 7-day forecast (always starts from today)
    # ----------------------------------------------------------
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    forecast_params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode',
        'timezone': 'auto',
        'forecast_days': 7,
    }
    forecast_raw = requests.get(forecast_url, params=forecast_params).json().get('daily', {})

    # Build a list with one item per day
    forecast = []
    for i, day_string in enumerate(forecast_raw.get('time', [])):
        day_obj = datetime.strptime(day_string, '%Y-%m-%d')
        forecast.append({
            'day_name': day_obj.strftime('%a'),       # example: "Mon"
            'day_date': day_obj.strftime('%b %d'),    # example: "May 22"
            'temp_max': round(forecast_raw['temperature_2m_max'][i]),
            'temp_min': round(forecast_raw['temperature_2m_min'][i]),
            'precipitation': forecast_raw['precipitation_sum'][i],
            'description': get_weather_description(forecast_raw['weathercode'][i]),
        })

    # ----------------------------------------------------------
    # STEP 6 - Send everything to the HTML template
    # ----------------------------------------------------------
    data = {
        'name': display_name,
        'is_city': search_type == 'city',
        'country_name': country_name,
        'official_name': official_name,
        'capital': capital,
        'population': f"{population:,}",
        'area': f"{area:,.0f}",
        'region': region,
        'subregion': subregion,
        'currency': currency,
        'languages': languages,
        'timezones': timezones,
        'borders': borders,
        'flag': flag,
        'lat': lat,
        'lon': lon,
        'weather': weather,
        'forecast': forecast,
        'selected_date': weather_date,
    }

    return render_template('index.html', data=data, **context)


if __name__ == '__main__':
    app.run(debug=True)
