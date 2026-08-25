from django.urls import path
from .EndPoints.UserController import *

urlpatterns = [
    path("user/sendAuthCode", sendAuthCode),
    path("user/createAccount", createAccount),
    path("user/verifyAccount", verifyAccount),
]
