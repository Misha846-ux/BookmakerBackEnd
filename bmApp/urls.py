from django.urls import path

from .EndPoints.RoomController import createRoom
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
    path("rooms/<int:room_id>/photos/", uploadRoomPhotos),
    path("rooms/<int:room_id>/photos/", getRoomPhotos),
    path("hotels/get/", getHotels),
    path("hotels/create/", createHotel),
    path("rooms/create/", createRoom),
    path("payment-methods/create/", createPaymentMethod),
]
