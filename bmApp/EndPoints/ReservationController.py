from rest_framework.response import Response
from rest_framework.decorators import api_view
from ..serializers import ReservationSerializer


@api_view(['POST'])
def createReservation(request):
    serializer = ReservationSerializer(data=request.data)

    if serializer.is_valid():
        reservation = serializer.save()

        return Response(
            ReservationSerializer(reservation).data,
            status=201
        )

    return Response(
        serializer.errors,
        status=400
    )