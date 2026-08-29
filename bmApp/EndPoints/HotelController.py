# for endPoints that working with Hotels
from django.db.models import Exists, OuterRef, Avg, Min
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from rest_framework.response import Response # type: ignore

from ..serializers import AdvancedSearchDTO, HotelSerializer
from ..models import *

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

