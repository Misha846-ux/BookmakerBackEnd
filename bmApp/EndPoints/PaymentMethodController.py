from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from ..models import PaymentMethodEntity
from ..serializers import PaymentMethodSerializer


@api_view(['POST'])
def createPaymentMethod(request):
    serializer = PaymentMethodSerializer(data=request.data)
    
    if serializer.is_valid():
        payment_method = serializer.save()

        return Response(PaymentMethodSerializer(payment_method).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET'])
def getPaymentMethod(request, payment_method_id):
    try:
        payment_method = PaymentMethodEntity.objects.get(id=payment_method_id)
    except PaymentMethodEntity.DoesNotExist:
        return Response({'error': 'Payment method not found.'}, status=404)
    serializer = PaymentMethodSerializer(payment_method)

    return Response(serializer.data, status=200)


@api_view(['GET'])
def getPaymentMethods(request):
    try:
        el = int(request.query_params.get('el', 10))
        page = int(request.query_params.get('page', 1))
    except (ValueError, TypeError):
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)
    if el < 1 or page < 1:
        return Response({'error': 'Parameters el and page must be positive integers.'}, status=400)

    payment_methods = PaymentMethodEntity.objects.all().order_by('id')
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
