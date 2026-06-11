"""
Data pipeline: convert BehaviorEvent records into training tensors.
"""

import numpy as np

# Mapping event types to indices (0 = padding)
EVENT_TYPE_MAP = {
    'page_view': 1,
    'product_view': 2,
    'add_to_cart': 3,
    'remove_from_cart': 4,
    'search': 5,
    'category_filter': 6,
    'checkout': 7,
}

# Intent heuristic labels based on behavior patterns
INTENT_MAP = {
    'browsing': 0,
    'buying': 1,
    'comparing': 2,
    'returning': 3,
}

MAX_SEQ_LEN = 50


def events_to_features(events):
    """
    Convert a list of event dicts into model input tensors.

    Args:
        events: list of dicts with keys:
            event_type, product_id, category_id, metadata, created_at

    Returns:
        dict with numpy arrays ready for torch conversion:
            event_types, categories, numerical_features,
            seq_length, global_features
    """
    if not events:
        return _empty_features()

    # Sort by time
    events = sorted(events, key=lambda e: e.get('created_at', ''))

    # Truncate to max sequence length (keep most recent)
    if len(events) > MAX_SEQ_LEN:
        events = events[-MAX_SEQ_LEN:]

    seq_len = len(events)

    event_types = np.zeros(MAX_SEQ_LEN, dtype=np.int64)
    categories = np.zeros(MAX_SEQ_LEN, dtype=np.int64)
    numerical = np.zeros((MAX_SEQ_LEN, 3), dtype=np.float32)  # price, quantity, hour

    for i, e in enumerate(events):
        event_types[i] = EVENT_TYPE_MAP.get(e.get('event_type', ''), 0)
        cat_id = e.get('category_id') or 0
        categories[i] = min(cat_id, 9)  # Cap at embedding size

        meta = e.get('metadata', {}) or {}
        numerical[i, 0] = float(meta.get('price', 0)) / 1000.0  # Normalize
        numerical[i, 1] = float(meta.get('quantity', 0)) / 10.0
        created = e.get('created_at')
        if hasattr(created, 'hour'):
            numerical[i, 2] = created.hour / 24.0

    # Global features
    global_features = _compute_global_features(events)

    return {
        'event_types': event_types,
        'categories': categories,
        'numerical_features': numerical,
        'seq_length': seq_len,
        'global_features': global_features,
    }


def _compute_global_features(events):
    """Compute aggregated user-level features."""
    features = np.zeros(5, dtype=np.float32)

    total = len(events)
    if total == 0:
        return features

    type_counts = {}
    for e in events:
        t = e.get('event_type', '')
        type_counts[t] = type_counts.get(t, 0) + 1

    features[0] = type_counts.get('product_view', 0) / max(total, 1)
    features[1] = type_counts.get('add_to_cart', 0) / max(total, 1)
    features[2] = type_counts.get('search', 0) / max(total, 1)
    features[3] = min(total / 100.0, 1.0)  # Activity level

    # Cart conversion rate
    views = type_counts.get('product_view', 0)
    carts = type_counts.get('add_to_cart', 0)
    features[4] = carts / max(views, 1)

    return features


def assign_intent_label(events):
    """Heuristic labeling for training: determine intent from event patterns."""
    if not events:
        return INTENT_MAP['browsing']

    type_counts = {}
    for e in events:
        t = e.get('event_type', '')
        type_counts[t] = type_counts.get(t, 0) + 1

    checkouts = type_counts.get('checkout', 0)
    carts = type_counts.get('add_to_cart', 0)
    views = type_counts.get('product_view', 0)
    searches = type_counts.get('search', 0)

    if checkouts > 0 or (carts >= 2 and carts / max(views, 1) > 0.3):
        return INTENT_MAP['buying']
    elif searches > views:
        return INTENT_MAP['comparing']
    elif type_counts.get('remove_from_cart', 0) > carts:
        return INTENT_MAP['returning']
    else:
        return INTENT_MAP['browsing']


def _empty_features():
    return {
        'event_types': np.zeros(MAX_SEQ_LEN, dtype=np.int64),
        'categories': np.zeros(MAX_SEQ_LEN, dtype=np.int64),
        'numerical_features': np.zeros((MAX_SEQ_LEN, 3), dtype=np.float32),
        'seq_length': 0,
        'global_features': np.zeros(5, dtype=np.float32),
    }
