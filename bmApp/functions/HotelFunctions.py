from typing import Optional

import math
import requests
from django.conf import settings


PLACE_TYPES = {
    'airport': 'airport',
    'train_station': 'public_transport.train',
    'bus_stop': 'public_transport.bus',
    'subway_station': 'public_transport.subway',
    'ferry_terminal': 'public_transport.ferry',
}

PLACES_LIMIT = 10


def _geoapify_request(url: str, params: dict,) -> dict:

    if not settings.GEOAPIFY_API_KEY:
        raise requests.RequestException('GEOAPIFY_API_KEY is not configured.')

    try:
        response = requests.get(
            url,
            params={
                **params,
                'apiKey': settings.GEOAPIFY_API_KEY,
            },
            headers={
                'User-Agent': settings.MAP_USER_AGENT,
            },
            timeout=settings.MAP_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        raise
    except ValueError as error:
        raise requests.RequestException(
            'Geoapify returned a response that is not valid JSON.',
        ) from error

    if not isinstance(data, dict):
        raise requests.RequestException(
            'Geoapify returned an unexpected response payload.',
        )

    return data


def get_coordinates(address: str, city: str, country: str,) -> Optional[tuple[float, float]]:
    query = f'{address}, {city}, {country}'

    data = _geoapify_request(
        settings.GEOAPIFY_GEOCODE_URL,
        {
            'text': query,
            'format': 'json',
            'limit': 1,
        },
    )

    results = data.get('results')

    if not isinstance(results, list):
        raise requests.RequestException(
            'Geoapify geocoding response has no results list.',
        )

    if not results:
        return None

    result = results[0]

    try:
        return (float(result['lat']), float(result['lon']),)
    except (KeyError, TypeError, ValueError) as error:
        raise requests.RequestException(
            'Geoapify geocoding result has no valid coordinates.',
        ) from error


def calculate_distance(latitude1: float, longitude1: float,
    latitude2: float, longitude2: float) -> int:

    earth_radius = 6_371_000

    latitude1 = math.radians(latitude1)
    latitude2 = math.radians(latitude2)

    delta_latitude = latitude2 - latitude1
    delta_longitude = math.radians(longitude2 - longitude1)

    a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude1)
        * math.cos(latitude2)
        * math.sin(delta_longitude / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return round(earth_radius * c)


def get_nearest_place(latitude: float, longitude: float, place_type: str,) -> Optional[dict]:
    if place_type not in PLACE_TYPES:
        raise ValueError(
            f'Unknown place type: {place_type}. '
            f'Available types: {", ".join(PLACE_TYPES.keys())}'
        )

    category = PLACE_TYPES[place_type]

    search_radius = min(settings.AIRPORT_SEARCH_RADIUS, 30_000)

    data = _geoapify_request(
        settings.GEOAPIFY_PLACES_URL,
        {
            'categories': category,
            'filter': f'circle:{longitude},{latitude},{search_radius}',
            'bias': f'proximity:{longitude},{latitude}',
            'limit': PLACES_LIMIT,
        },
    )

    features = data.get('features')

    if not isinstance(features, list):
        raise requests.RequestException(
            'Geoapify places response has no features list.',
        )

    nearest_place = None
    nearest_distance = None

    for feature in features:

        if not isinstance(feature, dict):
            continue

        properties = feature.get('properties')

        if not isinstance(properties, dict):
            properties = {}

        place_latitude = properties.get('lat')
        place_longitude = properties.get('lon')

        if place_latitude is None or place_longitude is None:
            geometry = feature.get('geometry')
            coordinates = geometry.get('coordinates') if isinstance(geometry, dict) else None

            if not coordinates:
                continue

            try:
                place_longitude, place_latitude = coordinates
            except (TypeError, ValueError):
                continue

        try:
            place_latitude = float(place_latitude)
            place_longitude = float(place_longitude)
        except (TypeError, ValueError):
            continue

        distance = calculate_distance(
            latitude,
            longitude,
            place_latitude,
            place_longitude,
        )

        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance

            nearest_place = {
                'latitude': place_latitude,
                'longitude': place_longitude,
                'distance': distance,
                'name': properties.get('name'),
            }

    return nearest_place


def get_nearest_place_distance(latitude: float, longitude: float, place_type: str,) -> Optional[int]:

    place = get_nearest_place(
        latitude,
        longitude,
        place_type,
    )

    if place is None:
        return None

    return place['distance']


def get_address_by_coordinates(latitude: float, longitude: float) -> Optional[str]:

    data = _geoapify_request(
        settings.GEOAPIFY_REVERSE_URL,
        {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
        },
    )

    results = data.get('results')

    if not isinstance(results, list):
        raise requests.RequestException(
            'Geoapify reverse geocoding response has no results list.',
        )

    if not results:
        return None

    result = results[0]

    if not isinstance(result, dict):
        raise requests.RequestException(
            'Geoapify reverse geocoding result has no address.',
        )

    return result.get('formatted')

