from pathlib import Path
import shutil
import tempfile

from django.conf import settings
from django.test import TestCase

from .models import CityEntity, CountryEntity, HotelEntity, RoomEntity


COUNTRIES_AND_CITIES = {
	"France": {
		"Paris": "Rue de Rivoli",
		"Lyon": "Rue de la République",
	},
	"United Kingdom": {
		"London": "Oxford Street",
		"Manchester": "Market Street",
	},
	"Italy": {
		"Rome": "Via del Corso",
		"Milan": "Corso Vittorio Emanuele II",
	},
	"Spain": {
		"Madrid": "Gran Vía",
		"Barcelona": "La Rambla",
	},
	"Germany": {
		"Berlin": "Unter den Linden",
		"Munich": "Kaufingerstraße",
	},
	"Netherlands": {
		"Amsterdam": "Kalverstraat",
		"Rotterdam": "Coolsingel",
	},
	"Austria": {
		"Vienna": "Kärntner Straße",
		"Salzburg": "Getreidegasse",
	},
	"Switzerland": {
		"Zurich": "Bahnhofstrasse",
		"Geneva": "Rue du Rhône",
	},
	"United States": {
		"New York City": "5th Avenue",
		"Chicago": "Michigan Avenue",
	},
	"Japan": {
		"Tokyo": "Chūō-dōri",
		"Kyoto": "Shijō-dori",
	},
}


class BookingDataTest(TestCase):
	def setUp(self):
		self.picture_source = Path(settings.BASE_DIR) / "PicturesForTests"
		self.picture_directory = Path(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, self.picture_directory, ignore_errors=True)

		self._create_countries_and_cities()
		self._create_hotels_and_rooms()

	def _create_countries_and_cities(self):
		for country_name, cities in COUNTRIES_AND_CITIES.items():
			country = CountryEntity.objects.create(name=country_name)
			CityEntity.objects.bulk_create([
				CityEntity(name=city_name, center=center, country=country)
				for city_name, center in cities.items()
			])

	def _copy_picture(self, folder_name, source_name, target_name):
		source = self.picture_source / folder_name / source_name
		target = self.picture_directory / target_name
		shutil.copy2(source, target)
		return str(target)

	def _create_hotels_and_rooms(self):
		city_by_name = {
			city.name: city
			for city in CityEntity.objects.filter(
				name__in=["Munich", "Salzburg", "New York City"]
			)
		}

		hotels = [
			{
				"name": "Leopold Grand Hotel",
				"address": "Leopoldstraße",
				"city": city_by_name["Munich"],
				"phone": "+49891234501",
				"email": "munich@test-bookmaker.example",
				"photo": self._copy_picture("Hotels", "Hotel1.png", "hotel-munich.png"),
			},
			{
				"name": "Linzer Gasse Palace",
				"address": "Linzer Gasse",
				"city": city_by_name["Salzburg"],
				"phone": "+436621234502",
				"email": "salzburg@test-bookmaker.example",
				"photo": self._copy_picture("Hotels", "Hotel2.jpg", "hotel-salzburg.jpg"),
			},
			{
				"name": "Broadway Central Hotel",
				"address": "Broadway",
				"city": city_by_name["New York City"],
				"phone": "+12125555003",
				"email": "new-york@test-bookmaker.example",
				"photo": self._copy_picture("Hotels", "Hotel3.jpg", "hotel-new-york.jpg"),
			},
		]

		for hotel_number, hotel_data in enumerate(hotels, start=1):
			hotel = HotelEntity.objects.create(
				description=f"Test hotel {hotel_number}",
				stars=4,
				**hotel_data,
			)

			for room_number in range(1, 3):
				source_name = ["Room1.jpg", "Room2.jpg", "Room3.png"][
					(hotel_number * 2 + room_number - 3) % 3
				]
				room_photo = self._copy_picture(
					"Rooms",
					source_name,
					f"hotel-{hotel_number}-room-{room_number}-{source_name}",
				)
				RoomEntity.objects.create(
					roomNumber=f"{hotel_number}0{room_number}",
					description=f"Test room {hotel_number}-{room_number}",
					wifi=True,
					privatePool=False,
					Bath=True,
					price=100 + hotel_number * 25 + room_number,
					beds=2,
					photo=room_photo,
					hotel=hotel,
				)

	def test_reference_data_and_booking_records_are_loaded(self):
		self.assertEqual(CountryEntity.objects.count(), 10)
		self.assertEqual(CityEntity.objects.count(), 20)
		self.assertEqual(HotelEntity.objects.count(), 3)
		self.assertEqual(RoomEntity.objects.count(), 6)

		for country_name, cities in COUNTRIES_AND_CITIES.items():
			country = CountryEntity.objects.get(name=country_name)
			for city_name, center in cities.items():
				city = CityEntity.objects.get(name=city_name, country=country)
				self.assertEqual(city.center, center)

		hotels = HotelEntity.objects.select_related("city__country").prefetch_related("roomentity_set")
		expected_addresses = {
			"Munich": "Leopoldstraße",
			"Salzburg": "Linzer Gasse",
			"New York City": "Broadway",
		}

		for hotel in hotels:
			self.assertEqual(hotel.address, expected_addresses[hotel.city.name])
			self.assertTrue(Path(hotel.photo).is_file())
			self.assertEqual(hotel.roomentity_set.count(), 2)
			for room in hotel.roomentity_set.all():
				self.assertTrue(Path(room.photo).is_file())
