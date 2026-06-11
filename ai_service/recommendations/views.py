import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from shared.rbac import get_user_id
from .engine import get_personalized_recommendations, get_cart_recommendations
from .content_based import get_similar_products
from .collaborative import get_also_bought
from .trending import get_trending_products

logger = logging.getLogger(__name__)


def _get_identity(request):
    """Extract user_id from JWT and session_id from header."""
    user_id = get_user_id(request)
    session_id = (
        request.headers.get('X-Session-Id')
        or request.META.get('HTTP_X_USER_SESSION_ID')
    )
    return user_id, session_id


@api_view(['GET'])
def personalized(request):
    """Get personalized recommendations for the current user."""
    user_id, session_id = _get_identity(request)
    limit = min(int(request.GET.get('limit', 12)), 50)

    try:
        recs = get_personalized_recommendations(
            user_id=user_id, session_id=session_id, limit=limit
        )
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'personalized',
        })
    except Exception as e:
        logger.error(f"Personalized recommendations failed: {e}")
        # Fallback to trending
        recs = get_trending_products(days=7, limit=limit)
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'trending_fallback',
        })


@api_view(['GET'])
def similar(request, product_id):
    """Get products similar to the given product."""
    limit = min(int(request.GET.get('limit', 8)), 50)

    try:
        recs = get_similar_products(product_id, limit=limit)
        # Enrich with product details
        from .engine import _enrich_recommendations
        recs = _enrich_recommendations(recs, limit)
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'similar',
        })
    except Exception as e:
        logger.error(f"Similar products failed for {product_id}: {e}")
        return Response({
            'recommendations': [],
            'count': 0,
            'recommendation_type': 'similar',
        })


@api_view(['GET'])
def also_bought(request, product_id):
    """Get products frequently bought together with the given product."""
    limit = min(int(request.GET.get('limit', 8)), 50)

    try:
        recs = get_also_bought(product_id, limit=limit)
        from .engine import _enrich_recommendations
        recs = _enrich_recommendations(recs, limit)
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'also_bought',
        })
    except Exception as e:
        logger.error(f"Also bought failed for {product_id}: {e}")
        return Response({
            'recommendations': [],
            'count': 0,
            'recommendation_type': 'also_bought',
        })


@api_view(['GET'])
def trending(request):
    """Get trending products."""
    limit = min(int(request.GET.get('limit', 10)), 50)
    days = min(int(request.GET.get('days', 7)), 30)

    try:
        recs = get_trending_products(days=days, limit=limit)
        from .engine import _enrich_recommendations
        recs = _enrich_recommendations(recs, limit)
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'trending',
        })
    except Exception as e:
        logger.error(f"Trending recommendations failed: {e}")
        return Response({
            'recommendations': [],
            'count': 0,
            'recommendation_type': 'trending',
        })


@api_view(['GET'])
def cart_recommendations(request):
    """Get recommendations based on cart contents."""
    user_id, session_id = _get_identity(request)
    limit = min(int(request.GET.get('limit', 6)), 50)

    # Get cart product IDs from query params
    product_ids_str = request.GET.get('product_ids', '')
    cart_product_ids = []
    if product_ids_str:
        try:
            cart_product_ids = [int(x) for x in product_ids_str.split(',') if x.strip()]
        except (ValueError, TypeError):
            pass

    try:
        recs = get_cart_recommendations(
            cart_product_ids=cart_product_ids,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'cart',
        })
    except Exception as e:
        logger.error(f"Cart recommendations failed: {e}")
        return Response({
            'recommendations': [],
            'count': 0,
            'recommendation_type': 'cart',
        })


@api_view(['GET'])
def rec_health(request):
    return Response({'status': 'ok', 'service': 'recommendations'})


@api_view(['POST'])
def next_product(request):
    """Predict the next products from a sequence of behavior events."""
    events = request.data.get('events') or []
    top_k = request.data.get('top_k', 5)

    if not isinstance(events, list) or not events:
        return Response(
            {'error': 'events must be a non-empty list'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from ml.next_product_inference import (
            NextProductModelNotFound,
            predict_next_products,
        )
        result = predict_next_products(events, top_k=top_k)
        return Response(result)
    except NextProductModelNotFound as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except (TypeError, ValueError) as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Next-product prediction failed: {e}")
        return Response(
            {'error': 'Next-product prediction failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def search_recommendations(request):
    """Get AI-powered product recommendations based on search query.
    Uses ChromaDB semantic search + behavior profile + trending."""
    user_id, session_id = _get_identity(request)
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', None)
    limit = min(int(request.GET.get('limit', 8)), 50)

    if not query and not category_id:
        return Response({
            'recommendations': [],
            'count': 0,
            'recommendation_type': 'search',
        })

    try:
        from .engine import get_search_recommendations
        recs = get_search_recommendations(
            query=query,
            category_id=category_id,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'search',
            'query': query,
        })
    except Exception as e:
        logger.error(f"Search recommendations failed: {e}")
        # Fallback to trending
        recs = get_trending_products(days=7, limit=limit)
        from .engine import _enrich_recommendations
        recs = _enrich_recommendations(recs, limit)
        return Response({
            'recommendations': recs,
            'count': len(recs),
            'recommendation_type': 'trending_fallback',
        })
