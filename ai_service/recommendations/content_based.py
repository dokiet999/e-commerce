"""
Content-Based Filtering Engine.
Finds similar products using ChromaDB semantic similarity + category/price matching.
"""

import logging

import requests
from django.conf import settings

from .models import ProductSimilarity

logger = logging.getLogger(__name__)

# Cache for product data
_product_cache = {}


def _fetch_product(product_id):
    """Fetch a single product from the product service."""
    if product_id in _product_cache:
        return _product_cache[product_id]
    try:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            product = resp.json()
            _product_cache[product_id] = product
            return product
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch product {product_id}: {e}")
    return None


def _fetch_all_products():
    """Fetch all active products from the product service."""
    try:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            products = resp.json()
            for p in products:
                _product_cache[p['id']] = p
            return products
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch products: {e}")
    return []


def get_similar_products(product_id, limit=8):
    """
    Find similar products using:
    1. Precomputed similarity (if available)
    2. ChromaDB semantic search (fallback)
    3. Category + price heuristic (fallback)
    """
    # Try precomputed similarities first
    precomputed = list(
        ProductSimilarity.objects.filter(product_a_id=product_id)
        .order_by('-similarity_score')
        .values_list('product_b_id', 'similarity_score')[:limit]
    )
    if precomputed:
        return [
            {'product_id': pid, 'score': round(score, 4), 'reason': 'similar'}
            for pid, score in precomputed
        ]

    # Fallback: live computation
    return _compute_similar_live(product_id, limit)


def _compute_similar_live(product_id, limit=8):
    """Compute similarity on-the-fly using ChromaDB + heuristics."""
    target = _fetch_product(product_id)
    if not target:
        return []

    results = {}

    # 1. Semantic similarity via ChromaDB
    try:
        from kb.vector_store import get_vectorstore
        vs = get_vectorstore()
        query_text = f"{target.get('name', '')} {target.get('description', '')}"
        docs = vs.similarity_search_with_score(
            query_text,
            k=limit * 2,
            filter={'source_type': 'product'},
        )
        for doc, score in docs:
            pid = doc.metadata.get('product_id')
            if pid and int(pid) != product_id:
                # ChromaDB distance → similarity (lower distance = more similar)
                similarity = max(0, 1 - score)
                results[int(pid)] = results.get(int(pid), 0) + similarity * 0.6
    except Exception as e:
        logger.warning(f"ChromaDB similarity search failed: {e}")

    # 2. Category + price heuristic
    all_products = _fetch_all_products()
    target_category = target.get('category')
    target_price = float(target.get('price', 0))

    for p in all_products:
        pid = p['id']
        if pid == product_id:
            continue

        score = 0
        # Same category bonus
        if p.get('category') == target_category and target_category:
            score += 0.3

        # Price proximity (within 30%)
        p_price = float(p.get('price', 0))
        if target_price > 0 and p_price > 0:
            ratio = min(target_price, p_price) / max(target_price, p_price)
            if ratio > 0.7:
                score += 0.1 * ratio

        if score > 0:
            results[pid] = results.get(pid, 0) + score

    # Sort and return top N
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        {'product_id': pid, 'score': round(score, 4), 'reason': 'similar'}
        for pid, score in sorted_results
    ]


def build_similarity_matrix():
    """
    Precompute product similarity pairs and store in DB.
    Should be run periodically via management command.
    """
    products = _fetch_all_products()
    if not products:
        logger.warning("No products found to build similarity matrix")
        return 0

    count = 0
    for i, p1 in enumerate(products):
        scores = {}
        p1_id = p1['id']
        p1_cat = p1.get('category')
        p1_price = float(p1.get('price', 0))

        # Category + price heuristic for all pairs
        for p2 in products:
            p2_id = p2['id']
            if p2_id == p1_id:
                continue

            score = 0
            if p2.get('category') == p1_cat and p1_cat:
                score += 0.3

            p2_price = float(p2.get('price', 0))
            if p1_price > 0 and p2_price > 0:
                ratio = min(p1_price, p2_price) / max(p1_price, p2_price)
                if ratio > 0.7:
                    score += 0.1 * ratio

            if score > 0:
                scores[p2_id] = score

        # Semantic similarity via ChromaDB
        try:
            from kb.vector_store import get_vectorstore
            vs = get_vectorstore()
            query = f"{p1.get('name', '')} {p1.get('description', '')}"
            docs = vs.similarity_search_with_score(
                query, k=20, filter={'source_type': 'product'}
            )
            for doc, dist in docs:
                pid = doc.metadata.get('product_id')
                if pid and int(pid) != p1_id:
                    similarity = max(0, 1 - dist)
                    scores[int(pid)] = scores.get(int(pid), 0) + similarity * 0.6
        except Exception as e:
            logger.warning(f"ChromaDB search failed for product {p1_id}: {e}")

        # Save top similarities
        for p2_id, score in scores.items():
            if score > 0.05:
                ProductSimilarity.objects.update_or_create(
                    product_a_id=p1_id,
                    product_b_id=p2_id,
                    similarity_type='hybrid',
                    defaults={'similarity_score': score},
                )
                count += 1

    logger.info(f"Built {count} similarity pairs for {len(products)} products")
    return count


def clear_product_cache():
    """Clear the in-memory product cache."""
    global _product_cache
    _product_cache = {}
