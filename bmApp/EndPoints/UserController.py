# for endPoints that working with user account.
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.db import IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from ..models import UserEntity
from datetime import datetime, timedelta
from ..functions.UserFunctions import *
from ..serializers import *
import json

def sendAuthCode(request):
    data = json.loads(request.body)
    authData = AuthAccountDTO(email = data.get("email"), password = data.get("password"))
    user = UserEntity.objects.get(email=authData.email)
    if user:
        if check_password(authData.password, user.hashPassword):
            user.authCode = make_password(send_auth_code(user.email))
            user.authCodeCreatedAt = datetime.now()
            user.save()
            return HttpResponse("OK", status=200)
        return HttpResponse("Incorrect passwrod or email")
    else:
        return HttpResponseNotFound("Incorrect passwrod or email")

def createAccount(request):
    data = json.loads(request.body)
    if request.method == "POST":
        authData = AuthAccountDTO(email = data.get("email"), password = data.get("password"))
        try:            
            user = UserEntity.objects.create(email = authData.email, 
                                            hashPassword = make_password(authData.password))
            return HttpResponse("CREATED", status=202)
        except IntegrityError:
            user = UserEntity.objects.get(email = authData.email)
            if(user.created):
                return HttpResponse("Account with this email already exist")
            else:
                user.hashPassword = make_password(authData.password)
                user.save()
        except:
            return HttpResponse("Error")

def verifyAccount(request):
    data = json.loads(request.body)
    if request.method == "PUT":
        authData = AuthAccountDTO(email = data.get("email"), password = data.get("password"))
        user = UserEntity.objects.get(email = authData.email)
        if(user.authCodeCreatedAt + timedelta(minutes=5) and 
           check_password(authData.password, user.authCode)):
            user.authCodeCreatedAt -= timedelta(minutes=50)
            if(user.created != True):
                user.created = True
            user.save()
            return HttpResponse("OK", status=202)
        else:
            return HttpResponse("Incorrect passwrod or email")

        

