from typing import Any, Dict
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass 
from rest_framework import serializers # type: ignore
# ignore сделан для того чтобы Pylance не ругался, особой роли он не играет и это не является ошибкой.

from .models import (
    CountryEntity,
    CityEntity,
    CurrencyEntity,
    DebitCardEntity,
    HotelEntity,
    PaymentMethodEntity,
    RoomEntity,
    UserEntity,
    ReservationEntity
)

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryEntity
        fields = [
            'id',
            'name'
        ]

class CitySerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=CountryEntity.objects.all())
    class Meta:
        model = CityEntity
        fields = [
            'id',
            'name',
            'center',
            'country'
        ]

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyEntity
        fields = [
            'id',
            'currency'
        ]

class DebitCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebitCardEntity
        fields = [
            'id',
            'name'
        ]

class PaymentMethodSerializer(serializers.ModelSerializer):
    cardType = serializers.PrimaryKeyRelatedField(queryset=DebitCardEntity.objects.all())

    class Meta:
        model = PaymentMethodEntity
        fields = [
            'id',
            'cardType',
            'cardNumber',
            'date'
        ]

class HotelSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=CityEntity.objects.all())

    class Meta:
        model = HotelEntity
        fields = [
            'id',
            'name',
            'description',
            'address',
            'phone',
            'email',
            'stars',
            'photo',
            'city'
        ]

    def validate_stars(self, value: int) -> int:
        if value < 0 or value > 5:
            raise serializers.ValidationError('Hotel stars must be between 0 and 5.')
        return value

class RoomSerializer(serializers.ModelSerializer):
    hotel = serializers.PrimaryKeyRelatedField(queryset=HotelEntity.objects.all())

    class Meta:
        model = RoomEntity
        fields = [
            'id',
            'roomNumber',
            'description',
            'wifi',
            'privatePool',
            'Bath',
            'price',
            'beds',
            'photo',
            'hotel'
        ]

    def validate_price(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError('Room price cannot be negative.')
        return value

    def validate_beds(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError('Number of beds must be greater than 0.')
        return value

class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    city = serializers.PrimaryKeyRelatedField(queryset=CityEntity.objects.all(), allow_null=True, required=False)
    currency = serializers.PrimaryKeyRelatedField(queryset=CurrencyEntity.objects.all(), allow_null=True, required=False)
    payMethod = serializers.PrimaryKeyRelatedField(queryset=PaymentMethodEntity.objects.all(), allow_null=True, required=False)
    hashPassword = serializers.CharField(write_only=True, required=False)
    authCode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = UserEntity
        fields = [
            'id',
            'name',
            'hashPassword',
            'email',
            'phone',
            'birthday',
            'photo',
            'ampthill',
            'authCode',
            'city',
            'currency',
            'payMethod'
        ]

class UserProfileUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=False)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=200)
    birthday = serializers.DateField(required=False, allow_null=True)
    ampthill = serializers.CharField(required=False, allow_blank=True, max_length=200)
    city = serializers.PrimaryKeyRelatedField(queryset=CityEntity.objects.all(), required=False, allow_null=True)
    country = serializers.PrimaryKeyRelatedField(queryset=CountryEntity.objects.all(), required=False, allow_null=True)
    currency = serializers.PrimaryKeyRelatedField(queryset=CurrencyEntity.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        city = data.get('city')
        country = data.get('country')
        
        if country and not city:
            raise serializers.ValidationError({'country': 'Country can only be specified together with a city.'})
        
        if city and country:
            if city.country_id != country.id:
                raise serializers.ValidationError({'city': 'The selected city does not belong to the selected country.'})
        return data

    def validate_email(self, value):
        if not value:
            return value
        user_id = self.context.get('user_id')
        if UserEntity.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError('Email is already in use by another user.')
        return value

    def validate_phone(self, value):
        if not value:
            return value
        user_id = self.context.get('user_id')
        if UserEntity.objects.filter(phone=value).exclude(id=user_id).exists():
            raise serializers.ValidationError('Phone number is already in use by another user.')
        return value

class ReservationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    room = serializers.PrimaryKeyRelatedField(queryset=RoomEntity.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=UserEntity.objects.all(), allow_null=True, required=False)
    country = serializers.PrimaryKeyRelatedField(queryset=CountryEntity.objects.all(), allow_null=True)
    payMethod = serializers.PrimaryKeyRelatedField(queryset=PaymentMethodEntity.objects.all(), allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ReservationEntity
        fields = [
            'id',
            'checkIn',
            'checkOut',
            'name',
            'sureName',
            'email',
            'password',
            'phoneNumber',
            'cityGuide',
            'room',
            'user',
            'country',
            'payMethod'
        ]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        check_in = attrs.get('checkIn')
        check_out = attrs.get('checkOut')
        if check_in and check_out:
            if check_out <= check_in:
                raise serializers.ValidationError({'checkOut': 'Check-out date must be later than check-in date.'})
        return attrs


class AuthAccountDTO():
    email: str
    password: str

class AdvancedSearchDTO(serializers.Serializer):
    land = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    checkIn = serializers.DateTimeField(required=False, allow_null=True)
    checkOut = serializers.DateTimeField(required=False, allow_null=True)
    people = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    nightPrice = serializers.FloatField(required=False, allow_null=True, min_value=0)
    rate = serializers.IntegerField(required=False, allow_null=True)
    stars = serializers.FloatField(required=False, allow_null=True)
    wifi = serializers.BooleanField(required=False, allow_null=True)

class HotelSearchDTO(serializers.Serializer):
    land = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    checkIn = serializers.DateTimeField(required=False, allow_null=True)
    checkOut = serializers.DateTimeField(required=False, allow_null=True)
    people = serializers.IntegerField(required=False, allow_null=True,min_value=1)