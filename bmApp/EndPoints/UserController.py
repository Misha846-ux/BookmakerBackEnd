from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from ..models import UserEntity
from datetime import timedelta
from django.utils import timezone
from ..functions.UserFunctions import send_auth_code
from ..serializers import UserProfileUpdateSerializer
import json
import requests as http_requests


@api_view(['POST'])
def sendAuthCode(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)

    try:
        user = UserEntity.objects.get(email=email)
    except UserEntity.DoesNotExist:
        return JsonResponse({"error": "Incorrect password or email."}, status=404)

    if not check_password(password, user.hashPassword):
        return JsonResponse({"error": "Incorrect password or email."}, status=401)

    user.authCode = make_password(send_auth_code(user.email))
    user.authCodeCreatedAt = timezone.now()
    user.save()
    return JsonResponse({"message": "OK"}, status=200)


@api_view(['POST'])
def createAccount(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)

    try:
        user = UserEntity.objects.create(
            email=email,
            hashPassword=make_password(password)
        )
        return JsonResponse({"message": "CREATED"}, status=201)
    except IntegrityError:
        try:
            user = UserEntity.objects.get(email=email)
        except UserEntity.DoesNotExist:
            return JsonResponse({"error": "Failed to create account."}, status=500)

        if user.created:
            return JsonResponse({"error": "Account with this email already exists."}, status=409)
        else:
            user.hashPassword = make_password(password)
            user.save()
            return JsonResponse({"message": "UPDATED"}, status=200)
    except Exception as e:
        return JsonResponse({"error": f"Error: {type(e).__name__}: {str(e)}"}, status=500)


@api_view(['PUT'])
def verifyAccount(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    email = data.get("email")
    code = data.get("password")

    if not email or not code:
        return JsonResponse({"error": "Email and code are required."}, status=400)

    try:
        user = UserEntity.objects.get(email=email)
    except UserEntity.DoesNotExist:
        return JsonResponse({"error": "User not found."}, status=404)

    if user.authCodeCreatedAt is None:
        return JsonResponse({"error": "No auth code requested."}, status=400)

    if timezone.now() > user.authCodeCreatedAt + timedelta(minutes=5):
        return JsonResponse({"error": "Auth code has expired."}, status=400)

    if not check_password(code, user.authCode):
        return JsonResponse({"error": "Incorrect code."}, status=400)

    if not user.created:
        user.created = True
    user.authCode = ""
    user.authCodeCreatedAt = None
    user.save()
    return JsonResponse({"message": "OK"}, status=200)


@api_view(['POST'])
def login(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)

    try:
        user = UserEntity.objects.get(email=email)
    except UserEntity.DoesNotExist:
        return JsonResponse({"error": "Incorrect email or password."}, status=401)

    if not check_password(password, user.hashPassword):
        return JsonResponse({"error": "Incorrect email or password."}, status=401)

    if not user.created:
        return JsonResponse({"error": "Account is not verified."}, status=403)

    refresh = RefreshToken()
    refresh["user_id"] = user.id
    refresh["email"] = user.email

    return JsonResponse({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getCurrentUser(request):
    user = request.user
    return JsonResponse({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "birthday": user.birthday,
        "photo": user.photo,
        "ampthill": user.ampthill,
        "city": user.city.id if user.city else None,
        "currency": user.currency.id if user.currency else None,
        "payMethod": user.payMethod.id if user.payMethod else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getProfileStatus(request):
    user = request.user
    has_info = bool(user.city or user.phone or user.birthday)
    return JsonResponse({"has_info": has_info})


@api_view(['POST'])
def googleLogin(request):
    token = request.data.get('access_token')
    if not token:
        return JsonResponse({"error": "access_token is required"}, status=400)

    google_response = http_requests.get(
        f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}",
        timeout=10
    )
    if google_response.status_code != 200:
        return JsonResponse({"error": "Invalid Google token"}, status=401)

    google_data = google_response.json()
    email = google_data.get('email')
    name = google_data.get('name', '')
    picture = google_data.get('picture', '')

    if not email:
        return JsonResponse({"error": "Email not available from Google"}, status=400)

    user, created = UserEntity.objects.get_or_create(
        email=email,
        defaults={
            'name': name,
            'hashPassword': make_password(make_password(None)),
            'created': True,
            'photo': picture or None,
            'phone': None,
        }
    )

    if not created and not user.created:
        user.created = True
        if not user.name:
            user.name = name
        user.save()

    refresh = RefreshToken()
    refresh["user_id"] = user.id
    refresh["email"] = user.email

    return JsonResponse({
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def updateUserProfile(request, user_id):
    if request.user.id != user_id:
        return JsonResponse({"error": "Forbidden."}, status=403)

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
    except IntegrityError:
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
