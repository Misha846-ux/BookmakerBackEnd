# for endpoints that work with reviews
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import HotelEntity, ReviewEntity
from ..serializers import ReviewSerializer


@api_view(['GET'])
def getHotelReviews(request, hotel_id):
	if not HotelEntity.objects.filter(id=hotel_id).exists():
		return Response({'error': 'Hotel not found'}, status=404)

	reviews = ReviewEntity.objects.filter(hotel_id=hotel_id).order_by('-createdAt')
	return Response({
		'count': reviews.count(),
		'results': ReviewSerializer(reviews, many=True).data,
	}, status=200)