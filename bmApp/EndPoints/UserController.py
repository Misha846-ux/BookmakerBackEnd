# for endPoints that working with user account.
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
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

@api_view(['POST'])
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
        # except:
        #     return HttpResponse("Error")
        except Exception as e:
            return HttpResponse(
                f"Error: {type(e).__name__}: {str(e)}",
                status=500
            )

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

@api_view(['POST'])
def login(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Method not allowed. Use POST."},
            status=405
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON format."},
            status=400
        )

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JsonResponse(
            {"error": "Email and password are required."},
            status=400
        )

    try:
        user = UserEntity.objects.get(email=email)
    except UserEntity.DoesNotExist:
        return JsonResponse(
            {"error": "Incorrect email or password."},
            status=401
        )

    if not check_password(password, user.hashPassword):
        return JsonResponse(
            {"error": "Incorrect email or password."},
            status=401
        )

    if not user.created:
        return JsonResponse(
            {"error": "Account is not verified."},
            status=403
        )

    refresh = RefreshToken()

    refresh["user_id"] = user.id
    refresh["email"] = user.email

    return JsonResponse({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }, status=200)


def updateUserProfile(request, user_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed. Use PATCH."}, status=405)
    
    try:
        user = UserEntity.objects.get(id=user_id)
    except UserEntity.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    
    serializer = UserProfileUpdateSerializer(data=data, partial=True, context={'user_id': user_id})
    
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)
    
    validated_data = serializer.validated_data
    
    if 'email' in validated_data:
        user.email = validated_data['email']
    if 'phone' in validated_data:
        user.phone = validated_data['phone']
    if 'birthday' in validated_data:
        user.birthday = validated_data['birthday']
    if 'ampthill' in validated_data:
        user.ampthill = validated_data['ampthill']
    if 'city' in validated_data:
        user.city = validated_data['city']
    if 'currency' in validated_data:
        user.currency = validated_data['currency']
    
    try:
        user.save()
    except IntegrityError as e:
        return JsonResponse({"error": "Failed to update user profile due to data conflict."}, status=400)
    
    response_data = {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "birthday": user.birthday,
        "ampthill": user.ampthill,
        "city": user.city.id if user.city else None,
        "country": user.city.country.id if user.city and user.city.country else None,
        "currency": user.currency.id if user.currency else None,
    }
    
    return JsonResponse(response_data, status=200)