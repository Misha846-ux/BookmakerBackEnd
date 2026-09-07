from django.urls import path

from .EndPoints.CityController import *
from .EndPoints.UserController import *
from .EndPoints.HotelController import *
from .EndPoints.RoomController import *
from .EndPoints.PaymentMethodController import createPaymentMethod

urlpatterns = [
    path("user/sendAuthCode", sendAuthCode),
    path("user/createAccount", createAccount),
    path("user/verifyAccount", verifyAccount),
    path("user/<int:user_id>/profile", updateUserProfile),
    path("hotels/advancedFilter/", AdvencedSearch),
    path("hotels/<int:hotel_id>/photos/", uploadHotelPhotos),
    path("hotels/<int:hotel_id>/photos/", getHotelPhotos),
    path("hotels/<int:hotel_id>/rooms/", getHotelRooms),
    path("hotels/get/", getHotels),
    path("hotels/create/", createHotel),
    path("hotels/<int:hotel_id>/NearestTrainStation/", getHotelNearestTrainStation),
    path("hotels/<int:hotel_id>/NearestAirport/", getHotelNearestAirport),
    path('hotels/<int:hotel_id>/CityCenter/', getHotelCityCenter,),
    path("rooms/<int:room_id>/photos/", uploadRoomPhotos),
    path("rooms/<int:room_id>/photos/", getRoomPhotos),
    path("rooms/create/", createRoom),
    path("payment-methods/create/", createPaymentMethod),
    path('cities/', getCities),
    path('cities/create/', createCity),
    path('cities/<int:city_id>/', getCity),
    path('cities/<int:city_id>/update/', updateCity),
    path('cities/<int:city_id>/delete/', deleteCity),
]
