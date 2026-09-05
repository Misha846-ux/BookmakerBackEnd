# for endPoints that working with Hotels
from django.db.models import Exists, OuterRef, Avg, Min, Case, When, Value, F, IntegerField
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from rest_framework.response import Response # type: ignore
from ..serializers import *
from ..models import *
import os
from django.conf import settings
from django.urls import reverse
import uuid

@api_view(['POST'])
def createHotel(request):

    serializer = HotelSerializer(data=request.data)

    if serializer.is_valid():
        hotel = serializer.save()

        return Response(
            HotelSerializer(hotel).data,
            status=201
        )

    return Response(
        serializer.errors,
        status=400
    )

@api_view(['GET'])
def getHotels(request):

    hotels = HotelEntity.objects.all()

    city = request.query_params.get('city')

    if city:
        hotels = hotels.filter(city_id=city)

    min_price = request.query_params.get('minPrice')

    if min_price:
        hotels = hotels.annotate(
            min_room_price=Min("roomentity_set__price")
        ).filter(
            min_room_price__gte=min_price
        )

    rating = request.query_params.get('rating')

    if rating:
        hotels = hotels.annotate(
            average_rate=Avg("reviewentity_set__rating")
        ).filter(
            average_rate__gte=rating
        )

    stars = request.query_params.get('stars')

    if stars:
        hotels = hotels.filter(
            stars=stars
        )

    # Remove duplicates
    hotels = hotels.distinct()

    page = int(request.query_params.get('page', 1))

    page_size = 30

    start = (page - 1) * page_size
    end = start + page_size

    total = hotels.count()

    hotels = hotels[start:end]

    serializer = HotelSerializer(
        hotels,
        many=True
    )

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'results': serializer.data
    })


def AdvencedSearch(request):
    dto = AdvancedSearchDTO(data=request.data)
    dto.is_valid(raise_exeption=True)

    data = dto.validated_data

    el = int(request.query_params.get("el", 10))
    page = int(request.query_params.get("page", 1))

    if(page < 1):
        page = 1

    hotels = HotelEntity.objects.all()

    if data.get("land"):
        hotels = hotels.filter(city__country__name__iexact = data["land"])

    if data.get("city"):
        hotels = hotels.filter(city__name__iexact = data["city"])

    if data.get("people"):
        hotels = hotels.filter(roomentity_set__beds__gte = data["people"])

    if data.get("nightPrice"):
        hotels = hotels.filter(roomentity_set__price__lte = data["nightPrice"])

    if data.get("rate"):
        hotels = hotels.annotate(average_rate=Avg("reviewentity_set__rating")).filter(
            average_rate__gte=data["rate"])

    if data.get("stars"):
        hotels = hotels.filter(stars__gte=data["stars"])

    if data.get("wifi"):
        hotels = hotels.filter(roomentity_set__wifi=data["wifi"])

    check_in = data.get("checkIn")
    check_out = data.get("checkOut")

    if check_in or check_out:

        check_in_date = check_in.date() if check_in else None
        check_out_date = check_out.date() if check_out else None

        reserved_rooms = ReservationEntity.objects.filter(
            room=OuterRef("pk")
        )
        if check_in_date and not check_out_date:
            reserved_rooms = reserved_rooms.filter(
                checkIn__lte=check_in_date, checkOut__gt=check_in_date)
        else:
            reserved_rooms = reserved_rooms.filter(
                checkIn__lt=check_out_date, checkOut__gt=check_in_date)

        free_rooms = RoomEntity.objects.annotate(is_reserved=Exists(reserved_rooms)).filter(
            is_reserved=False)

        hotels = hotels.filter(roomentity_set__in=free_rooms)

    hotels = hotels.distinct()
    total = hotels.count()

    start = (page - 1) * el
    end = start + el

    hotels = hotels[start:end]

    serializer = HotelSerializer(hotels, many=True)

    return Response(serializer.data, status = 200)


def Search(request):
    dto = HotelSearchDTO(data=request.data)
    dto.is_valid(raise_exception=True)

    data = dto.validated_data

    hotels = HotelEntity.objects.all()

    if data.get("land"):
        hotels = hotels.filter(city__country__name__iexact=data["land"])

    if data.get("city"):
        hotels = hotels.filter(city__name__iexact = data["city"])

    if data.get("people"):
        hotels = hotels.filter(roomentity_set__beds__gte=data["people"])

    check_in = data.get("checkIn")
    check_out = data.get("checkOut")

    if check_in or check_out:

        check_in_date = check_in.date() if check_in else None
        check_out_date = check_out.date() if check_out else None

        reserved_rooms = ReservationEntity.objects.filter(
            room=OuterRef("pk")
        )
        if check_in_date and not check_out_date:
            reserved_rooms = reserved_rooms.filter(
                checkIn__lte=check_in_date, checkOut__gt=check_in_date)
        else:
            reserved_rooms = reserved_rooms.filter(
                checkIn__lt=check_out_date, checkOut__gt=check_in_date)

        free_rooms = RoomEntity.objects.annotate(is_reserved=Exists(reserved_rooms)).filter(
            is_reserved=False)

        hotels = hotels.filter(roomentity_set__in=free_rooms)

    hotels = hotels.distinct()

    serializer = HotelSerializer(hotels, many=True)

    return Response(serializer.data, status=200)

@api_view(['POST'])
def uploadHotelPhotos(request, hotel_id):
    try:
        hotel = HotelEntity.objects.get(id=hotel_id)
    except HotelEntity.DoesNotExist:
        return Response({'error': 'Hotel not found'}, status=404)
    
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    photo_dir = f'hotels/{hotel_id}/'
    photo_dir_path = os.path.join(settings.MEDIA_ROOT, photo_dir)
    
    os.makedirs(photo_dir_path, exist_ok=True)
    
    file_name, file_ext = os.path.splitext(file.name)
    unique_filename = f'{file_name}_{uuid.uuid4().hex[:8]}{file_ext}'
    
    file_path = os.path.join(photo_dir_path, unique_filename)
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    hotel.photo = photo_dir
    hotel.save()
    
    return Response({'message': 'Photo uploaded successfully', 'photo_url': f'{settings.MEDIA_URL}{photo_dir}{unique_filename}'}, status=201)

@api_view(['GET'])
def getHotelPhotos(request, hotel_id):
    try:
        hotel = HotelEntity.objects.get(id=hotel_id)
    except HotelEntity.DoesNotExist:
        return Response({'error': 'Hotel not found'}, status=404)
    
    if not hotel.photo:
        return Response({'photos': []}, status=200)
    
    photo_dir_path = os.path.join(settings.MEDIA_ROOT, hotel.photo)
    
    if not os.path.exists(photo_dir_path):
        return Response({'photos': []}, status=200)
    
    photos = []
    try:
        for filename in os.listdir(photo_dir_path):
            file_path = os.path.join(photo_dir_path, filename)
            if os.path.isfile(file_path):
                photo_url = f'{settings.MEDIA_URL}{hotel.photo}{filename}'
                photos.append({'photo': photo_url})
    except Exception as e:
        return Response({'error': f'Error reading photos: {str(e)}'}, status=500)
    
    return Response({'photos': photos}, status=200)

@api_view(['POST'])
def getHotelRooms(request, hotel_id):
    try:
        hotel = HotelEntity.objects.get(id=hotel_id)
    except HotelEntity.DoesNotExist:
        return Response({'error': 'Hotel not found'}, status=404)

    dto = AdvancedSearchDTO(data=request.data)
    dto.is_valid(raise_exception=True)
    data = dto.validated_data

    try:
        el = int(request.query_params.get("el", 10))
        page = int(request.query_params.get("page", 1))
    except (ValueError, TypeError):
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)

    if el < 1 or page < 1:
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)

    rooms = RoomEntity.objects.filter(hotel_id=hotel_id)

    if data.get("people"):
        rooms = rooms.filter(beds__gte=data["people"])

    if data.get("nightPrice"):
        rooms = rooms.filter(price__lte=data["nightPrice"])

    check_in = data.get("checkIn")
    check_out = data.get("checkOut")

    if check_in or check_out:
        check_in_date = check_in.date() if check_in else None
        check_out_date = check_out.date() if check_out else None

        reserved_rooms = ReservationEntity.objects.filter(room=OuterRef("pk"))

        if check_in_date and not check_out_date:
            reserved_rooms = reserved_rooms.filter(checkIn__lte=check_in_date, checkOut__gt=check_in_date)
        elif check_out_date and not check_in_date:
            reserved_rooms = reserved_rooms.filter(checkIn__lt=check_out_date, checkOut__gt=check_out_date)
        else:
            reserved_rooms = reserved_rooms.filter(checkIn__lt=check_out_date, checkOut__gt=check_in_date)

        rooms = rooms.annotate(is_reserved=Exists(reserved_rooms)).filter(is_reserved=False)

    annotations = {}
    order_fields = []

    if data.get("nightPrice"):
        annotations['price_closeness'] = F('price')
        order_fields.append('-price_closeness')

    if data.get("wifi"):
        annotations['wifi_match'] = Case(When(wifi=True, then=Value(1)), default=Value(0), output_field=IntegerField())
        order_fields.append('-wifi_match')

    order_fields.append('id')

    if annotations:
        rooms = rooms.annotate(**annotations)

    rooms = rooms.order_by(*order_fields)

    total = rooms.count()
    start = (page - 1) * el
    end = start + el
    rooms = rooms[start:end]

    serializer = RoomSerializer(rooms, many=True)

    return Response({
        'count': total,
        'page': page,
        'el': el,
        'total_pages': (total + el - 1) // el,
        'results': serializer.data
    }, status=200)