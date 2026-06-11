import os
import requests as http_requests
from django.conf import settings
from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import get_user_id, is_admin
from .models import Review
from .serializers import ReviewSerializer, CreateReviewSerializer


def _get_user_id(request):
    return get_user_id(request)


def _check_verified_purchase(user_id, product_id):
    try:
        resp = http_requests.get(
            f"{settings.ORDER_SERVICE_URL}/api/orders/",
            headers={
                'X-User-Id': str(user_id),
                'X-Service-Token': os.environ.get('SERVICE_AUTH_TOKEN', 'change-me-service-token'),
                'X-Service-Name': 'review_service',
            },
            timeout=5,
        )
        if resp.status_code == 200:
            for order in resp.json():
                for item in order.get('items', []):
                    if item.get('product_id') == product_id:
                        return True
    except http_requests.RequestException:
        pass
    return False


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def review_list(request):
    if request.method == 'GET':
        reviews = Review.objects.filter(is_approved=True)
        return Response(ReviewSerializer(reviews, many=True).data)

    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = CreateReviewSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    product_id = serializer.validated_data['product_id']

    if Review.objects.filter(product_id=product_id, user_id=user_id).exists():
        return Response({'error': 'You already reviewed this product'}, status=status.HTTP_400_BAD_REQUEST)

    is_verified = _check_verified_purchase(user_id, product_id)

    review = Review.objects.create(
        product_id=product_id,
        user_id=user_id,
        rating=serializer.validated_data['rating'],
        title=serializer.validated_data.get('title', ''),
        comment=serializer.validated_data.get('comment', ''),
        is_verified_purchase=is_verified,
    )

    return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def review_detail(request, review_id):
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ReviewSerializer(review).data)

    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    if review.user_id != user_id and not is_admin(request):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT
    if 'rating' in request.data:
        review.rating = request.data['rating']
    if 'title' in request.data:
        review.title = request.data['title']
    if 'comment' in request.data:
        review.comment = request.data['comment']
    review.save()
    return Response(ReviewSerializer(review).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_reviews(request, product_id):
    reviews = Review.objects.filter(product_id=product_id, is_approved=True)
    return Response(ReviewSerializer(reviews, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_review_summary(request, product_id):
    reviews = Review.objects.filter(product_id=product_id, is_approved=True)
    agg = reviews.aggregate(avg_rating=Avg('rating'), total_reviews=Count('id'))
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[str(i)] = reviews.filter(rating=i).count()
    return Response({
        'product_id': product_id,
        'average_rating': round(agg['avg_rating'] or 0, 1),
        'total_reviews': agg['total_reviews'],
        'rating_distribution': rating_dist,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'review_service'})
