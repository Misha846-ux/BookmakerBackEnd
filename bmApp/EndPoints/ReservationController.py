from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError, transaction
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone
import os
import secrets
from ..models import ReservationEntity, RoomEntity, UserEntity
from ..serializers import ReservationSerializer


def _media_photo_urls(request, photo_dir):
    if not photo_dir:
        return []

    directory = os.path.join(settings.MEDIA_ROOT, photo_dir)
    if not os.path.isdir(directory):
        return []

    urls = []
    try:
        for filename in sorted(os.listdir(directory)):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                urls.append(request.build_absolute_uri(
                    f'{settings.MEDIA_URL}{photo_dir}{filename}'
                ))
    except OSError:
        return []

    return urls


def _reservation_dto(request, reservation):
    room = reservation.room
    hotel = room.hotel
    city = hotel.city

    return {
        'id': reservation.id,
        'checkIn': reservation.checkIn,
        'checkOut': reservation.checkOut,
        'totalPrice': str(reservation.totalPrice) if reservation.totalPrice is not None else None,
        'viewToken': reservation.viewToken,
        'room': {
            'id': room.id,
            'roomNumber': room.roomNumber,
            'description': room.description,
            'wifi': room.wifi,
            'privatePool': room.privatePool,
            'Bath': room.Bath,
            'price': str(room.price),
            'beds': room.beds,
            'photos': _media_photo_urls(request, room.photo),
        },
        'hotel': {
            'id': hotel.id,
            'name': hotel.name,
            'stars': hotel.stars,
            'photos': _media_photo_urls(request, hotel.photo),
        },
        'city': {
            'id': city.id,
            'name': city.name,
            'country': {
                'id': city.country_id,
                'name': city.country.name if city.country else None,
            },
        },
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyReservations(request):
    reservations = list(
        ReservationEntity.objects.filter(user=request.user).select_related(
            'room',
            'room__hotel',
            'room__hotel__city',
            'room__hotel__city__country',
        )
    )

    today = timezone.localdate()
    upcoming = [reservation for reservation in reservations if reservation.checkOut >= today]
    past = [reservation for reservation in reservations if reservation.checkOut < today]
    upcoming.sort(key=lambda reservation: reservation.checkIn)
    past.sort(key=lambda reservation: reservation.checkIn, reverse=True)
    reservations = upcoming + past

    return Response({
        'count': len(reservations),
        'results': [_reservation_dto(request, reservation) for reservation in reservations],
    }, status=200)


@api_view(['POST'])
def createReservation(request):
    serializer = ReservationSerializer(
        data=request.data,
        context={'request': request},
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    validated_data = serializer.validated_data

    room = validated_data['room']
    check_in = validated_data['checkIn']
    check_out = validated_data['checkOut']

    user = getattr(request, 'user', None)
    is_authenticated = bool(user is not None and getattr(user, 'is_authenticated', False))

    pay_method = validated_data.get('payMethod')
    if pay_method is not None:
        if is_authenticated:
            if pay_method.user_id is None:
                pay_method.user = user
                pay_method.save(update_fields=['user'])
            elif pay_method.user_id != user.id:
                return Response(
                    {'error': 'Payment method does not belong to this user.'},
                    status=400,
                )
        elif pay_method.user_id is not None:
            return Response(
                {'error': 'Payment method does not belong to this user.'},
                status=400,
            )

    save_data = dict(validated_data)
    password = save_data.pop('password', None)
    save_data.pop('user', None)
    save_data.pop('payMethod', None)
    save_data.pop('id', None)

    if check_in < timezone.localdate():
        return Response(
            {'error': 'Check-in date cannot be in the past.'},
            status=400,
        )

    if is_authenticated:
        save_data['user'] = user
    else:
        save_data['user'] = None
        if password:
            if len(password) < 6:
                return Response(
                    {'error': 'Password must be at least 6 characters long.'},
                    status=400,
                )
            email = validated_data['email']
            existing_user = UserEntity.objects.filter(email=email).first()
            if existing_user is None:
                guest_user = UserEntity.objects.create(
                    email=email,
                    name=f"{validated_data['name']} {validated_data['sureName']}".strip(),
                    phone=validated_data.get('phoneNumber'),
                    hashPassword=make_password(password),
                    created=False,
                )
                save_data['user'] = guest_user
            elif not check_password(password, existing_user.hashPassword):
                return Response(
                    {'error': 'An account with this email already exists and the password is incorrect.'},
                    status=400,
                )
            else:
                save_data['user'] = existing_user

    save_data['payMethod'] = pay_method
    nights = (check_out - check_in).days
    save_data['totalPrice'] = room.price * nights

    try:
        with transaction.atomic():
            locked_room = RoomEntity.objects.select_for_update().get(pk=room.pk)

            is_conflict = ReservationEntity.objects.filter(
                room=locked_room,
                checkIn__lt=check_out,
                checkOut__gt=check_in,
            ).exists()

            if is_conflict:
                return Response(
                    {
                        'error': 'This room is already booked for the selected dates.',
                        'code': 'room_unavailable',
                    },
                    status=409,
                )

            save_data['room'] = locked_room
            reservation = ReservationEntity.objects.create(**save_data)
    except RoomEntity.DoesNotExist:
        return Response({'error': 'Room not found.'}, status=404)
    except IntegrityError:
        return Response(
            {'error': 'Failed to create reservation due to a data conflict.'},
            status=400,
        )

    return Response(ReservationSerializer(reservation).data, status=201)


@api_view(['GET'])
def getReservation(request, reservation_id):
    try:
        reservation = ReservationEntity.objects.get(id=reservation_id)
    except ReservationEntity.DoesNotExist:
        return Response({'error': 'Reservation not found.'}, status=404)

    token = request.query_params.get('token')
    if token and secrets.compare_digest(str(reservation.viewToken), token):
        return Response(ReservationSerializer(reservation).data, status=200)

    user = getattr(request, 'user', None)
    is_authenticated = bool(user is not None and getattr(user, 'is_authenticated', False))
    if is_authenticated:
        if reservation.user_id == user.id:
            return Response(ReservationSerializer(reservation).data, status=200)
        return Response({'error': 'Forbidden.'}, status=403)

    return Response({'error': 'Authentication required.'}, status=401)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancelReservation(request, reservation_id):
    try:
        reservation = ReservationEntity.objects.get(id=reservation_id)
    except ReservationEntity.DoesNotExist:
        return Response({'error': 'Reservation not found.'}, status=404)

    if reservation.user_id != request.user.id:
        return Response({'error': 'Forbidden.'}, status=403)

    if reservation.checkIn < timezone.localdate():
        return Response({'error': 'This reservation can no longer be cancelled.'}, status=409)

    reservation.delete()

    return Response({'message': 'Reservation cancelled successfully.'}, status=200)
