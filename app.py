from flask import Flask, render_template, request
import requests
import re
from datetime import date, datetime, timedelta

app = Flask(__name__)

CURRENCY_TO_USD = {
    'EUR': 1.08,
    'GBP': 1.27,
    'JPY': 0.0067,
    'BRL': 0.20,
    'CAD': 0.73,
    'AUD': 0.66,
    'CNY': 0.14,
    'INR': 0.012,
    'MXN': 0.058,
    'CHF': 1.13,
    'ARS': 0.0011,
    'KRW': 0.00073,
    'ZAR': 0.054,
    'RUB': 0.011,
    'SEK': 0.094,
}



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


def join_with_default(items, default):
    items = list(items)
    if not items:
        return default
    return ', '.join(items)



def parse_user_date(text):
    
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text or ''):
        return None
   
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        return None


def convert_to_usd(currency_code):
    rate = CURRENCY_TO_USD.get(currency_code)
    if rate is None:
        return None
    return f"1 {currency_code} ~ {rate:.2f} USD"



def calculate_local_time(timezone_string):
    
    match = re.fullmatch(r'UTC([+-])(\d{2}):(\d{2})', timezone_string or '')
  
    now_utc = datetime.utcnow()

    if not match:
        return now_utc.strftime('%H:%M') + ' UTC'

    sign, hours, minutes = match.groups()
    offset = timedelta(hours=int(hours), minutes=int(minutes))
    if sign == '-':
        offset = -offset

    local_time = now_utc + offset
    return local_time.strftime('%H:%M') + f' (UTC{sign}{hours}:{minutes})'


def fetch_country_by_name(name):
    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/name/{name}",
            timeout=10,
        )
    except requests.RequestException:
        return None, "Could not reach the country service. plys try again."

    if response.status_code != 200:
        return None, "Country not found. Please check the spelling."

    try:
        return response.json()[0], None
    except (ValueError, IndexError):
        return None, "Unexpected answer from the country service."

def fetch_country_by_code(code):
    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/alpha/{code}",
            timeout=10,
        )
    except requests.RequestException:
        return None, "Could not reach the country service."

    if response.status_code != 200:
        return None, "Country information not available for this city."

    try:
        return response.json()[0], None
    except (ValueError, IndexError):
        return None, "Unexpected answer from the country service."

def fetch_city_coordinates(name):
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={'name': name, 'count': 1},
            timeout=10,
        ).json()
    except requests.RequestException:
        return None, "Could not reach the geocoding service."
    except ValueError:
        return None, "Unexpected answer from the geocoding service."

    if not response.get('results'):
        return None, "City not found. Please try another name."

    return response['results'][0], None


def fetch_weather(lat, lon, chosen_date, today):
    
    if chosen_date < today:
        weather_type = 'historical'
        url = "https://archive-api.open-meteo.com/v1/archive"
    elif chosen_date == today:
        weather_type = 'current'
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        weather_type = 'forecast'
        url = "https://api.open-meteo.com/v1/forecast"

    
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': chosen_date.isoformat(),
        'end_date': chosen_date.isoformat(),
        'daily': 'temperature_2m_max,temperature_2m_min,'
                 'precipitation_sum,windspeed_10m_max,weathercode',
        'timezone': 'auto',
    }

    try:
        daily = requests.get(url, params=params, timeout=10).json().get('daily', {})
    except (requests.RequestException, ValueError):
        return None, "Could not retrieve the weather data."

    
    weather = {
        'type': weather_type,
        'date': chosen_date.isoformat(),
        'temp_max': daily.get('temperature_2m_max', ['N/A'])[0],
        'temp_min': daily.get('temperature_2m_min', ['N/A'])[0],
        'precipitation': daily.get('precipitation_sum', ['N/A'])[0],
        'wind': daily.get('windspeed_10m_max', ['N/A'])[0],
        'description': get_weather_description(daily.get('weathercode', [0])[0]),
    }
    return weather, None

def fetch_seven_day_forecast(lat, lon):
    params = {
        'latitude': lat,
        'longitude': lon,
        'daily': 'temperature_2m_max,temperature_2m_min,'
                 'precipitation_sum,weathercode',
        'timezone': 'auto',
        'forecast_days': 7,
    }

    try:
        raw = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params, timeout=10,
        ).json().get('daily', {})
    except (requests.RequestException, ValueError):
        return []

    forecast = []
    for i, day_string in enumerate(raw.get('time', [])):
        day_obj = datetime.strptime(day_string, '%Y-%m-%d')
        forecast.append({
            'day_name': day_obj.strftime('%a'),      
            'day_date': day_obj.strftime('%b %d'),   
            'temp_max': round(raw['temperature_2m_max'][i]),
            'temp_min': round(raw['temperature_2m_min'][i]),
            'precipitation': raw['precipitation_sum'][i],
            'description': get_weather_description(raw['weathercode'][i]),
        })
    return forecast


def extract_country_info(country):
    name = country.get('name', {}).get('common', '')
    official = country.get('name', {}).get('official', name)

   
    currencies = country.get('currencies', {})
    if currencies:
        code = list(currencies.keys())[0]
        cname = currencies[code].get('name', '')
        currency_text = f"{cname} ({code})"
    else:
        code = None
        currency_text = 'Unknown'

    timezones_list = country.get('timezones', [])
    first_timezone = timezones_list[0] if timezones_list else 'UTC'

  
    flag = country.get('flags', {}).get('svg', '')
    coat = country.get('coatOfArms', {}).get('svg', '')

    return {
        'common_name': name,
        'official_name': official,
        'capital': country.get('capital', ['Unknown'])[0],
        'population': country.get('population', 0),
        'region': country.get('region', 'Unknown'),
        'subregion': country.get('subregion', ''),
        'area': country.get('area', 0) or 0,
        'currency_code': code,
        'currency_text': currency_text,
        'languages': join_with_default(country.get('languages', {}).values(), 'Unknown'),
        'timezones': join_with_default(timezones_list, 'Unknown'),
        'first_timezone': first_timezone,
        'borders': join_with_default(country.get('borders', []), 'None'),
        'latlng': country.get('latlng', [0, 0]),
        'flag': flag,
        'coat': coat,
    }


@app.route('/', methods=['GET', 'POST'])
def home():
    today = date.today()

   
    context = {
        'today': today.isoformat(),
        'search_type': 'country',
        'search_term': '',
        'date_term': today.isoformat(),
    }

   
    if request.method != 'POST':
        return render_template('index.html', **context)

 
    search_type = request.form.get('search_type', 'country')
    search_term = request.form.get('search_term', '').strip()
    date_term = request.form.get('weather_date', '').strip()

    context['search_type'] = search_type
    context['search_term'] = search_term
    context['date_term'] = date_term


    if not search_term:
        return render_template('index.html',
                               error="Please type something to search.",
                               **context)

    chosen_date = parse_user_date(date_term)
    if chosen_date is None:
        return render_template(
            'index.html',
            error="The date must use the format YYYY-MM-DD "
                  "(example: 2024-05-20).",
            **context,
        )

    if search_type == 'city':
        city, err = fetch_city_coordinates(search_term)
        if err:
            return render_template('index.html', error=err, **context)

        display_name = city['name']
        lat = city['latitude']
        lon = city['longitude']

        country_raw, err = fetch_country_by_code(city.get('country_code', ''))
        if err:
            return render_template('index.html', error=err, **context)
    else:
        country_raw, err = fetch_country_by_name(search_term)
        if err:
            return render_template('index.html', error=err, **context)

        display_name = country_raw.get('name', {}).get('common', search_term)
        lat, lon = country_raw.get('latlng', [0, 0])


    info = extract_country_info(country_raw)

 
    usd_value = convert_to_usd(info['currency_code'])
    local_time = calculate_local_time(info['first_timezone'])

    weather, err = fetch_weather(lat, lon, chosen_date, today)
    if err:
        return render_template('index.html', error=err, **context)

    forecast = fetch_seven_day_forecast(lat, lon)

    data = {
        'name': display_name,
        'is_city': search_type == 'city',
        'country_name': info['common_name'],
        'official_name': info['official_name'],
        'capital': info['capital'],
        'population': f"{info['population']:,}",
        'area': f"{info['area']:,.0f}",
        'region': info['region'],
        'subregion': info['subregion'],
        'currency': info['currency_text'],
        'usd_value': usd_value,
        'languages': info['languages'],
        'timezones': info['timezones'],
        'local_time': local_time,
        'borders': info['borders'],
        'lat': lat,
        'lon': lon,
        'flag_url': info['flag'],
        'coat_url': info['coat'],
        'weather': weather,
        'forecast': forecast,
        'selected_date': chosen_date.isoformat(),
    }

    return render_template('index.html', data=data, **context)


if __name__ == '__main__':
    app.run(debug=True)