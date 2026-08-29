# for andPoints that working with rooms
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..serializers import RoomSerializer


@api_view(['POST'])
def createRoom(request):

    serializer = RoomSerializer(data=request.data)

    if serializer.is_valid():
        room = serializer.save()

        return Response(
            RoomSerializer(room).data,
            status=201
        )

    return Response(
        serializer.errors,
        status=400
    )