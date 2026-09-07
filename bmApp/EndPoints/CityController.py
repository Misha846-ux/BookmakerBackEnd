from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import CityEntity
from ..serializers import CitySerializer


@api_view(['GET'])
def getCities(request):
    cities = CityEntity.objects.all()

    serializer = CitySerializer(
        cities,
        many=True,
    )

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
def getCity(request, city_id):
    try:
        city = CityEntity.objects.get(id=city_id)
    except CityEntity.DoesNotExist:
        return Response(
            {'error': 'City not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CitySerializer(city)

    return Response(
        serializer.data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def createCity(request):
    serializer = CitySerializer(
        data=request.data,
    )

    if serializer.is_valid():
        city = serializer.save()

        return Response(
            CitySerializer(city).data,
            status=status.HTTP_201_CREATED,
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(['PUT', 'PATCH'])
def updateCity(request, city_id):
    try:
        city = CityEntity.objects.get(id=city_id)
    except CityEntity.DoesNotExist:
        return Response(
            {'error': 'City not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CitySerializer(
        city,
        data=request.data,
        partial=request.method == 'PATCH',
    )

    if serializer.is_valid():
        city = serializer.save()

        return Response(
            CitySerializer(city).data,
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST,)


@api_view(['DELETE'])
def deleteCity(request, city_id):
    try:
        city = CityEntity.objects.get(id=city_id)
    except CityEntity.DoesNotExist:
        return Response(
            {'error': 'City not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    city.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )