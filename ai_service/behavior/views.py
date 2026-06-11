import logging

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from shared.rbac import get_user_id
from .models import BehaviorEvent, UserBehaviorProfile
from .serializers import (
    BehaviorEventCreateSerializer,
    BehaviorEventSerializer,
    UserBehaviorProfileSerializer,
)

logger = logging.getLogger(__name__)


def _get_user_and_session(request):
    """Extract user_id from JWT and session_id from header."""
    user_id = get_user_id(request)
    session_id = (
        request.headers.get('X-Session-Id')
        or request.META.get('HTTP_X_USER_SESSION_ID')
    )
    return user_id, session_id


@api_view(['POST'])
def record_event(request):
    """Record a behavior event. Public — uses JWT or session_id."""
    user_id, session_id = _get_user_and_session(request)

    if not user_id and not session_id:
        return Response(
            {'error': 'Authentication or session required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = BehaviorEventCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    event = serializer.save(
        user_id=user_id,
        session_id=session_id,
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    # Update profile asynchronously (inline for simplicity)
    _update_profile(user_id, session_id)
    _sync_event_to_neo4j(event)

    return Response(
        BehaviorEventSerializer(event).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
def get_events(request):
    """Get behavior events for current user."""
    user_id, session_id = _get_user_and_session(request)

    if not user_id and not session_id:
        return Response(
            {'error': 'Authentication or session required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    events = BehaviorEvent.objects.all()
    if user_id:
        events = events.filter(user_id=user_id)
    else:
        events = events.filter(session_id=session_id)

    events = events[:100]  # Limit
    return Response(BehaviorEventSerializer(events, many=True).data)


@api_view(['GET'])
def get_profile(request):
    """Get behavior profile for current user."""
    user_id, session_id = _get_user_and_session(request)

    if not user_id and not session_id:
        return Response(
            {'error': 'Authentication or session required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = None
    if user_id:
        profile = UserBehaviorProfile.objects.filter(user_id=user_id).first()
    if not profile and session_id:
        profile = UserBehaviorProfile.objects.filter(session_id=session_id).first()

    if not profile:
        # Generate on-the-fly
        _update_profile(user_id, session_id)
        if user_id:
            profile = UserBehaviorProfile.objects.filter(user_id=user_id).first()
        elif session_id:
            profile = UserBehaviorProfile.objects.filter(session_id=session_id).first()

    if not profile:
        return Response(
            {'error': 'No behavior data found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(UserBehaviorProfileSerializer(profile).data)


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok', 'service': 'ai_service'})


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _sync_event_to_neo4j(event):
    """Best-effort projection; tracking must not fail when Neo4j is unavailable."""
    try:
        from kb.neo4j_store import index_behavior_event

        index_behavior_event(event)
    except Exception as exc:
        logger.warning("Skipping Neo4j behavior sync for event %s: %s", event.id, exc)


def _update_profile(user_id, session_id):
    """Update or create behavior profile from aggregated events."""
    if not user_id and not session_id:
        return

    events = BehaviorEvent.objects.all()
    if user_id:
        events = events.filter(user_id=user_id)
    else:
        events = events.filter(session_id=session_id)

    if not events.exists():
        return

    total_views = events.filter(
        event_type__in=['page_view', 'product_view']
    ).count()
    total_cart = events.filter(
        event_type__in=['add_to_cart', 'remove_from_cart']
    ).count()
    total_searches = events.filter(event_type='search').count()

    # Category preferences
    cat_events = (
        events.filter(category_id__isnull=False)
        .values('category_id')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    preferred_categories = {
        str(e['category_id']): e['count'] for e in cat_events
    }

    # Activity pattern (hour distribution)
    hour_dist = {}
    for e in events.values_list('created_at', flat=True)[:500]:
        h = str(e.hour)
        hour_dist[h] = hour_dist.get(h, 0) + 1

    lookup = {}
    if user_id:
        lookup['user_id'] = user_id
    else:
        lookup['session_id'] = session_id

    UserBehaviorProfile.objects.update_or_create(
        **lookup,
        defaults={
            'total_views': total_views,
            'total_cart_actions': total_cart,
            'total_searches': total_searches,
            'preferred_categories': preferred_categories,
            'activity_pattern': {'hour_distribution': hour_dist},
        },
    )
