from datetime import date, timedelta
from pathlib import Path
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
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


class UserPhotoTest(TestCase):
	def setUp(self):
		self.media_directory = Path(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, self.media_directory, ignore_errors=True)

		self.media_override = override_settings(MEDIA_ROOT=self.media_directory)
		self.media_override.enable()
		self.addCleanup(self.media_override.disable)

		self.user = self._create_user("avatar-owner@test-bookmaker.example")
		self.other_user = self._create_user("avatar-other@test-bookmaker.example")

		self.client = APIClient()
		self.client.force_authenticate(user=self.user)

	def _create_user(self, email):
		return UserEntity.objects.create(
			name="Avatar Owner",
			email=email,
			hashPassword=make_password("strong-password"),
			created=True,
		)

	def _upload(self, name="avatar.png", content_type="image/png"):
		return self.client.post(
			f"/user/{self.user.id}/photo/",
			{
				"file": SimpleUploadedFile(
					name,
					b"\x89PNG\r\n\x1a\n",
					content_type=content_type,
				)
			},
			format="multipart",
		)

	def _stored_photos(self):
		photo_directory = self.media_directory / "users" / str(self.user.id)
		if not photo_directory.exists():
			return []
		return [entry for entry in photo_directory.iterdir() if entry.is_file()]

	def test_upload_stores_avatar_and_returns_url(self):
		response = self._upload()

		self.assertEqual(response.status_code, 201)
		self.user.refresh_from_db()
		self.assertTrue(self.user.photo.startswith(f"users/{self.user.id}/"))
		self.assertEqual(len(self._stored_photos()), 1)
		self.assertEqual(response.json()["message"], "Photo uploaded successfully")
		self.assertTrue(response.json()["photo_url"].endswith(f"/media/{self.user.photo}"))

	def test_upload_replaces_previous_avatar(self):
		self._upload()
		self.user.refresh_from_db()
		previous_photo = self.user.photo

		response = self._upload(name="replacement.jpg", content_type="image/jpeg")

		self.assertEqual(response.status_code, 201)
		self.user.refresh_from_db()
		self.assertNotEqual(self.user.photo, previous_photo)
		self.assertFalse((self.media_directory / previous_photo).exists())
		self.assertEqual(len(self._stored_photos()), 1)

	def test_delete_removes_avatar(self):
		self._upload()
		self.user.refresh_from_db()
		photo_path = self.media_directory / self.user.photo

		response = self.client.delete(f"/user/{self.user.id}/photo/delete/")

		self.assertEqual(response.status_code, 200)
		self.user.refresh_from_db()
		self.assertIsNone(self.user.photo)
		self.assertFalse(photo_path.exists())
		self.assertEqual(self._stored_photos(), [])

	def test_delete_without_avatar_returns_not_found(self):
		response = self.client.delete(f"/user/{self.user.id}/photo/delete/")

		self.assertEqual(response.status_code, 404)

	def test_upload_rejects_non_image_file(self):
		response = self._upload(name="avatar.txt", content_type="text/plain")

		self.assertEqual(response.status_code, 400)

	def test_upload_rejects_missing_file(self):
		response = self.client.post(f"/user/{self.user.id}/photo/", {}, format="multipart")

		self.assertEqual(response.status_code, 400)

	def test_upload_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self._upload()

		self.assertEqual(response.status_code, 403)

	def test_upload_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self._upload()

		self.assertEqual(response.status_code, 401)

	def test_current_user_returns_absolute_photo_url(self):
		self._upload()
		self.user.refresh_from_db()

		response = self.client.get("/user/me/")

		self.assertEqual(response.status_code, 200)
		self.assertTrue(
			response.json()["photo"].startswith("http://testserver/media/users/")
		)


class UserProfileEndpointTest(TestCase):
	def setUp(self):
		self.country = CountryEntity.objects.create(name="Testland")
		self.city = CityEntity.objects.create(name="Test City", country=self.country)
		self.other_country = CountryEntity.objects.create(name="Otherland")
		self.other_city = CityEntity.objects.create(name="Other City", country=self.other_country)
		self.currency = CurrencyEntity.objects.create(currency="TST")

		self.user = UserEntity.objects.create(
			name="Original Name",
			email="profile-owner@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
			city=self.city,
			currency=self.currency,
			ampthill="",
		)
		self.other_user = UserEntity.objects.create(
			name="Other User",
			email="profile-other@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)

		self.client = APIClient()

	def test_public_profile_is_readable_without_authentication(self):
		response = self.client.get(f"/user/{self.user.id}/profile")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["id"], self.user.id)
		self.assertEqual(data["name"], "Original Name")
		self.assertIn("photo", data)

	def test_public_profile_returns_not_found_for_unknown_user(self):
		response = self.client.get("/user/999999/profile")

		self.assertEqual(response.status_code, 404)

	def test_current_user_includes_country(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.get("/user/me/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["country"], self.country.id)

	def test_profile_update_saves_name_and_reference_data(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.patch(
			f"/user/{self.user.id}/profile",
			{
				"name": "Renamed User",
				"phone": "+380000000001",
				"ampthill": "Test City",
				"city": self.city.id,
				"country": self.country.id,
				"currency": self.currency.id,
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["name"], "Renamed User")
		self.assertEqual(response.json()["country"], self.country.id)

		self.user.refresh_from_db()
		self.assertEqual(self.user.name, "Renamed User")
		self.assertEqual(self.user.city_id, self.city.id)
		self.assertEqual(self.user.currency_id, self.currency.id)
		self.assertEqual(self.user.ampthill, "Test City")

	def test_profile_update_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self.client.patch(
			f"/user/{self.user.id}/profile",
			{"name": "Hacked"},
			format="json",
		)

		self.assertEqual(response.status_code, 401)
		self.user.refresh_from_db()
		self.assertEqual(self.user.name, "Original Name")

	def test_profile_update_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self.client.patch(
			f"/user/{self.user.id}/profile",
			{"name": "Hacked"},
			format="json",
		)

		self.assertEqual(response.status_code, 403)
		self.user.refresh_from_db()
		self.assertEqual(self.user.name, "Original Name")

	def test_profile_update_rejects_city_from_another_country(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.patch(
			f"/user/{self.user.id}/profile",
			{"city": self.other_city.id, "country": self.country.id},
			format="json",
		)

		self.assertEqual(response.status_code, 400)

	def test_profile_update_keeps_country_consistent_with_city(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.patch(
			f"/user/{self.user.id}/profile",
			{"city": self.other_city.id, "country": self.other_country.id},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["country"], self.other_country.id)


class CurrencyEndpointTest(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_currencies_are_listed(self):
		CurrencyEntity.objects.create(currency="USD")
		CurrencyEntity.objects.create(currency="EUR")

		response = self.client.get("/currencies/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			[currency["currency"] for currency in response.json()],
			["USD", "EUR"],
		)


class MyReservationsEndpointTest(TestCase):
	def setUp(self):
		self.media_directory = Path(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, self.media_directory, ignore_errors=True)

		self.media_override = override_settings(MEDIA_ROOT=self.media_directory)
		self.media_override.enable()
		self.addCleanup(self.media_override.disable)

		self.country = CountryEntity.objects.create(name="Reservationland")
		self.city = CityEntity.objects.create(name="Reservation City", country=self.country)
		self.hotel = HotelEntity.objects.create(
			name="Reservation Hotel",
			address="Test street 1",
			phone="+3800000000001",
			email="reservation-hotel@test-bookmaker.example",
			stars=4,
			city=self.city,
			photo=f"hotels/99001/",
		)
		self.room = RoomEntity.objects.create(
			roomNumber="9001",
			description="Suite with a queen-size bed",
			wifi=True,
			privatePool=False,
			Bath=True,
			price=120,
			beds=2,
			photo=f"rooms/99001/",
			hotel=self.hotel,
		)

		room_photos = self.media_directory / "rooms" / "99001"
		room_photos.mkdir(parents=True)
		(room_photos / "room.jpg").write_bytes(b"\xff\xd8\xff")
		hotel_photos = self.media_directory / "hotels" / "99001"
		hotel_photos.mkdir(parents=True)
		(hotel_photos / "hotel.jpg").write_bytes(b"\xff\xd8\xff")

		self.user = UserEntity.objects.create(
			name="Booker",
			email="reservation-owner@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)
		self.other_user = UserEntity.objects.create(
			name="Other Booker",
			email="reservation-other@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)

		check_in = timezone.localdate() + timedelta(days=10)
		self.reservation = ReservationEntity.objects.create(
			checkIn=check_in,
			checkOut=check_in + timedelta(days=3),
			name="Booker",
			sureName="Tester",
			email=self.user.email,
			phoneNumber="+3800000000002",
			room=self.room,
			user=self.user,
			totalPrice=360,
		)
		ReservationEntity.objects.create(
			checkIn=check_in,
			checkOut=check_in + timedelta(days=3),
			name="Other",
			sureName="Booker",
			email=self.other_user.email,
			phoneNumber="+3800000000003",
			room=self.room,
			user=self.other_user,
		)

		self.client = APIClient()

	def test_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self.client.get("/user/reservations/")

		self.assertEqual(response.status_code, 401)

	def test_returns_only_own_reservations_with_room_data(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.get("/user/reservations/")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["count"], 1)

		entry = data["results"][0]
		self.assertEqual(entry["id"], self.reservation.id)
		self.assertEqual(entry["room"]["id"], self.room.id)
		self.assertEqual(entry["room"]["description"], "Suite with a queen-size bed")
		self.assertEqual(entry["room"]["beds"], 2)
		self.assertTrue(entry["room"]["wifi"])
		self.assertEqual(len(entry["room"]["photos"]), 1)
		self.assertTrue(entry["room"]["photos"][0].endswith("/media/rooms/99001/room.jpg"))
		self.assertEqual(entry["hotel"]["id"], self.hotel.id)
		self.assertEqual(entry["hotel"]["name"], "Reservation Hotel")
		self.assertEqual(entry["city"]["name"], "Reservation City")
		self.assertEqual(entry["city"]["country"]["name"], "Reservationland")
		self.assertEqual(entry["totalPrice"], "360.00")

	def test_returns_empty_list_for_user_without_reservations(self):
		self.client.force_authenticate(user=self.other_user)

		ReservationEntity.objects.all().delete()

		response = self.client.get("/user/reservations/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["count"], 0)

	def test_cancel_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self.client.post(f"/reservation/{self.reservation.id}/cancel/")

		self.assertEqual(response.status_code, 401)
		self.assertTrue(
			ReservationEntity.objects.filter(id=self.reservation.id).exists()
		)

	def test_cancel_removes_own_upcoming_reservation(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.post(f"/reservation/{self.reservation.id}/cancel/")

		self.assertEqual(response.status_code, 200)
		self.assertFalse(
			ReservationEntity.objects.filter(id=self.reservation.id).exists()
		)

	def test_cancel_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self.client.post(f"/reservation/{self.reservation.id}/cancel/")

		self.assertEqual(response.status_code, 403)
		self.assertTrue(
			ReservationEntity.objects.filter(id=self.reservation.id).exists()
		)

	def test_cancel_rejects_reservation_that_already_started(self):
		self.client.force_authenticate(user=self.user)
		self.reservation.checkIn = timezone.localdate() - timedelta(days=1)
		self.reservation.save(update_fields=["checkIn"])

		response = self.client.post(f"/reservation/{self.reservation.id}/cancel/")

		self.assertEqual(response.status_code, 409)
		self.assertTrue(
			ReservationEntity.objects.filter(id=self.reservation.id).exists()
		)


class MyReviewsEndpointTest(TestCase):
	def setUp(self):
		self.country = CountryEntity.objects.create(name="Reviewland")
		self.city = CityEntity.objects.create(name="Review City", country=self.country)
		self.hotel = HotelEntity.objects.create(
			name="Review Hotel",
			address="Review street 1",
			phone="+3800000000011",
			email="review-hotel@test-bookmaker.example",
			stars=5,
			city=self.city,
		)
		self.user = UserEntity.objects.create(
			name="Reviewer",
			email="review-owner@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)
		self.other_user = UserEntity.objects.create(
			name="Other Reviewer",
			email="review-other@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)

		self.review = ReviewEntity.objects.create(
			review="Wonderful stay, would come back.",
			createdAt=timezone.now(),
			user=self.user,
			hotel=self.hotel,
			rating=9,
		)
		ReviewEntity.objects.create(
			review="Not for us.",
			createdAt=timezone.now(),
			user=self.other_user,
			hotel=self.hotel,
			rating=4,
		)

		self.client = APIClient()

	def test_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self.client.get("/user/reviews/")

		self.assertEqual(response.status_code, 401)

	def test_returns_only_own_reviews_with_hotel_data(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.get("/user/reviews/")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["count"], 1)

		entry = data["results"][0]
		self.assertEqual(entry["id"], self.review.id)
		self.assertEqual(entry["rating"], 9)
		self.assertEqual(entry["hotel"]["id"], self.hotel.id)
		self.assertEqual(entry["hotel"]["name"], "Review Hotel")
		self.assertEqual(entry["hotel"]["city"], "Review City")
		self.assertEqual(entry["hotel"]["country"], "Reviewland")


class PaymentMethodManagementTest(TestCase):
	def setUp(self):
		self.card = DebitCardEntity.objects.create(name="Visa")
		self.user = UserEntity.objects.create(
			name="Payer",
			email="payment-owner@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)
		self.other_user = UserEntity.objects.create(
			name="Other Payer",
			email="payment-other@test-bookmaker.example",
			hashPassword=make_password("strong-password"),
			created=True,
		)
		self.payment_method = PaymentMethodEntity.objects.create(
			cardType=self.card,
			cardNumber="4242424242424242",
			date=date(2030, 1, 31),
			user=self.user,
		)
		self.user.payMethod = self.payment_method
		self.user.save(update_fields=["payMethod"])

		self.client = APIClient()
		self.client.force_authenticate(user=self.user)

	def test_delete_removes_own_payment_method_and_clears_default(self):
		response = self.client.delete(
			f"/payment-methods/{self.payment_method.id}/delete/"
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(
			PaymentMethodEntity.objects.filter(id=self.payment_method.id).exists()
		)
		self.user.refresh_from_db()
		self.assertIsNone(self.user.payMethod_id)

	def test_delete_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self.client.delete(
			f"/payment-methods/{self.payment_method.id}/delete/"
		)

		self.assertEqual(response.status_code, 403)
		self.assertTrue(
			PaymentMethodEntity.objects.filter(id=self.payment_method.id).exists()
		)

	def test_delete_returns_not_found_for_unknown_method(self):
		response = self.client.delete("/payment-methods/999999/delete/")

		self.assertEqual(response.status_code, 404)

	def test_set_default_marks_payment_method_as_active(self):
		response = self.client.post(
			f"/payment-methods/{self.payment_method.id}/default/"
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["payMethod"], self.payment_method.id)
		self.user.refresh_from_db()
		self.assertEqual(self.user.payMethod_id, self.payment_method.id)

	def test_set_default_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self.client.post(
			f"/payment-methods/{self.payment_method.id}/default/"
		)

		self.assertEqual(response.status_code, 403)
		self.other_user.refresh_from_db()
		self.assertIsNone(self.other_user.payMethod_id)

	def test_update_changes_date_and_card_type(self):
		second_card = DebitCardEntity.objects.create(name="MasterCard")

		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"cardType": second_card.id, "date": "2031-06-30"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.cardType_id, second_card.id)
		self.assertEqual(self.payment_method.date, date(2031, 6, 30))
		self.assertEqual(response.json()["cardNumber"], "**** **** **** 4242")

	def test_update_can_change_card_number(self):
		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"cardNumber": "4111111111111111"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.cardNumber, "4111111111111111")

	def test_update_keeps_card_number_when_not_provided(self):
		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"date": "2032-02-29"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.cardNumber, "4242424242424242")

	def test_update_rejects_card_number_used_by_another_user(self):
		other_payment_method = PaymentMethodEntity.objects.create(
			cardType=self.card,
			cardNumber="4111111111111111",
			date=date(2031, 1, 31),
			user=self.other_user,
		)

		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"cardNumber": other_payment_method.cardNumber},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.cardNumber, "4242424242424242")

	def test_update_rejects_masked_card_number(self):
		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"cardNumber": "**** **** **** 4242"},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.cardNumber, "4242424242424242")

	def test_update_requires_at_least_one_field(self):
		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{},
			format="json",
		)

		self.assertEqual(response.status_code, 400)

	def test_update_is_forbidden_for_another_user(self):
		self.client.force_authenticate(user=self.other_user)

		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"date": "2031-05-05"},
			format="json",
		)

		self.assertEqual(response.status_code, 403)
		self.payment_method.refresh_from_db()
		self.assertEqual(self.payment_method.date, date(2030, 1, 31))

	def test_update_returns_not_found_for_unknown_method(self):
		response = self.client.put(
			"/payment-methods/999999/update/",
			{"date": "2031-05-05"},
			format="json",
		)

		self.assertEqual(response.status_code, 404)

	def test_update_requires_authentication(self):
		self.client.force_authenticate(user=None)

		response = self.client.put(
			f"/payment-methods/{self.payment_method.id}/update/",
			{"date": "2031-05-05"},
			format="json",
		)

		self.assertEqual(response.status_code, 401)


