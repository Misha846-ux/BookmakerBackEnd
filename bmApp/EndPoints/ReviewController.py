# for endpoints that work with reviews
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import HotelEntity, ReviewEntity
from ..functions.UserFunctions import user_photo_url
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

@api_view(['GET'])
def getLatestReviews(request):
    reviews = ReviewEntity.objects.select_related(
        'user',
        'hotel',
    ).order_by('-createdAt')[:3]

    return Response({
        'results': [
            {
                'id': review.id,
                'review': review.review,
                'createdAt': review.createdAt,
                'rating': review.rating,
                'user': {
                    'id': review.user.id,
                    'name': review.user.name,
                    'photo': user_photo_url(request, review.user.photo),
                },
                'hotel': {
                    'id': review.hotel.id,
                    'name': review.hotel.name,
                },
            }
            for review in reviews
        ]
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyReviews(request):
    reviews = ReviewEntity.objects.filter(user=request.user).select_related(
        'hotel',
        'hotel__city',
        'hotel__city__country',
    ).order_by('-createdAt')

    return Response({
        'count': reviews.count(),
        'results': [
            {
                'id': review.id,
                'review': review.review,
                'createdAt': review.createdAt,
                'rating': review.rating,
                'hotel': {
                    'id': review.hotel.id,
                    'name': review.hotel.name,
                    'stars': review.hotel.stars,
                    'city': review.hotel.city.name if review.hotel.city else None,
                    'country': (
                        review.hotel.city.country.name
                        if review.hotel.city and review.hotel.city.country
                        else None
                    ),
                },
            }
            for review in reviews
        ],
    }, status=200)
