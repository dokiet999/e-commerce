"""
Trending Products Engine.
Computes popular products based on recent behavior events.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from behavior.models import BehaviorEvent

logger = logging.getLogger(__name__)

# Weighted scoring for trending
TRENDING_WEIGHTS = {
    'checkout': 5.0,
    'add_to_cart': 3.0,
    'product_view': 1.0,
    'search': 0.5,
}


def get_trending_products(days=7, limit=10):
    """
    Get trending products based on weighted event counts
    over a recent time window.
    """
    cutoff = timezone.now() - timedelta(days=days)

    events = (
        BehaviorEvent.objects.filter(
            created_at__gte=cutoff,
            product_id__isnull=False,
            event_type__in=list(TRENDING_WEIGHTS.keys()),
        )
        .values('product_id', 'event_type')
    )

    scores = defaultdict(float)
    event_counts = defaultdict(int)

    for event in events.iterator(chunk_size=1000):
        pid = event['product_id']
        weight = TRENDING_WEIGHTS.get(event['event_type'], 0)
        scores[pid] += weight
        event_counts[pid] += 1

    if not scores:
        return []

    sorted_products = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [
        {
            'product_id': pid,
            'score': round(score, 4),
            'event_count': event_counts[pid],
            'reason': 'trending',
        }
        for pid, score in sorted_products
    ]
