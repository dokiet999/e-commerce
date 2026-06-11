"""
Collaborative Filtering Engine.
Uses item-item co-occurrence from BehaviorEvent data.
"""

import logging
from collections import defaultdict

from django.db.models import Q

from behavior.models import BehaviorEvent
from .models import ProductCoOccurrence

logger = logging.getLogger(__name__)

# Event weights for co-occurrence scoring
EVENT_WEIGHTS = {
    'checkout': 5.0,
    'add_to_cart': 3.0,
    'product_view': 1.0,
    'remove_from_cart': -1.0,
}

RELEVANT_EVENTS = ['product_view', 'add_to_cart', 'remove_from_cart', 'checkout']


def get_also_bought(product_id, limit=8):
    """
    Get products frequently co-occurring with the given product.
    Uses precomputed co-occurrence data.
    """
    co_occurring = list(
        ProductCoOccurrence.objects.filter(
            product_a_id=product_id,
            co_occurrence_count__gt=0,
        )
        .order_by('-co_occurrence_count')
        .values_list('product_b_id', 'co_occurrence_count')[:limit]
    )

    if not co_occurring:
        # Fallback: compute on-the-fly from recent events
        return _compute_also_bought_live(product_id, limit)

    return [
        {'product_id': pid, 'score': round(score, 4), 'reason': 'also_bought'}
        for pid, score in co_occurring
    ]


def _compute_also_bought_live(product_id, limit=8):
    """Compute co-occurrence on-the-fly from BehaviorEvent data."""
    # Find users/sessions that interacted with this product
    events_with_product = BehaviorEvent.objects.filter(
        product_id=product_id,
        event_type__in=RELEVANT_EVENTS,
    ).values_list('user_id', 'session_id')

    user_ids = set()
    session_ids = set()
    for uid, sid in events_with_product:
        if uid:
            user_ids.add(uid)
        elif sid:
            session_ids.add(sid)

    if not user_ids and not session_ids:
        return []

    # Find other products these users/sessions interacted with
    q = Q()
    if user_ids:
        q |= Q(user_id__in=list(user_ids)[:100])
    if session_ids:
        q |= Q(session_id__in=list(session_ids)[:100])

    other_events = (
        BehaviorEvent.objects.filter(q, event_type__in=RELEVANT_EVENTS)
        .exclude(product_id=product_id)
        .exclude(product_id__isnull=True)
    )

    # Aggregate scores
    scores = defaultdict(float)
    for event in other_events.values('product_id', 'event_type')[:5000]:
        pid = event['product_id']
        weight = EVENT_WEIGHTS.get(event['event_type'], 0)
        scores[pid] += weight

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        {'product_id': pid, 'score': round(score, 4), 'reason': 'also_bought'}
        for pid, score in sorted_scores
        if score > 0
    ]


def get_user_collaborative(user_id=None, session_id=None, limit=10):
    """
    Get recommendations for a user based on collaborative filtering.
    Finds products that similar users interacted with.
    """
    if not user_id and not session_id:
        return []

    # Get products user interacted with
    user_filter = Q(user_id=user_id) if user_id else Q(session_id=session_id)
    user_products = set(
        BehaviorEvent.objects.filter(user_filter, event_type__in=RELEVANT_EVENTS)
        .exclude(product_id__isnull=True)
        .values_list('product_id', flat=True)
        .distinct()
    )

    if not user_products:
        return []

    # For each product the user interacted with, get co-occurring products
    scores = defaultdict(float)
    for pid in list(user_products)[:20]:
        co_items = ProductCoOccurrence.objects.filter(
            product_a_id=pid,
            co_occurrence_count__gt=0,
        ).values_list('product_b_id', 'co_occurrence_count')[:10]

        for co_pid, co_score in co_items:
            if co_pid not in user_products:
                scores[co_pid] += co_score

    # If no precomputed data, try live computation
    if not scores:
        for pid in list(user_products)[:5]:
            live_recs = _compute_also_bought_live(pid, limit=5)
            for rec in live_recs:
                if rec['product_id'] not in user_products:
                    scores[rec['product_id']] += rec['score']

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        {'product_id': pid, 'score': round(score, 4), 'reason': 'collaborative'}
        for pid, score in sorted_scores
    ]


def build_co_occurrence_matrix():
    """
    Build the item-item co-occurrence matrix from BehaviorEvent data.
    Groups events by user/session and computes weighted pair scores.
    Should be run periodically via management command.
    """
    logger.info("Building co-occurrence matrix...")

    # Group events by user
    user_sessions = defaultdict(list)

    events = (
        BehaviorEvent.objects.filter(
            event_type__in=RELEVANT_EVENTS,
            product_id__isnull=False,
        )
        .values('user_id', 'session_id', 'product_id', 'event_type')
        .order_by('created_at')
    )

    for event in events.iterator(chunk_size=1000):
        key = event['user_id'] or event['session_id']
        if key:
            user_sessions[key].append(event)

    # Compute co-occurrence pairs
    pair_scores = defaultdict(float)

    for key, events_list in user_sessions.items():
        # Get unique products with their best event weight
        product_weights = defaultdict(float)
        for evt in events_list:
            pid = evt['product_id']
            weight = EVENT_WEIGHTS.get(evt['event_type'], 0)
            product_weights[pid] = max(product_weights[pid], weight)

        # Create weighted pairs
        products = list(product_weights.keys())
        for i, p1 in enumerate(products):
            for p2 in products[i + 1:]:
                combined_weight = (product_weights[p1] + product_weights[p2]) / 2
                if combined_weight > 0:
                    pair_scores[(p1, p2)] += combined_weight
                    pair_scores[(p2, p1)] += combined_weight

    # Bulk upsert to database
    count = 0
    for (p1, p2), score in pair_scores.items():
        if score > 0:
            ProductCoOccurrence.objects.update_or_create(
                product_a_id=p1,
                product_b_id=p2,
                defaults={'co_occurrence_count': score},
            )
            count += 1

    logger.info(f"Built {count} co-occurrence pairs from {len(user_sessions)} user sessions")
    return count
