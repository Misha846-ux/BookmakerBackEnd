from datetime import date, timedelta
from pathlib import Path
import random
import sys
import time

import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from bmApp.models import (
    CityEntity,
    CountryEntity,
    CurrencyEntity,
    DebitCardEntity,
    HotelEntity,
    PaymentMethodEntity,
    ReservationEntity,
    ReviewEntity,
    RoomEntity,
    UserEntity,
)
from bmApp.functions.HotelFunctions import get_coordinates, get_nearest_place


GEOAPIFY_PAUSE = 0.35

COUNTRIES_AND_CITIES = {
    "France": {
        "Paris": "Rue de Rivoli",
        "Lyon": "Rue de la République",
        "Marseille": "La Canebière",
        "Nice": "Promenade des Anglais",
    },
    "United Kingdom": {
        "London": "Oxford Street",
        "Manchester": "Market Street",
        "Edinburgh": "Royal Mile",
        "Birmingham": "New Street",
    },
    "Italy": {
        "Rome": "Via del Corso",
        "Milan": "Corso Vittorio Emanuele II",
        "Naples": "Via Toledo",
        "Venice": "Piazza San Marco",
    },
    "Spain": {
        "Madrid": "Gran Vía",
        "Barcelona": "La Rambla",
        "Seville": "Calle Sierpes",
        "Valencia": "Calle Colón",
    },
    "Germany": {
        "Berlin": "Unter den Linden",
        "Munich": "Kaufingerstraße",
        "Hamburg": "Mönckebergstraße",
        "Frankfurt": "Zeil",
    },
    "Netherlands": {
        "Amsterdam": "Kalverstraat",
        "Rotterdam": "Coolsingel",
        "Utrecht": "Oudegracht",
        "The Hague": "Grote Markt",
    },
    "Austria": {
        "Vienna": "Kärntner Straße",
        "Salzburg": "Getreidegasse",
        "Innsbruck": "Maria-Theresien-Straße",
        "Graz": "Hauptplatz",
    },
    "Switzerland": {
        "Zurich": "Bahnhofstrasse",
        "Geneva": "Rue du Rhône",
        "Basel": "Freie Strasse",
        "Bern": "Kramgasse",
    },
    "United States": {
        "New York City": "5th Avenue",
        "Chicago": "Michigan Avenue",
        "Los Angeles": "Sunset Boulevard",
        "Miami": "Ocean Drive",
    },
    "Japan": {
        "Tokyo": "Chūō-dōri",
        "Kyoto": "Shijō-dori",
        "Osaka": "Midosuji",
        "Hiroshima": "Hondōri",
    },
}

HOTEL_PHOTOS = ("Hotel1.png", "Hotel2.jpg", "Hotel3.jpg")

HOTELS = [
    {
        "name": "Leopold Grand Hotel",
        "description": "Classic grand hotel opposite the English Garden, with a spa and traditional Bavarian restaurant.",
        "address": "Leopoldstraße",
        "country": "Germany",
        "city": "Munich",
        "phone": "+49891234501",
        "email": "munich@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Linzer Gasse Palace",
        "description": "Baroque palace on a quiet pedestrian street, a short walk from Mozart's birthplace.",
        "address": "Linzer Gasse",
        "country": "Austria",
        "city": "Salzburg",
        "phone": "+436621234502",
        "email": "salzburg@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Broadway Central Hotel",
        "description": "Theatre district landmark with rooftop views over Times Square.",
        "address": "Broadway",
        "country": "United States",
        "city": "New York City",
        "phone": "+12125555003",
        "email": "new-york@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Hôtel Rivage",
        "description": "Elegant Left Bank hotel on the Seine, steps away from the Latin Quarter.",
        "address": "Boulevard Saint-Germain",
        "country": "France",
        "city": "Paris",
        "phone": "+33142680004",
        "email": "paris@test-bookmaker.example",
        "stars": 5,
    },
    {
        "name": "Thamesview Hotel",
        "description": "Riverside hotel between Covent Garden and the South Bank, with a panorama lounge.",
        "address": "Strand",
        "country": "United Kingdom",
        "city": "London",
        "phone": "+442079460005",
        "email": "london@test-bookmaker.example",
        "stars": 5,
    },
    {
        "name": "Palazzo Verdi",
        "description": "Renowned palazzo near Piazza Navona with a cloister breakfast garden.",
        "address": "Via Giulia",
        "country": "Italy",
        "city": "Rome",
        "phone": "+39066800006",
        "email": "rome@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Vondelpark Lodge",
        "description": "Canal-side lodge beside the Vondelpark, bicycles available for guests.",
        "address": "Overtoom",
        "country": "Netherlands",
        "city": "Amsterdam",
        "phone": "+31206400007",
        "email": "amsterdam@test-bookmaker.example",
        "stars": 3,
    },
    {
        "name": "Brandenburger Hof",
        "description": "Grand hotel on Pariser Platz, a two minute walk from the Brandenburg Gate.",
        "address": "Friedrichstraße",
        "country": "Germany",
        "city": "Berlin",
        "phone": "+49302600008",
        "email": "berlin@test-bookmaker.example",
        "stars": 5,
    },
    {
        "name": "Hotel Alcázar",
        "description": "Andalusian courtyard hotel in the Santa Cruz quarter, next to the cathedral.",
        "address": "Calle Sierpes",
        "country": "Spain",
        "city": "Seville",
        "phone": "+34954900009",
        "email": "seville@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Sakura Ryokan",
        "description": "Traditional ryokan in Ginza with tatami rooms, onsen baths and kaiseki dinners.",
        "address": "Chūō-dōri",
        "country": "Japan",
        "city": "Tokyo",
        "phone": "+81335700010",
        "email": "tokyo@test-bookmaker.example",
        "stars": 5,
    },
    {
        "name": "Lakeshore Suites",
        "description": "Lakefront suites on the Magnificent Mile, walking distance to Navy Pier.",
        "address": "Michigan Avenue",
        "country": "United States",
        "city": "Chicago",
        "phone": "+13126400011",
        "email": "chicago@test-bookmaker.example",
        "stars": 4,
    },
    {
        "name": "Rhone Boutique Hotel",
        "description": "Boutique hotel on the lakeside promenade, close to the Jet d'Eau and old town.",
        "address": "Rue du Rhône",
        "country": "Switzerland",
        "city": "Geneva",
        "phone": "+41223100012",
        "email": "geneva@test-bookmaker.example",
        "stars": 4,
    },
]

CURRENCIES = (
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "CAD",
    "AUD",
    "CNY",
)

TEST_USER_PASSWORD = "Test1234!"

TEST_USERS = (
    {
        "name": "Emma Walker",
        "email": "emma.walker@test-bookmaker.example",
        "phone": "+447700900001",
        "birthday": "1992-04-17",
        "city": ("United Kingdom", "London"),
        "currency": "GBP",
        "photo": "https://i.pravatar.cc/150?img=5",
    },
    {
        "name": "Lucas Bernard",
        "email": "lucas.bernard@test-bookmaker.example",
        "phone": "+33612340002",
        "birthday": "1990-11-03",
        "city": ("France", "Paris"),
        "currency": "EUR",
        "photo": "https://i.pravatar.cc/150?img=12",
    },
    {
        "name": "Giulia Romano",
        "email": "giulia.romano@test-bookmaker.example",
        "phone": "+393331230003",
        "birthday": "1995-06-21",
        "city": ("Italy", "Rome"),
        "currency": "EUR",
        "photo": "https://i.pravatar.cc/150?img=9",
    },
    {
        "name": "Daan de Vries",
        "email": "daan.devries@test-bookmaker.example",
        "phone": "+31612340004",
        "birthday": "1988-02-09",
        "city": ("Netherlands", "Amsterdam"),
        "currency": "EUR",
        "photo": "https://i.pravatar.cc/150?img=33",
    },
    {
        "name": "Yuki Tanaka",
        "email": "yuki.tanaka@test-bookmaker.example",
        "phone": "+819012340005",
        "birthday": "1997-09-30",
        "city": ("Japan", "Tokyo"),
        "currency": "JPY",
        "photo": "https://i.pravatar.cc/150?img=47",
    },
    {
        "name": "Michael Brooks",
        "email": "michael.brooks@test-bookmaker.example",
        "phone": "+12125550006",
        "birthday": "1985-07-12",
        "city": ("United States", "New York City"),
        "currency": "USD",
        "photo": "https://i.pravatar.cc/150?img=52",
    },
    {
        "name": "Sophie Meier",
        "email": "sophie.meier@test-bookmaker.example",
        "phone": "+41791230007",
        "birthday": "1993-12-05",
        "city": ("Switzerland", "Zurich"),
        "currency": "CHF",
        "photo": "https://i.pravatar.cc/150?img=45",
    },
    {
        "name": "Olivia Bennett",
        "email": "olivia.bennett@test-bookmaker.example",
        "phone": "+13125550008",
        "birthday": "1991-03-28",
        "city": ("United States", "Chicago"),
        "currency": "USD",
        "photo": "https://i.pravatar.cc/150?img=26",
    },
)

MIN_REVIEWS_PER_HOTEL = 3
MAX_REVIEWS_PER_HOTEL = 4

REVIEW_RATING_SCALE = (1, 10)

REVIEW_SENTIMENTS = (
    "positive", "positive", "positive", "positive",
    "positive", "positive", "positive",
    "neutral", "neutral",
    "negative",
)

REVIEW_RATINGS = {
    "positive": (8, 9, 9, 10),
    "neutral": (5, 6, 7),
    "negative": (3, 4, 5),
}

REVIEW_TEXTS = {
    "positive": (
        "Great location and friendly staff. The room was clean and quiet all weekend.",
        "Perfect base for sightseeing, the breakfast had a good hot and cold selection.",
        "Comfortable bed and fast Wi-Fi. Would definitely book this hotel again.",
        "The staff went out of their way to help with luggage and restaurant bookings.",
        "Spacious room with a lovely view. Check-in was quick even late at night.",
        "Beautiful building and a great breakfast terrace. Only a short walk to the metro.",
        "Clean, modern room and an excellent shower. The gym was a nice bonus.",
        "Warm welcome and a spotless room. The neighbourhood has plenty of cafés.",
        "The restaurant inside the hotel surprised us — dinner was excellent.",
        "Quiet room facing the courtyard, which made sleeping easy despite the centre.",
    ),
    "neutral": (
        "Very good value for the price, though the walls are a bit thin.",
        "Ideal for a short city trip, but the room felt smaller than in the photos.",
        "Nice touches like free water and a city map at reception, the lift was often busy.",
        "Reliable choice for business travel: desk and fast internet, but a noisy lobby.",
        "Decent stay overall. Everything worked, but nothing really stood out.",
        "The location saves a lot of time, the breakfast could have had more variety.",
    ),
    "negative": (
        "Check-in took almost an hour and the room was not ready when we arrived.",
        "The Wi-Fi dropped constantly and the air conditioning was loud at night.",
        "Street noise came through the window even when it was closed.",
        "The bathroom needed a proper cleaning and the towels were worn out.",
        "Friendly reception, but the room did not match the description at all.",
        "Overpriced for what you get. We would look for something else next time.",
    ),
}

REVIEW_SUFFIXES = {
    "positive": (
        "We would happily stay at {name} again when we are back in {city}.",
        "{name} is our recommendation for a trip to {city}.",
        "For us, {name} was the best part of our time in {city}.",
        "We would book {name} again without hesitation on our next visit to {city}.",
        "Anyone travelling to {city} should consider {name} first.",
    ),
    "neutral": (
        "All in all {name} is a fair option in {city}.",
        "We would stay at {name} again only if the price in {city} drops.",
        "{name} does the job for a few nights in {city}.",
        "A decent base in {city}, though {name} has room to improve.",
    ),
    "negative": (
        "We cannot recommend {name} to anyone travelling to {city}.",
        "There are better places than {name} in {city}.",
        "Unless something changes, we will not return to {name} in {city}.",
        "For our next trip to {city} we will pick a different hotel than {name}.",
    ),
}

HOTELS_BY_EMAIL = {hotel["email"]: hotel for hotel in HOTELS}

TEST_PAYMENT_METHODS = (
    {
        "email": "emma.walker@test-bookmaker.example",
        "cardType": "Visa",
        "cardNumber": "4242424242424242",
        "date": "2029-05-31",
    },
    {
        "email": "michael.brooks@test-bookmaker.example",
        "cardType": "Mastercard",
        "cardNumber": "5555555555554444",
        "date": "2030-01-31",
    },
    {
        "email": "yuki.tanaka@test-bookmaker.example",
        "cardType": "American Express",
        "cardNumber": "378282246310005",
        "date": "2028-09-30",
    },
)

TEST_RESERVATIONS = (
    {"user": 0, "hotel": 0, "nights": 3, "daysAhead": 14},
    {"user": 1, "hotel": 4, "nights": 2, "daysAhead": 21},
    {"user": 2, "hotel": 5, "nights": 4, "daysAhead": 10},
    {"user": 3, "hotel": 6, "nights": 3, "daysAhead": 30},
    {"user": 4, "hotel": 9, "nights": 5, "daysAhead": 17},
    {"user": 5, "hotel": 2, "nights": 2, "daysAhead": 25},
    {"user": 6, "hotel": 7, "nights": 3, "daysAhead": 12},
    {"user": 7, "hotel": 11, "nights": 4, "daysAhead": 40},
)

ROOM_PHOTO_SETS = (
    ("Room1.jpg", "Room1.jpg", "Room2.jpg"),
    ("Room1.jpg", "Room2.jpg", "Room3.png"),
    ("Room2.jpg", "Room2.jpg", "Room3.png"),
    ("Room2.jpg", "Room3.png", "Room1.jpg"),
    ("Room3.png", "Room3.png", "Room1.jpg"),
    ("Room3.png", "Room1.jpg", "Room2.jpg"),
)

ROOMS_PER_HOTEL = 3

DEBIT_CARD_TYPES = (
    "Visa",
    "Mastercard",
    "Maestro",
    "American Express",
    "Discover",
)


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
            default=120,
            help="HTTP request timeout in seconds.",
        )

    def handle(self, *args, **options):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        source_directory = Path(settings.BASE_DIR) / "PicturesForTests"
        if not source_directory.is_dir():
            raise CommandError(f"Picture directory not found: {source_directory}")

        self.base_url = options["base_url"].rstrip("/")
        self.timeout = options["timeout"]
        self.manual_fallbacks = []
        self.distance_fallbacks = []
        self.session = requests.Session()
        self.access_tokens = {}

        try:
            self._load_debit_card_types()
            currencies = self._load_currencies()
            cities = self._load_countries_and_cities()
            users = self._load_users(cities, currencies)
            hotels = self._load_hotels_and_rooms(source_directory, cities)
            reviews = self._load_reviews(hotels, users)
            payment_methods = self._load_payment_methods(users)
            reservations = self._load_reservations(users)
        except requests.RequestException as error:
            raise CommandError(
                f"Could not connect to {self.base_url}. Start the Django server first. {error}"
            ) from error

        self._recalculate_distances(hotels)

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(cities)} cities and {len(hotels)} hotels through the API."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(users)} test users, {reviews} reviews, "
            f"{payment_methods} payment methods and {reservations} reservations."
        ))
        self.stdout.write(
            f"Test users can log in with the password: {TEST_USER_PASSWORD}"
        )
        if self.distance_fallbacks:
            self.stdout.write(self.style.WARNING(
                "Geoapify requests failed; fallback 10000 was used for: "
                + ", ".join(self.distance_fallbacks)
            ))
        else:
            self.stdout.write("Geoapify distance lookups completed without fallback.")
        if self.manual_fallbacks:
            self.stdout.write(self.style.WARNING(
                "Manual database fallbacks were used: "
                + ", ".join(self.manual_fallbacks)
            ))
        else:
            self.stdout.write("Manual database fallbacks: none.")

    def _load_debit_card_types(self):
        for card_name in DEBIT_CARD_TYPES:
            DebitCardEntity.objects.get_or_create(name=card_name)
        self.manual_fallbacks.append(
            "debit card types (no debit card creation API endpoint exists)"
        )

    def _load_currencies(self):
        currencies = {}
        for currency_name in CURRENCIES:
            currency, _ = CurrencyEntity.objects.get_or_create(currency=currency_name)
            currencies[currency_name] = currency
        self.manual_fallbacks.append(
            "currencies (no currency creation API endpoint exists)"
        )
        return currencies

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
                    time.sleep(GEOAPIFY_PAUSE)
                cities[(country_name, city_name)] = city
        return cities

    def _load_users(self, cities, currencies):
        users = []
        for user_data in TEST_USERS:
            country_name, city_name = user_data["city"]
            user, created = UserEntity.objects.get_or_create(
                email=user_data["email"],
                defaults={
                    "name": user_data["name"],
                    "hashPassword": make_password(TEST_USER_PASSWORD),
                    "phone": user_data["phone"],
                    "birthday": date.fromisoformat(user_data["birthday"]),
                    "photo": user_data["photo"],
                    "city": CityEntity.objects.get(
                        id=cities[(country_name, city_name)]["id"]
                    ),
                    "currency": currencies[user_data["currency"]],
                    "created": True,
                },
            )
            if not created:
                user.hashPassword = make_password(TEST_USER_PASSWORD)
                user.save(update_fields=["hashPassword"])
            users.append(user)
        self.manual_fallbacks.append(
            "test users (creating verified accounts through the API requires an emailed auth code)"
        )
        return users

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
                        "description": hotel_data["description"],
                        "address": hotel_data["address"],
                        "phone": hotel_data["phone"],
                        "email": hotel_data["email"],
                        "stars": hotel_data["stars"],
                        "city": cities[(hotel_data["country"], hotel_data["city"])]["id"],
                    },
                ).json()
                time.sleep(GEOAPIFY_PAUSE)
            self._clear_hotel_photos(hotel["id"])
            self._upload_file(
                f"/hotels/post/{hotel['id']}/photos/",
                source_directory / "Hotels" / HOTEL_PHOTOS[(hotel_number - 1) % len(HOTEL_PHOTOS)],
            )

            rooms = self._get_existing_rooms(hotel["id"])
            for room_number in range(1, ROOMS_PER_HOTEL + 1):
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
                            "privatePool": hotel_data["stars"] == 5 and room_number == 1,
                            "Bath": True,
                            "price": 100 + hotel_number * 25 + room_number,
                            "beds": (hotel_number + room_number) % 4 + 1,
                            "hotel": hotel["id"],
                        },
                    ).json()
                self._clear_room_photos(room["id"])
                photo_set_index = (hotel_number * 2 + room_number - 3) % len(ROOM_PHOTO_SETS)
                for source_name in ROOM_PHOTO_SETS[photo_set_index]:
                    self._upload_file(
                        f"/rooms/post/{room['id']}/photos/",
                        source_directory / "Rooms" / source_name,
                    )
            loaded_hotels.append(hotel)
        return loaded_hotels

    def _load_reviews(self, hotels, users):
        for pool in REVIEW_RATINGS.values():
            if not all(
                REVIEW_RATING_SCALE[0] <= rating <= REVIEW_RATING_SCALE[1]
                for rating in pool
            ):
                raise CommandError(
                    f"Review ratings must be inside {REVIEW_RATING_SCALE}."
                )
        rng = random.Random(20261006)
        reviewer_order = list(users)
        rng.shuffle(reviewer_order)
        reviewer_cursor = 0
        created = 0
        for hotel_index, hotel in enumerate(hotels):
            hotel_data = HOTELS_BY_EMAIL.get(hotel.get("email")) or HOTELS[hotel_index]
            review_count = rng.randint(MIN_REVIEWS_PER_HOTEL, MAX_REVIEWS_PER_HOTEL)
            reviewers = []
            for _ in range(min(review_count, len(reviewer_order))):
                reviewers.append(reviewer_order[reviewer_cursor % len(reviewer_order)])
                reviewer_cursor += 1
            used_texts = set()
            for user in reviewers:
                sentiment = rng.choice(REVIEW_SENTIMENTS)
                text_pool = REVIEW_TEXTS[sentiment]
                available = [
                    text_index
                    for text_index in range(len(text_pool))
                    if (sentiment, text_index) not in used_texts
                ] or list(range(len(text_pool)))
                text_index = rng.choice(available)
                used_texts.add((sentiment, text_index))
                suffix = rng.choice(REVIEW_SUFFIXES[sentiment]).format(
                    name=hotel_data["name"],
                    city=hotel_data["city"],
                )
                review_text = f"{text_pool[text_index]} {suffix}"
                created_at = timezone.now() - timedelta(
                    days=rng.randint(1, 150),
                    hours=rng.randint(0, 23),
                    minutes=rng.randint(0, 59),
                )
                rating = rng.choice(REVIEW_RATINGS[sentiment])
                if ReviewEntity.objects.filter(user=user, hotel_id=hotel["id"]).exists():
                    continue
                ReviewEntity.objects.create(
                    review=review_text,
                    createdAt=created_at,
                    user=user,
                    hotel_id=hotel["id"],
                    rating=rating,
                )
                created += 1
        self.manual_fallbacks.append(
            "reviews (no review creation API endpoint exists)"
        )
        return created

    def _load_payment_methods(self, users):
        users_by_email = {user.email: user for user in users}
        created = 0
        for method_data in TEST_PAYMENT_METHODS:
            if PaymentMethodEntity.objects.filter(cardNumber=method_data["cardNumber"]).exists():
                continue
            token = self._login(method_data["email"])
            self._request(
                "POST",
                "/payment-methods/create/",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "cardType": DebitCardEntity.objects.get(name=method_data["cardType"]).id,
                    "cardNumber": method_data["cardNumber"],
                    "date": method_data["date"],
                },
            )
            created += 1
        return created

    def _load_reservations(self, users):
        created = 0
        for reservation_data in TEST_RESERVATIONS:
            user = users[reservation_data["user"]]
            hotel = HotelEntity.objects.get(email=HOTELS[reservation_data["hotel"]]["email"])
            check_in = timezone.localdate() + timedelta(days=reservation_data["daysAhead"])
            check_out = check_in + timedelta(days=reservation_data["nights"])

            if ReservationEntity.objects.filter(
                user=user,
                room__hotel=hotel,
                checkOut__gte=timezone.localdate(),
            ).exists():
                continue

            rooms = RoomEntity.objects.filter(hotel=hotel).order_by("id")
            room = None
            for candidate in rooms:
                is_taken = ReservationEntity.objects.filter(
                    room=candidate,
                    checkIn__lt=check_out,
                    checkOut__gt=check_in,
                ).exists()
                if not is_taken:
                    room = candidate
                    break
            if room is None:
                continue

            name, _, sure_name = user.name.partition(" ")
            token = self._login(user.email)
            self._request(
                "POST",
                "/reservation/create/",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "checkIn": check_in.isoformat(),
                    "checkOut": check_out.isoformat(),
                    "name": name,
                    "sureName": sure_name or name,
                    "email": user.email,
                    "phoneNumber": user.phone,
                    "room": room.id,
                    "confirmByEmail": True,
                },
            )
            created += 1
        return created

    def _login(self, email):
        token = self.access_tokens.get(email)
        if token is not None:
            return token
        response = self._request(
            "POST",
            "/user/login",
            json={"email": email, "password": TEST_USER_PASSWORD},
        ).json()
        token = response["access"]
        self.access_tokens[email] = token
        return token

    def _clear_photos(self, folder, entity_id):
        photo_directory = Path(settings.MEDIA_ROOT) / folder / str(entity_id)
        if not photo_directory.is_dir():
            return
        for photo_path in photo_directory.iterdir():
            if photo_path.is_file():
                photo_path.unlink()

    def _clear_room_photos(self, room_id):
        self._clear_photos("rooms", room_id)

    def _clear_hotel_photos(self, hotel_id):
        self._clear_photos("hotels", hotel_id)

    @staticmethod
    def _format_distance(distance):
        if distance is None:
            return "n/a"
        if distance >= 1000:
            return f"{distance / 1000:.1f} km ({distance} m)"
        return f"{distance} m"

    def _recalculate_distances(self, seeded_hotels):
        self.stdout.write("Recalculating distances through Geoapify...")

        hotel_ids = [hotel["id"] for hotel in seeded_hotels]
        hotels = HotelEntity.objects.filter(pk__in=hotel_ids).select_related(
            "city", "city__country"
        ).order_by("id")

        for hotel in hotels:
            time.sleep(GEOAPIFY_PAUSE)
            label = f"{hotel.name} <{hotel.email or hotel.id}>"
            if hotel.latitude is None or hotel.longitude is None:
                try:
                    coordinates = get_coordinates(
                        hotel.address,
                        hotel.city.name,
                        hotel.city.country.name,
                    )
                except requests.RequestException as error:
                    self.stdout.write(self.style.WARNING(
                        f"  {label}: Geoapify geocoding failed "
                        f"({self._request_error_summary(error)})."
                    ))
                    self._save_distance_fallbacks(
                        hotel,
                        ("nearest_airport_distance", "nearest_train_distance"),
                        label,
                    )
                    continue

                if coordinates is None:
                    hotel.latitude = None
                    hotel.longitude = None
                    hotel.nearest_airport_distance = None
                    hotel.nearest_train_distance = None
                    hotel.save(update_fields=[
                        "latitude",
                        "longitude",
                        "nearest_airport_distance",
                        "nearest_train_distance",
                    ])
                    self.stdout.write(self.style.WARNING(
                        f"  {label}: Geoapify returned no coordinates; distances left empty."
                    ))
                    continue

                hotel.latitude, hotel.longitude = coordinates
                hotel.save(update_fields=["latitude", "longitude"])

            place_results = {}
            for place_type, field in (
                ("airport", "nearest_airport_distance"),
                ("train_station", "nearest_train_distance"),
            ):
                try:
                    place_results[place_type] = get_nearest_place(
                        float(hotel.latitude),
                        float(hotel.longitude),
                        place_type,
                    )
                except requests.RequestException as error:
                    self.stdout.write(self.style.WARNING(
                        f"  {label}: Geoapify {place_type} lookup failed "
                        f"({self._request_error_summary(error)})."
                    ))
                    setattr(hotel, field, 10000)
                    self.distance_fallbacks.append(label)
                else:
                    place = place_results[place_type]
                    setattr(hotel, field, place["distance"] if place else None)

            hotel.save(update_fields=[
                "nearest_airport_distance",
                "nearest_train_distance",
            ])
            airport = place_results.get("airport")
            train_station = place_results.get("train_station")
            self.stdout.write(
                f"  {label}: "
                f"airport={self._format_distance(hotel.nearest_airport_distance)}"
                f" [{airport['name'] if airport else 'not found'}], "
                f"train={self._format_distance(hotel.nearest_train_distance)}"
                f" [{train_station['name'] if train_station else 'not found'}]"
            )

    def _save_distance_fallbacks(self, hotel, fields, label):
        for field in fields:
            setattr(hotel, field, 10000)
        hotel.save(update_fields=list(fields))
        self.distance_fallbacks.append(label)

    @staticmethod
    def _request_error_summary(error):
        status_code = getattr(getattr(error, "response", None), "status_code", None)
        if status_code is not None:
            return f"{type(error).__name__}, HTTP {status_code}"
        return type(error).__name__

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
