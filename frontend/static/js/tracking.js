/**
 * Behavior Tracking Module — sends user events to AI service
 * Uses fetch with keepalive (supports Authorization header).
 * Falls back to sendBeacon for guests on page unload.
 */
const tracker = {
    _send(eventType, data = {}) {
        const payload = {
            event_type: eventType,
            ...data,
        };
        const url = `${API_URL}/api/ai/events/`;
        const token = localStorage.getItem('access_token');

        // Use fetch so we can attach the Authorization header
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
            credentials: 'include',
            keepalive: true,
        }).catch(() => {
            // Last-resort fallback (no auth header possible)
            if (navigator.sendBeacon) {
                const blob = new Blob(
                    [JSON.stringify(payload)],
                    { type: 'application/json' }
                );
                navigator.sendBeacon(url, blob);
            }
        });
    },

    trackPageView(page) {
        this._send('page_view', { metadata: { page } });
    },

    trackProductView(productId, categoryId, price) {
        this._send('product_view', {
            product_id: productId,
            category_id: categoryId || null,
            metadata: { price: price || null },
        });
    },

    trackAddToCart(productId, quantity, price) {
        this._send('add_to_cart', {
            product_id: productId,
            metadata: { quantity, price: price || null },
        });
    },

    trackRemoveFromCart(productId) {
        this._send('remove_from_cart', {
            product_id: productId,
        });
    },

    trackSearch(query, categoryId) {
        this._send('search', {
            search_query: query,
            category_id: categoryId || null,
        });
    },

    trackCategoryFilter(categoryId) {
        this._send('category_filter', {
            category_id: categoryId,
        });
    },
};
