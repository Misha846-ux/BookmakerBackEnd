from django.urls import path
from .EndPoints.UserController import *
from .EndPoints.HotelController import *

urlpatterns = [
    path("user/sendAuthCode", sendAuthCode),
    path("user/createAccount", createAccount),
    path("user/verifyAccount", verifyAccount),
    path("hotels/advancedFilter/", AdvencedSearch),
    path("hotels/get/", getHotels),
    path("hotels/create/", createHotel),
]
