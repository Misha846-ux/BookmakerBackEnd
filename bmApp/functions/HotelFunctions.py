from typing import Optional

import requests
from django.conf import settings


def get_coordinates(address: str,city: str,country: str,) -> Optional[tuple[float, float]]:
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

    return (
        float(data[0]['lat']),
        float(data[0]['lon']),
    )