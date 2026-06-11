"""
Generate synthetic behavior data for initial model training.

Usage:
    python manage.py seed_behavior_data
    python manage.py seed_behavior_data --users 50 --events-per-user 30
"""

import os
import sys
import random
from datetime import timedelta

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_config.settings')
django.setup()

from django.utils import timezone
from behavior.models import BehaviorEvent


EVENT_TYPES = [
    'page_view', 'product_view', 'add_to_cart',
    'remove_from_cart', 'search', 'category_filter', 'checkout',
]

# Weighted distribution: browsing-heavy users, buyers, etc.
USER_PROFILES = [
    {
        'name': 'browser',
        'weights': [0.3, 0.4, 0.05, 0.02, 0.15, 0.08, 0.0],
        'intent': 'browsing',
    },
    {
        'name': 'buyer',
        'weights': [0.1, 0.25, 0.3, 0.05, 0.1, 0.05, 0.15],
        'intent': 'buying',
    },
    {
        'name': 'comparer',
        'weights': [0.15, 0.3, 0.1, 0.05, 0.25, 0.15, 0.0],
        'intent': 'comparing',
    },
    {
        'name': 'returner',
        'weights': [0.1, 0.15, 0.15, 0.35, 0.1, 0.05, 0.1],
        'intent': 'returning',
    },
]

SEARCH_QUERIES = [
    'laptop gaming', 'tai nghe bluetooth', 'áo thun nam',
    'giày chạy bộ', 'sách hay', 'đồ chơi trẻ em',
    'điện thoại samsung', 'bàn phím cơ', 'quần jean',
    'máy tính bảng', 'đồng hồ thông minh', 'balo du lịch',
]


def seed(num_users=30, events_per_user=25):
    """Generate synthetic behavior events."""
    print(f"Generating data for {num_users} users, ~{events_per_user} events each...")

    BehaviorEvent.objects.all().delete()
    created = 0
    now = timezone.now()

    for user_idx in range(num_users):
        profile = random.choice(USER_PROFILES)
        is_authenticated = random.random() > 0.3  # 70% authenticated

        user_id = user_idx + 1 if is_authenticated else None
        session_id = f"session_{user_idx}_{random.randint(1000,9999)}" if not is_authenticated else None

        num_events = random.randint(
            max(5, events_per_user - 10),
            events_per_user + 10,
        )

        # Random start time in the past 30 days
        start_time = now - timedelta(days=random.randint(1, 30))

        for event_idx in range(num_events):
            event_type = random.choices(EVENT_TYPES, weights=profile['weights'])[0]

            product_id = random.randint(1, 20) if event_type in [
                'product_view', 'add_to_cart', 'remove_from_cart',
            ] else None

            category_id = random.randint(1, 6) if event_type in [
                'product_view', 'category_filter', 'add_to_cart',
            ] else None

            search_query = random.choice(SEARCH_QUERIES) if event_type == 'search' else None

            metadata = {}
            if product_id:
                metadata['price'] = round(random.uniform(10, 500), 2)
            if event_type in ['add_to_cart', 'remove_from_cart']:
                metadata['quantity'] = random.randint(1, 5)

            event_time = start_time + timedelta(
                minutes=event_idx * random.randint(1, 30),
            )

            BehaviorEvent.objects.create(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                product_id=product_id,
                category_id=category_id,
                search_query=search_query,
                metadata=metadata,
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                user_agent='Mozilla/5.0 (Synthetic Data Generator)',
            )
            # Manually set created_at since auto_now_add
            BehaviorEvent.objects.filter(
                user_id=user_id, session_id=session_id,
            ).order_by('-created_at').first()

            created += 1

    print(f"Created {created} behavior events")
    return created


if __name__ == '__main__':
    seed()
