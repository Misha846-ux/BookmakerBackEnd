from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.permissions import IsAuthenticated # type: ignore
from django.db import IntegrityError
from ..models import PaymentMethodEntity, DebitCardEntity
from ..serializers import PaymentMethodSerializer, DebitCardSerializer


@api_view(['POST'])
def createPaymentMethod(request):
    serializer = PaymentMethodSerializer(data=request.data)

    if serializer.is_valid():
        card_number = serializer.validated_data['cardNumber']
        existing = PaymentMethodEntity.objects.filter(cardNumber=card_number).first()
        user = getattr(request, 'user', None)
        is_authenticated = bool(user is not None and getattr(user, 'is_authenticated', False))

        if existing is not None:
            if existing.user_id is not None:
                if is_authenticated and existing.user_id == user.id:
                    return Response(PaymentMethodSerializer(existing).data, status=200)
                return Response(
                    {'cardNumber': ['A payment method with this card number already belongs to another account.']},
                    status=400,
                )

            if is_authenticated:
                existing.user = user
                existing.save(update_fields=['user'])
                if user.payMethod is None:
                    user.payMethod = existing
                    user.save(update_fields=['payMethod'])
                return Response(PaymentMethodSerializer(existing).data, status=200)

            return Response(PaymentMethodSerializer(existing).data, status=200)

        data = serializer.validated_data
        if is_authenticated:
            data['user'] = user

        try:
            payment_method = PaymentMethodEntity.objects.create(**data)
        except IntegrityError:
            return Response(
                {'cardNumber': ['A payment method with this card number already exists.']},
                status=400,
            )

        if is_authenticated and user.payMethod is None:
            user.payMethod = payment_method
            user.save(update_fields=['payMethod'])

        return Response(PaymentMethodSerializer(payment_method).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getPaymentMethod(request, payment_method_id):
    try:
        payment_method = PaymentMethodEntity.objects.get(id=payment_method_id)
    except PaymentMethodEntity.DoesNotExist:
        return Response({'error': 'Payment method not found.'}, status=404)

    if payment_method.user_id != request.user.id:
        return Response({'error': 'Forbidden.'}, status=403)

    serializer = PaymentMethodSerializer(payment_method)

    return Response(serializer.data, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getPaymentMethods(request):
    try:
        el = int(request.query_params.get('el', 10))
        page = int(request.query_params.get('page', 1))
    except (ValueError, TypeError):
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)
    if el < 1 or page < 1:
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)

    payment_methods = PaymentMethodEntity.objects.filter(user=request.user).order_by('id')
    total = payment_methods.count()
    start = (page - 1) * el
    end = start + el
    payment_methods = payment_methods[start:end]
    serializer = PaymentMethodSerializer(payment_methods, many=True)

    return Response({
        'count': total,
        'page': page,
        'el': el,
        'total_pages': (total + el - 1) // el,
        'results': serializer.data
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyPaymentMethods(request):
    payment_methods = PaymentMethodEntity.objects.filter(user=request.user).order_by('id')
    serializer = PaymentMethodSerializer(payment_methods, many=True)

    return Response(serializer.data, status=200)


@api_view(['GET'])
def getDebitCards(request):
    cards = DebitCardEntity.objects.all().order_by('id')
    serializer = DebitCardSerializer(cards, many=True)

    return Response(serializer.data, status=200)


def _own_payment_method(request, payment_method_id):
    try:
        payment_method = PaymentMethodEntity.objects.get(id=payment_method_id)
    except PaymentMethodEntity.DoesNotExist:
        return None, Response({'error': 'Payment method not found.'}, status=404)

    if payment_method.user_id != request.user.id:
        return None, Response({'error': 'Forbidden.'}, status=403)

    return payment_method, None


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updatePaymentMethod(request, payment_method_id):
    payment_method, error = _own_payment_method(request, payment_method_id)

    if error is not None:
        return error

    data = request.data
    allowed_fields = ('cardType', 'cardNumber', 'date')
    update_data = {field: data[field] for field in allowed_fields if field in data}

    if not update_data:
        return Response({'error': 'No fields to update.'}, status=400)

    serializer = PaymentMethodSerializer(payment_method, data=update_data, partial=True)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    card_number = serializer.validated_data.get('cardNumber')
    if card_number is not None:
        duplicate = (
            PaymentMethodEntity.objects
            .filter(cardNumber=card_number)
            .exclude(id=payment_method.id)
            .first()
        )
        if duplicate is not None:
            return Response(
                {'cardNumber': ['A payment method with this card number already exists.']},
                status=400,
            )

    try:
        updated = serializer.save()
    except IntegrityError:
        return Response(
            {'cardNumber': ['A payment method with this card number already exists.']},
            status=400,
        )

    return Response(PaymentMethodSerializer(updated).data, status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deletePaymentMethod(request, payment_method_id):
    payment_method, error = _own_payment_method(request, payment_method_id)

    if error is not None:
        return error

    user = request.user
    if user.payMethod_id == payment_method.id:
        user.payMethod = None
        user.save(update_fields=['payMethod'])

    payment_method.delete()

    return Response({'message': 'Payment method deleted successfully.'}, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setDefaultPaymentMethod(request, payment_method_id):
    payment_method, error = _own_payment_method(request, payment_method_id)

    if error is not None:
        return error

    user = request.user
    user.payMethod = payment_method
    user.save(update_fields=['payMethod'])

    return Response({'payMethod': payment_method.id}, status=200)
