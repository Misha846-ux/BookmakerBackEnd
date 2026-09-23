from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import IntegrityError, transaction
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import secrets
from ..models import ReservationEntity, RoomEntity, UserEntity
from ..serializers import ReservationSerializer


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