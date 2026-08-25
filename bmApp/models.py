from django.db import models

class CountryEntity(models.Model):
    name = models.CharField(max_length=200, unique=True)

class CityEntity(models.Model):
    name = models.CharField(max_length=200)
    country = models.ForeignKey(CountryEntity, on_delete=models.CASCADE)

class CurrencyEntity(models.Model):
    currency = models.CharField(max_length=200, unique=True)

class DebitCardEntity(models.Model):
    name = models.CharField(max_length=200, unique=True)

class HotelEntity(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=200, unique=True)
    email = models.CharField(max_length=200, unique=True)
    stars = models.IntegerField(default=0)
    photo = models.CharField(max_length=200, unique=True, blank=True, null=True) #Ведёт к дерикторию где лежат футажи
    city = models.ForeignKey(CityEntity, on_delete=models.CASCADE)

class PaymentMethodEntity(models.Model):
    cardType = models.ForeignKey(DebitCardEntity, on_delete=models.CASCADE)
    cardNumber = models.CharField(max_length=10, unique=True)
    date = models.DateField()

class RoomEntity(models.Model):
    roomNumber = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    wifi = models.BooleanField(default=False)
    privatePool = models.BooleanField(default=False)
    Bath = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    beds = models.IntegerField()
    hotel = models.ForeignKey(HotelEntity, on_delete=models.CASCADE)

class UserEntity(models.Model):
    name = models.CharField(max_length=200, blank=True)
    hashPassword = models.CharField(max_length=200)
    email = models.CharField(max_length=200, unique=True)
    phone = models.CharField(max_length=200, unique=True, blank=True)
    birthday = models.DateField(blank=True, null=True)
    photo = models.CharField(max_length=200, unique=True, blank=True) #Путь к аватарке пользователя
    ampthill = models.CharField(max_length=200, blank=True)
    authCode = models.CharField(max_length=200, blank=True)
    authCodeCreatedAt = models.DateTimeField(blank=True)
    created = models.BooleanField(default=False)
    city = models.ForeignKey(CityEntity, blank=True, null=True, on_delete=models.SET_NULL)
    currency = models.ForeignKey(CurrencyEntity, blank=True, null=True, on_delete=models.SET_NULL)
    payMethod = models.ForeignKey(PaymentMethodEntity, blank=True, null=True, on_delete=models.SET_NULL)

class ReservationEntity(models.Model):
    checkIn = models.DateField()
    checkOut = models.DateField()
    name = models.CharField(max_length=200)
    sureName = models.CharField(max_length=200)
    email = models.CharField(max_length=200, unique=True)
    password = models.CharField(max_length=200, blank=True)
    phoneNumber = models.CharField(max_length=200, unique=True)
    cityGuide = models.BooleanField(default=False)
    room = models.ForeignKey(RoomEntity, on_delete=models.CASCADE)
    user = models.ForeignKey(UserEntity, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(CountryEntity, on_delete=models.SET_NULL, null=True)
    payMethod = models.ForeignKey(PaymentMethodEntity, on_delete=models.SET_NULL, null=True)


