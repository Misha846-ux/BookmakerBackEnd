from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from ..serializers import PaymentMethodSerializer


@api_view(['POST'])
def createPaymentMethod(request):
    serializer = PaymentMethodSerializer(data=request.data)
    
    if serializer.is_valid():
        payment_method = serializer.save()

        return Response(PaymentMethodSerializer(payment_method).data, status=201)
    return Response(serializer.errors, status=400)
