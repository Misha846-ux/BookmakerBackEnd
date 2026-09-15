from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bmApp.models import CountryEntity


COUNTRIES_AND_CITIES = {
    "France": {"Paris": "Rue de Rivoli", "Lyon": "Rue de la République"},
    "United Kingdom": {"London": "Oxford Street", "Manchester": "Market Street"},
    "Italy": {"Rome": "Via del Corso", "Milan": "Corso Vittorio Emanuele II"},
    "Spain": {"Madrid": "Gran Vía", "Barcelona": "La Rambla"},
    "Germany": {"Berlin": "Unter den Linden", "Munich": "Kaufingerstraße"},
    "Netherlands": {"Amsterdam": "Kalverstraat", "Rotterdam": "Coolsingel"},
    "Austria": {"Vienna": "Kärntner Straße", "Salzburg": "Getreidegasse"},
    "Switzerland": {"Zurich": "Bahnhofstrasse", "Geneva": "Rue du Rhône"},
    "United States": {"New York City": "5th Avenue", "Chicago": "Michigan Avenue"},
    "Japan": {"Tokyo": "Chūō-dōri", "Kyoto": "Shijō-dori"},
}

HOTELS = [
    {
        "name": "Leopold Grand Hotel",
        "address": "Leopoldstraße",
        "country": "Germany",
        "city": "Munich",
        "phone": "+49891234501",
        "email": "munich@test-bookmaker.example",
        "source_photo": "Hotel1.png",
    },
    {
        "name": "Linzer Gasse Palace",
        "address": "Linzer Gasse",
        "country": "Austria",
        "city": "Salzburg",
        "phone": "+436621234502",
        "email": "salzburg@test-bookmaker.example",
        "source_photo": "Hotel2.jpg",
    },
    {
        "name": "Broadway Central Hotel",
        "address": "Broadway",
        "country": "United States",
        "city": "New York City",
        "phone": "+12125555003",
        "email": "new-york@test-bookmaker.example",
        "source_photo": "Hotel3.jpg",
    },
]

ROOM_PHOTOS = ("Room1.jpg", "Room2.jpg", "Room3.png")


class Command(BaseCommand):
    help = "Load test data through the running REST API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default="http://127.0.0.1:8000",
            help="Base URL of the running Bookmaker API.",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=30,
            help="HTTP request timeout in seconds.",
        )

    def handle(self, *args, **options):
        source_directory = Path(settings.BASE_DIR) / "PicturesForTests"
        if not source_directory.is_dir():
            raise CommandError(f"Picture directory not found: {source_directory}")

        self.base_url = options["base_url"].rstrip("/")
        self.timeout = options["timeout"]
        self.manual_fallbacks = []
        self.session = requests.Session()

        try:
            cities = self._load_countries_and_cities()
            hotels = self._load_hotels_and_rooms(source_directory, cities)
        except requests.RequestException as error:
            raise CommandError(
                f"Could not connect to {self.base_url}. Start the Django server first. {error}"
            ) from error

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(cities)} cities and {len(hotels)} hotels through the API."
        ))
        if self.manual_fallbacks:
            self.stdout.write(self.style.WARNING(
                "Manual database fallbacks were used: "
                + ", ".join(self.manual_fallbacks)
            ))
        else:
            self.stdout.write("Manual database fallbacks: none.")

    def _load_countries_and_cities(self):
        countries = {}
        for country_name in COUNTRIES_AND_CITIES:
            country, _ = CountryEntity.objects.get_or_create(name=country_name)
            countries[country_name] = country
        self.manual_fallbacks.append(
            "countries (no country creation API endpoint exists)"
        )

        response = self._request("PUT", "/cities/")
        existing_cities = {
            (city["country"], city["name"]): city
            for city in response.json()
        }

        cities = {}
        for country_name, city_data in COUNTRIES_AND_CITIES.items():
            country_id = countries[country_name].id
            for city_name, center in city_data.items():
                city = existing_cities.get((country_id, city_name))
                if city is None:
                    city = self._request(
                        "POST",
                        "/cities/create/",
                        json={
                            "name": city_name,
                            "center": center,
                            "country": country_id,
                        },
                    ).json()
                cities[(country_name, city_name)] = city
        return cities

    def _load_hotels_and_rooms(self, source_directory, cities):
        existing_hotels = self._get_existing_hotels()
        loaded_hotels = []
        for hotel_number, hotel_data in enumerate(HOTELS, start=1):
            hotel = existing_hotels.get(hotel_data["email"])
            if hotel is None:
                hotel = self._request(
                    "POST",
                    "/hotels/create/",
                    json={
                        "name": hotel_data["name"],
                        "description": f"Test hotel {hotel_number}",
                        "address": hotel_data["address"],
                        "phone": hotel_data["phone"],
                        "email": hotel_data["email"],
                        "stars": 4,
                        "city": cities[(hotel_data["country"], hotel_data["city"])]["id"],
                    },
                ).json()
            self._upload_file(
                f"/hotels/post/{hotel['id']}/photos/",
                source_directory / "Hotels" / hotel_data["source_photo"],
            )

            rooms = self._get_existing_rooms(hotel["id"])
            for room_number in range(1, 3):
                if len(rooms) >= room_number:
                    room = rooms[room_number - 1]
                else:
                    room = self._request(
                        "POST",
                        "/rooms/create/",
                        json={
                            "roomNumber": f"{hotel_number}0{room_number}",
                            "description": f"Test room {hotel_number}-{room_number}",
                            "wifi": True,
                            "privatePool": False,
                            "Bath": True,
                            "price": 100 + hotel_number * 25 + room_number,
                            "beds": 2,
                            "hotel": hotel["id"],
                        },
                    ).json()
                source_name = ROOM_PHOTOS[(hotel_number + room_number - 2) % len(ROOM_PHOTOS)]
                self._upload_file(
                    f"/rooms/post/{room['id']}/photos/",
                    source_directory / "Rooms" / source_name,
                )
            loaded_hotels.append(hotel)
        return loaded_hotels

    def _get_existing_hotels(self):
        response = self._request("PUT", "/hotels/get/?el=100&page=1", json={})
        return {hotel["email"]: hotel for hotel in response.json()["results"]}

    def _get_existing_rooms(self, hotel_id):
        response = self._request(
            "PUT",
            f"/hotels/{hotel_id}/rooms/?el=100&page=1",
            json={},
        )
        return response.json()["results"]

    def _upload_file(self, path, file_path):
        if not file_path.is_file():
            raise CommandError(f"Picture not found: {file_path}")
        with file_path.open("rb") as picture:
            self._request(
                "POST",
                path,
                files={"file": (file_path.name, picture)},
            )

    def _request(self, method, path, **kwargs):
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
        if not response.ok:
            raise CommandError(
                f"{method} {path} failed with {response.status_code}: {response.text}"
            )
        return response
