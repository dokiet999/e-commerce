/**
 * Recommendations Module — fetches and renders product recommendations.
 */
const recommendations = {

    async fetchPersonalized(limit = 12) {
        try {
            return await api.request('GET', `/api/ai/recommendations/personalized/?limit=${limit}`);
        } catch (e) {
            console.warn('Failed to fetch personalized recommendations:', e);
            return { recommendations: [] };
        }
    },

    async fetchSimilar(productId, limit = 8) {
        try {
            return await api.request('GET', `/api/ai/recommendations/similar/${productId}/?limit=${limit}`);
        } catch (e) {
            console.warn('Failed to fetch similar products:', e);
            return { recommendations: [] };
        }
    },

    async fetchAlsoBought(productId, limit = 8) {
        try {
            return await api.request('GET', `/api/ai/recommendations/also-bought/${productId}/?limit=${limit}`);
        } catch (e) {
            console.warn('Failed to fetch also-bought:', e);
            return { recommendations: [] };
        }
    },

    async fetchTrending(limit = 10) {
        try {
            return await api.request('GET', `/api/ai/recommendations/trending/?limit=${limit}`);
        } catch (e) {
            console.warn('Failed to fetch trending:', e);
            return { recommendations: [] };
        }
    },

    async fetchCartRecommendations(productIds, limit = 6) {
        try {
            const ids = productIds.join(',');
            return await api.request('GET', `/api/ai/recommendations/cart/?product_ids=${ids}&limit=${limit}`);
        } catch (e) {
            console.warn('Failed to fetch cart recommendations:', e);
            return { recommendations: [] };
        }
    },

    async fetchSearchRecommendations(query, categoryId = null, limit = 8) {
        try {
            let url = `/api/ai/recommendations/search/?q=${encodeURIComponent(query)}&limit=${limit}`;
            if (categoryId) url += `&category=${categoryId}`;
            return await api.request('GET', url);
        } catch (e) {
            console.warn('Failed to fetch search recommendations:', e);
            return { recommendations: [] };
        }
    },

    async fetchBehaviorEvents(limit = 30) {
        try {
            const data = await api.request('GET', '/api/ai/events/list/');
            return Array.isArray(data) ? data.slice(0, limit) : [];
        } catch (e) {
            console.warn('Failed to fetch behavior events:', e);
            return [];
        }
    },

    async fetchNextProducts(events, topK = 5) {
        try {
            return await api.request('POST', '/api/ai/recommendations/next-product/', {
                events,
                top_k: topK,
            });
        } catch (e) {
            console.warn('Failed to fetch next-product predictions:', e);
            return { predictions: [] };
        }
    },

    /**
     * Render a horizontal scrollable section of product cards.
     * @param {string} containerId - The DOM element ID to render into.
     * @param {Array} recs - Array of recommendation objects with .product field.
     * @param {string} title - Section title.
     * @param {string} icon - Emoji/icon for the title.
     */
    renderSection(containerId, recs, title, icon = '✨') {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!recs || recs.length === 0) {
            container.style.display = 'none';
            return;
        }

        const cards = recs
            .filter(r => r.product)
            .map(r => {
                const p = r.product;
                const imgHtml = p.image_url
                    ? `<img src="${p.image_url}" alt="${p.name}" class="rec-card-img">`
                    : `<div class="rec-card-img-placeholder">📦</div>`;
                return `
                    <a href="/product/${p.id}/" class="rec-card">
                        ${imgHtml}
                        <div class="rec-card-body">
                            <div class="rec-card-title">${p.name}</div>
                            <div class="rec-card-price">${formatPrice(p.price)}</div>
                            ${p.category_name ? `<div class="rec-card-cat">${p.category_name}</div>` : ''}
                        </div>
                    </a>
                `;
            })
            .join('');

        if (!cards) {
            container.style.display = 'none';
            return;
        }

        container.innerHTML = `
            <div class="rec-section">
                <div class="rec-section-header">
                    <h3>${icon} ${title}</h3>
                </div>
                <div class="rec-scroll-container">
                    <div class="rec-scroll">${cards}</div>
                </div>
            </div>
        `;
        container.style.display = 'block';
    },

    /**
     * Load and render personalized recommendations for the home page.
     */
    async loadHomeRecommendations() {
        const token = api.getToken();

        // Personalized — only for logged-in users or users with session
        const personalizedPromise = this.fetchPersonalized(12);
        const trendingPromise = this.fetchTrending(10);

        const [personalizedData, trendingData] = await Promise.all([
            personalizedPromise,
            trendingPromise,
        ]);

        if (token && personalizedData.recommendations.length > 0) {
            this.renderSection(
                'recPersonalized',
                personalizedData.recommendations,
                'Dành cho bạn',
                '🎯'
            );
        }

        this.renderSection(
            'recTrending',
            trendingData.recommendations,
            'Xu hướng',
            '🔥'
        );
    },

    /**
     * Load and render product detail page recommendations.
     */
    async loadProductRecommendations(productId) {
        const [similarData, alsoBoughtData] = await Promise.all([
            this.fetchSimilar(productId, 8),
            this.fetchAlsoBought(productId, 8),
        ]);

        this.renderSection(
            'recSimilar',
            similarData.recommendations,
            'Sản phẩm tương tự',
            '🔍'
        );

        this.renderSection(
            'recAlsoBought',
            alsoBoughtData.recommendations,
            'Khách hàng cũng mua',
            '🛒'
        );
    },

    /**
     * Load and render cart page recommendations.
     */
    async loadCartRecommendations(cartItems) {
        if (!cartItems || cartItems.length === 0) return;

        const productIds = cartItems.map(item => item.product_id);
        const data = await this.fetchCartRecommendations(productIds, 6);

        this.renderSection(
            'recCart',
            data.recommendations,
            'Có thể bạn cũng thích',
            '💡'
        );
    },

    /**
     * Load and render AI-powered search recommendations.
     */
    async loadSearchRecommendations(query, categoryId) {
        if (!query && !categoryId) return;

        const data = await this.fetchSearchRecommendations(query, categoryId, 8);

        this.renderSection(
            'recSearch',
            data.recommendations,
            query ? `AI gợi ý cho "${query}"` : 'AI gợi ý cho bạn',
            '🤖'
        );
    },
    /**
     * Load and render LSTM next-product recommendations on product detail pages.
     */
    async loadNextProductRecommendations(currentProduct) {
        if (!currentProduct) return;

        const events = await this.fetchBehaviorEvents(30);
        const modelEvents = this._toNextProductEvents(events, currentProduct);
        if (modelEvents.length === 0) return;

        const data = await this.fetchNextProducts(modelEvents, 5);
        const recs = await this._nextPredictionsToRecommendations(
            data.predictions || [],
            currentProduct.id
        );

        this.renderSection(
            'recNextProduct',
            recs,
            'Co the ban se xem tiep',
            'AI'
        );
    },

    _toNextProductEvents(events, currentProduct) {
        const normalized = [];
        const sourceEvents = Array.isArray(events) ? events.slice().reverse() : [];

        sourceEvents.forEach(event => {
            const productId = event.product_id || null;
            if (!productId) return;
            normalized.push({
                product_id: this._toCsvProductId(productId),
                action: this._toCsvAction(event.event_type),
                category: this._toCsvCategory(event.category_id),
                device: this._deviceType(),
                timestamp: this._toCsvTimestamp(event.created_at),
            });
        });

        normalized.push({
            product_id: this._toCsvProductId(currentProduct.id),
            action: 'view',
            category: this._toCsvCategory(currentProduct.category),
            device: this._deviceType(),
            timestamp: this._toCsvTimestamp(new Date().toISOString()),
        });

        return normalized;
    },

    async _nextPredictionsToRecommendations(predictions, currentProductId) {
        const recs = [];
        const seen = new Set([Number(currentProductId)]);

        for (const pred of predictions) {
            const productId = this._fromCsvProductId(pred.product_id);
            if (!productId || seen.has(productId)) continue;

            try {
                const product = await api.getProduct(productId);
                recs.push({
                    product,
                    score: pred.score,
                    recommendation_type: 'next_product_lstm',
                });
                seen.add(productId);
            } catch (e) {
                console.warn('Failed to hydrate predicted product:', pred.product_id, e);
            }
        }

        return recs;
    },

    _toCsvProductId(productId) {
        const value = parseInt(productId, 10);
        if (!Number.isFinite(value)) return String(productId || '');
        return `P${String(value).padStart(3, '0')}`;
    },

    _fromCsvProductId(productId) {
        const match = String(productId || '').match(/^P?0*(\d+)$/i);
        return match ? parseInt(match[1], 10) : null;
    },

    _toCsvAction(eventType) {
        const map = {
            page_view: 'view',
            product_view: 'view',
            add_to_cart: 'add_to_cart',
            remove_from_cart: 'click',
            search: 'click',
            category_filter: 'click',
            checkout: 'purchase',
        };
        return map[eventType] || 'view';
    },

    _toCsvCategory(categoryId) {
        const map = {
            1: 'electronics',
            2: 'fashion',
            3: 'food',
            4: 'books',
            5: 'sports',
            6: 'beauty',
            7: 'home',
            8: 'toys',
        };
        return map[parseInt(categoryId, 10)] || 'electronics';
    },

    _deviceType() {
        const width = window.innerWidth || 1024;
        if (width < 768) return 'mobile';
        if (width < 1024) return 'tablet';
        return 'desktop';
    },

    _toCsvTimestamp(value) {
        const date = value ? new Date(value) : new Date();
        if (Number.isNaN(date.getTime())) return '2024-01-01 00:00:00';
        return date.toISOString().slice(0, 19).replace('T', ' ');
    },
};
