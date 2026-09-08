from typing import Optional

import math
import requests
from django.conf import settings


PLACE_TYPES = {
    'airport': 'aeroway="aerodrome"',
    'train_station': 'railway="station"',
    'bus_stop': 'highway="bus_stop"',
    'subway_station': 'railway="subway_entrance"',
    'ferry_terminal': 'amenity="ferry_terminal"',
}


def get_coordinates(address: str, city: str, country: str,) -> Optional[tuple[float, float]]:
    query = f'{address}, {city}, {country}'

    response = requests.get(
        settings.NOMINATIM_URL,
        params={
            'q': query,
            'format': 'json',
            'limit': 1,
        },
        headers={
            'User-Agent': settings.NOMINATIM_USER_AGENT,
        },
        timeout=settings.MAP_API_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return (float(data[0]['lat']),float(data[0]['lon']),)


def calculate_distance(latitude1: float, longitude1: float,
    latitude2: float, longitude2: float) -> int:

    earth_radius = 6_371_000

    latitude1 = math.radians(latitude1)
    latitude2 = math.radians(latitude2)

    delta_latitude = math.radians(latitude2 - latitude1)
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

    osm_filter = PLACE_TYPES[place_type]

    # Хз как это работает но это работает. Я из будующего не трогай это сломаешь потом не починешь
    query = f'''
    [out:json];

    (
        node[{osm_filter}]
            (around:{settings.AIRPORT_SEARCH_RADIUS},{latitude},{longitude});

        way[{osm_filter}]
            (around:{settings.AIRPORT_SEARCH_RADIUS},{latitude},{longitude});

        relation[{osm_filter}]
            (around:{settings.AIRPORT_SEARCH_RADIUS},{latitude},{longitude});
    );

    out center;
    '''

    response = requests.post(
        settings.OVERPASS_URL,
        data=query,
        timeout=settings.MAP_API_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get('elements'):
        return None

    nearest_place = None
    nearest_distance = None

    for place in data['elements']:

        if place['type'] == 'node':
            place_latitude = place['lat']
            place_longitude = place['lon']
        else:
            center = place.get('center')

            if not center:
                continue

            place_latitude = center['lat']
            place_longitude = center['lon']

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
                'name': place.get('tags', {}).get('name'),
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

    response = requests.get(
        settings.NOMINATIM_URL.replace('/search', '/reverse'),
        params={
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 18,
        },
        headers={
            'User-Agent': settings.NOMINATIM_USER_AGENT,
        },
        timeout=settings.MAP_API_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return data.get('display_name')

