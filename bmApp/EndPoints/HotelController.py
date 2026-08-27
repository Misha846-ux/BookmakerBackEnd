# for endPoints that working with Hotels
from django.db.models import Exists, OuterRef, Avg
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from rest_framework.response import Response # type: ignore
from ..serializers import AdvancedSearchDTO
from ..models import *

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
