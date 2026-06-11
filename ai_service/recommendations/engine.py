"""
Hybrid Recommendation Engine.
Orchestrates content-based, collaborative, and trending engines
with ML behavior predictions to produce final recommendations.
"""

import logging
from collections import defaultdict

import requests
from django.conf import settings

from behavior.models import BehaviorEvent, UserBehaviorProfile
from .collaborative import get_user_collaborative, get_also_bought
from .content_based import get_similar_products
from .trending import get_trending_products

logger = logging.getLogger(__name__)

# Default blending weights
BASE_WEIGHTS = {
    'collaborative': 0.40,
    'content':       0.30,
    'ml':            0.20,
    'trending':      0.10,
}

# ── Logged-in users: full 4-method blend, intent-adaptive ──────────────────
# Collaborative và ML chỉ có ý nghĩa khi có lịch sử dài hạn (user_id).
# Intent-adaptive: mỗi trạng thái mua sắm ưu tiên tín hiệu khác nhau.
INTENT_WEIGHTS = {
    # Sắp mua → tin vào co-purchase signal nhất
    'buying': {
        'collaborative': 0.50,
        'content':       0.20,
        'ml':            0.20,
        'trending':      0.10,
    },
    # Đang so sánh → cần thấy sản phẩm tương tự để cân nhắc
    'comparing': {
        'collaborative': 0.20,
        'content':       0.50,
        'ml':            0.20,
        'trending':      0.10,
    },
    # Đang lướt, khám phá → cân bằng, trending nhiều hơn
    'browsing': {
        'collaborative': 0.30,
        'content':       0.30,
        'ml':            0.20,
        'trending':      0.20,
    },
    # Có xu hướng trả hàng → gợi ý sản phẩm mới/hot, tránh lặp lại
    'returning': {
        'collaborative': 0.20,
        'content':       0.20,
        'ml':            0.20,
        'trending':      0.40,
    },
}

# ── Anonymous users: chỉ content + trending ─────────────────────────────────
# Collaborative: session quá ngắn, co-occurrence thưa → không đáng tin
# ML profile:    sparse data, prediction kém → bỏ qua
# Content:       ChromaDB semantic chỉ cần 1 sản phẩm đang xem → vẫn dùng được
# Trending:      tín hiệu global, luôn có dữ liệu → filler chính
ANONYMOUS_WEIGHTS = {
    'collaborative': 0.00,
    'content':       0.55,
    'ml':            0.00,
    'trending':      0.45,
}

# purchase_likelihood multiplier: high-intent users get a stronger ranking boost
PURCHASE_MULTIPLIER_RANGE = (1.0, 1.5)


def _normalize_scores(recs):
    """Min-max normalize a list of {'product_id', 'score', ...} dicts to [0, 1].
    This ensures each method contributes equally before weight blending,
    eliminating bias from methods that share the same underlying data.
    """
    if not recs:
        return recs
    values = [r['score'] for r in recs]
    lo, hi = min(values), max(values)
    if hi == lo:
        for r in recs:
            r['score'] = 1.0
        return recs
    for r in recs:
        r['score'] = (r['score'] - lo) / (hi - lo)
    return recs


def _fetch_product_details(product_ids):
    """Fetch product details from product_service for a list of IDs."""
    if not product_ids:
        return {}

    products = {}
    try:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for p in resp.json():
                if p['id'] in product_ids and p.get('is_active', True):
                    products[p['id']] = p
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch product details: {e}")

    return products


def _enrich_recommendations(recommendations, max_items=None):
    """Add product details to recommendation results."""
    if max_items:
        recommendations = recommendations[:max_items]

    product_ids = {r['product_id'] for r in recommendations}
    product_details = _fetch_product_details(product_ids)

    enriched = []
    for rec in recommendations:
        pid = rec['product_id']
        product = product_details.get(pid)
        if product:
            rec['product'] = {
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'image_url': product.get('image_url'),
                'category_name': product.get('category_name', ''),
                'stock': product.get('stock', 0),
            }
            enriched.append(rec)

    return enriched


def _get_user_profile(user_id=None, session_id=None):
    """Load UserBehaviorProfile in a single DB query.
    Returns the profile (with intent, purchase_likelihood, preferred_categories) or None.
    """
    if user_id:
        profile = UserBehaviorProfile.objects.filter(user_id=user_id).first()
        if profile:
            return profile
    if session_id:
        return UserBehaviorProfile.objects.filter(session_id=session_id).first()
    return None


def _has_behavior_data(user_id=None, session_id=None):
    """Quick existence check — avoids running heavy methods on cold-start users."""
    from django.db.models import Q
    if not user_id and not session_id:
        return False
    q = Q(user_id=user_id) if user_id else Q(session_id=session_id)
    return BehaviorEvent.objects.filter(q).exists()


def _get_user_viewed_products(user_id=None, session_id=None, limit=10):
    """Get recently viewed product IDs for a user."""
    from django.db.models import Q

    q = Q()
    if user_id:
        q = Q(user_id=user_id)
    elif session_id:
        q = Q(session_id=session_id)
    else:
        return []

    return list(
        BehaviorEvent.objects.filter(
            q,
            event_type='product_view',
            product_id__isnull=False,
        )
        .order_by('-created_at')
        .values_list('product_id', flat=True)
        .distinct()[:limit]
    )


def _blend_scores(scores, method_recs, weight, reason_tag):
    """Normalize a method's results then accumulate into the shared scores dict."""
    for rec in _normalize_scores(method_recs):
        pid = rec['product_id']
        scores[pid]['score'] += rec['score'] * weight
        if reason_tag not in scores[pid]['reasons']:
            scores[pid]['reasons'].append(reason_tag)


def get_personalized_recommendations(user_id=None, session_id=None, limit=12):
    """
    Generate personalized recommendations using a 2-tier hybrid approach:

    Tier 1 — Auth state:
      • Logged-in  (user_id)   → full 4-method blend with intent-adaptive weights
      • Anonymous  (session_id) → content + trending only (skip collaborative & ML)

    Tier 2 — Intent (logged-in only):
      Weights shift based on UserBehaviorProfile.predicted_intent so the blend
      matches the user's current shopping mindset (buying/comparing/browsing/returning).

    Additional:
      • Scores are min-max normalized per method before blending to eliminate
        double-counting bias (all 4 methods share BehaviorEvent as data source).
      • purchase_likelihood is applied as a final ×1.0–1.5 multiplier so
        high-intent users see their best matches ranked higher.
      • Cold-start fast path: no behavior data → trending only.
    """
    # ── Fully anonymous, no identifier at all ────────────────────────────────
    if not user_id and not session_id:
        recs = get_trending_products(days=7, limit=limit)
        return _enrich_recommendations(recs, limit)

    # ── Cold-start: identifier exists but no events yet ──────────────────────
    if not _has_behavior_data(user_id, session_id):
        recs = get_trending_products(days=7, limit=limit)
        return _enrich_recommendations(recs, limit)

    scores = defaultdict(lambda: {'score': 0.0, 'reasons': []})
    viewed = _get_user_viewed_products(user_id, session_id, limit=5)

    if user_id:
        # ════════════════════════════════════════════════════════════════════
        # LOGGED-IN PATH — collaborative + content + ML + trending
        # Weights are intent-adaptive; fall back to BASE_WEIGHTS if no profile.
        # ════════════════════════════════════════════════════════════════════
        profile = _get_user_profile(user_id=user_id)
        intent = profile.predicted_intent if profile else None
        purchase_likelihood = profile.purchase_likelihood if profile else None
        category_prefs = (profile.preferred_categories or {}) if profile else {}

        w = INTENT_WEIGHTS.get(intent, BASE_WEIGHTS)

        # 1. Collaborative filtering
        _blend_scores(
            scores,
            get_user_collaborative(user_id=user_id, limit=limit * 2),
            w['collaborative'],
            'collaborative',
        )

        # 2. Content-based (seed: recently viewed)
        content_recs_raw = []
        for pid in viewed[:3]:
            content_recs_raw.extend(get_similar_products(pid, limit=5))
        _blend_scores(scores, content_recs_raw, w['content'], 'similar')

        # 3. ML category preference boost
        if category_prefs and w['ml'] > 0:
            try:
                resp = requests.get(
                    f"{settings.PRODUCT_SERVICE_URL}/api/products/", timeout=10
                )
                if resp.status_code == 200:
                    total = sum(float(v) for v in category_prefs.values()) or 1.0
                    ml_recs_raw = [
                        {'product_id': p['id'],
                         'score': float(category_prefs[str(p.get('category', ''))]) / total}
                        for p in resp.json()
                        if str(p.get('category', '')) in category_prefs
                    ]
                    _blend_scores(scores, ml_recs_raw, w['ml'], 'ml_preference')
            except requests.RequestException:
                pass

        # 4. Trending as filler
        _blend_scores(
            scores,
            get_trending_products(days=7, limit=limit * 2),
            w['trending'],
            'trending',
        )

        # purchase_likelihood final multiplier (×1.0 – ×1.5)
        if purchase_likelihood is not None and purchase_likelihood > 0:
            lo, hi = PURCHASE_MULTIPLIER_RANGE
            multiplier = lo + (hi - lo) * float(purchase_likelihood)
            for data in scores.values():
                data['score'] *= multiplier

    else:
        # ════════════════════════════════════════════════════════════════════
        # ANONYMOUS PATH — content + trending only
        # Collaborative skipped: session co-occurrence quá thưa
        # ML skipped:            session profile sparse, prediction không tin cậy
        # ════════════════════════════════════════════════════════════════════
        w = ANONYMOUS_WEIGHTS

        # Content-based (seed: sản phẩm xem trong session hiện tại)
        content_recs_raw = []
        for pid in viewed[:3]:
            content_recs_raw.extend(get_similar_products(pid, limit=5))
        _blend_scores(scores, content_recs_raw, w['content'], 'similar')

        # Trending
        _blend_scores(
            scores,
            get_trending_products(days=7, limit=limit * 2),
            w['trending'],
            'trending',
        )

    # ── Final ranking ────────────────────────────────────────────────────────
    viewed_set = set(viewed)
    final_scores = {
        pid: data for pid, data in scores.items()
        if pid not in viewed_set and data['score'] > 0
    }
    sorted_recs = sorted(final_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    recommendations = [
        {
            'product_id': pid,
            'score': round(data['score'], 4),
            'reason': data['reasons'][0] if data['reasons'] else 'recommended',
        }
        for pid, data in sorted_recs
    ]
    return _enrich_recommendations(recommendations, limit)


def get_search_recommendations(query='', category_id=None, user_id=None, session_id=None, limit=8):
    """
    AI-powered search recommendations.
    Uses ChromaDB semantic search + user behavior profile to find
    the most relevant products for a search query.
    """
    scores = defaultdict(lambda: {'score': 0, 'reasons': []})

    # 1. ChromaDB semantic search (primary)
    if query:
        try:
            from kb.vector_store import get_collection
            collection = get_collection()
            results = collection.query(
                query_texts=[query],
                n_results=min(limit * 2, 20),
                where={'source_type': 'product'} if collection.count() > 0 else None,
            )
            if results and results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    meta = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    pid = meta.get('product_id')
                    if pid:
                        try:
                            pid = int(pid)
                        except (ValueError, TypeError):
                            continue
                        similarity = max(0, 1 - distance)
                        scores[pid]['score'] += similarity * 0.6
                        scores[pid]['reasons'].append('semantic_match')
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}")

    # 2. Category filter boost
    if category_id:
        try:
            url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for p in resp.json():
                    if str(p.get('category', '')) == str(category_id):
                        scores[p['id']]['score'] += 0.3
                        if 'category' not in scores[p['id']]['reasons']:
                            scores[p['id']]['reasons'].append('category')
        except requests.RequestException:
            pass

    # 3. User behavior boost — prefer products in categories user likes
    profile = _get_user_profile(user_id, session_id)
    category_prefs = (profile.preferred_categories or {}) if profile else {}
    if category_prefs:
        total = sum(int(v) for v in category_prefs.values()) or 1
        try:
            url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for p in resp.json():
                    cat_id = str(p.get('category', ''))
                    if cat_id in category_prefs:
                        pref_score = int(category_prefs[cat_id]) / total
                        scores[p['id']]['score'] += pref_score * 0.1
                        if 'personalized' not in scores[p['id']]['reasons']:
                            scores[p['id']]['reasons'].append('personalized')
        except requests.RequestException:
            pass

    # 4. Text match on product name/description (fallback if no ChromaDB)
    if query and not any('semantic_match' in d['reasons'] for d in scores.values()):
        try:
            url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                q_lower = query.lower()
                for p in resp.json():
                    name_match = q_lower in (p.get('name', '') or '').lower()
                    desc_match = q_lower in (p.get('description', '') or '').lower()
                    if name_match:
                        scores[p['id']]['score'] += 0.5
                        scores[p['id']]['reasons'].append('name_match')
                    elif desc_match:
                        scores[p['id']]['score'] += 0.3
                        scores[p['id']]['reasons'].append('description_match')
        except requests.RequestException:
            pass

    sorted_recs = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)

    recommendations = [
        {
            'product_id': pid,
            'score': round(data['score'], 4),
            'reason': data['reasons'][0] if data['reasons'] else 'search',
        }
        for pid, data in sorted_recs
        if data['score'] > 0
    ]

    return _enrich_recommendations(recommendations, limit)


def get_cart_recommendations(cart_product_ids=None, user_id=None, session_id=None, limit=6):
    """
    Get recommendations based on products currently in the cart.
    Combines similar products and also-bought for each cart item.
    """
    if not cart_product_ids:
        return get_trending_products(days=7, limit=limit)

    scores = defaultdict(lambda: {'score': 0, 'reasons': []})
    cart_set = set(cart_product_ids)

    for pid in cart_product_ids[:5]:
        # Similar products
        similar = get_similar_products(pid, limit=4)
        for rec in similar:
            rpid = rec['product_id']
            if rpid not in cart_set:
                scores[rpid]['score'] += rec['score'] * 0.5
                if 'similar' not in scores[rpid]['reasons']:
                    scores[rpid]['reasons'].append('similar')

        # Also bought
        also = get_also_bought(pid, limit=4)
        for rec in also:
            rpid = rec['product_id']
            if rpid not in cart_set:
                scores[rpid]['score'] += rec['score'] * 0.5
                if 'also_bought' not in scores[rpid]['reasons']:
                    scores[rpid]['reasons'].append('also_bought')

    sorted_recs = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)

    recommendations = [
        {
            'product_id': pid,
            'score': round(data['score'], 4),
            'reason': data['reasons'][0] if data['reasons'] else 'cart_suggestion',
        }
        for pid, data in sorted_recs
    ]

    return _enrich_recommendations(recommendations, limit)
