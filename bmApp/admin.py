from django.contrib import admin

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


@admin.register(CountryEntity)
class CountryEntityAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)


@admin.register(CityEntity)
class CityEntityAdmin(admin.ModelAdmin):
	list_display = ("name", "country", "center")
	list_filter = ("country",)
	search_fields = ("name", "center", "country__name")


@admin.register(CurrencyEntity)
class CurrencyEntityAdmin(admin.ModelAdmin):
	list_display = ("currency",)
	search_fields = ("currency",)


@admin.register(DebitCardEntity)
class DebitCardEntityAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)


@admin.register(HotelEntity)
class HotelEntityAdmin(admin.ModelAdmin):
	list_display = ("name", "city", "stars", "phone", "email")
	list_filter = ("stars", "city__country")
	search_fields = ("name", "address", "phone", "email", "city__name")


@admin.register(PaymentMethodEntity)
class PaymentMethodEntityAdmin(admin.ModelAdmin):
	list_display = ("cardType", "cardNumber", "date")
	list_filter = ("cardType",)
	search_fields = ("cardNumber", "cardType__name")


@admin.register(RoomEntity)
class RoomEntityAdmin(admin.ModelAdmin):
	list_display = ("roomNumber", "hotel", "price", "beds", "wifi", "privatePool", "Bath")
	list_filter = ("wifi", "privatePool", "Bath", "hotel__city__country")
	search_fields = ("roomNumber", "hotel__name", "hotel__city__name")


@admin.register(UserEntity)
class UserEntityAdmin(admin.ModelAdmin):
	list_display = ("name", "email", "phone", "city", "created")
	list_filter = ("created", "city__country")
	search_fields = ("name", "email", "phone")


@admin.register(ReservationEntity)
class ReservationEntityAdmin(admin.ModelAdmin):
	list_display = ("name", "sureName", "room", "checkIn", "checkOut", "email")
	list_filter = ("checkIn", "checkOut", "cityGuide")
	search_fields = ("name", "sureName", "email", "phoneNumber", "room__roomNumber")


@admin.register(ReviewEntity)
class ReviewEntityAdmin(admin.ModelAdmin):
	list_display = ("hotel", "user", "rating", "createdAt")
	list_filter = ("rating", "createdAt")
	search_fields = ("hotel__name", "user__name", "user__email", "review")
