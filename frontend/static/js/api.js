/**
 * API Client — communicates with the API Gateway
 */
const api = {
    getToken() {
        return localStorage.getItem('access_token');
    },
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },
    setTokens(access, refresh) {
        localStorage.setItem('access_token', access);
        if (refresh) localStorage.setItem('refresh_token', refresh);
    },
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
    },

    async request(method, path, data = null, requireAuth = false) {
        const headers = { 'Content-Type': 'application/json' };
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const opts = { method, headers, credentials: 'include' };
        if (data && method !== 'GET') {
            opts.body = JSON.stringify(data);
        }

        let resp = await fetch(`${API_URL}${path}`, opts);

        // If 401 and we have a refresh token, try refreshing
        if (resp.status === 401 && this.getRefreshToken()) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${this.getToken()}`;
                opts.headers = headers;
                resp = await fetch(`${API_URL}${path}`, opts);
            }
        }

        if (resp.status === 204) return null;

        const json = await resp.json();
        if (!resp.ok) {
            throw { status: resp.status, data: json };
        }
        return json;
    },

    async refreshAccessToken() {
        try {
            const resp = await fetch(`${API_URL}/api/auth/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: this.getRefreshToken() }),
            });
            if (resp.ok) {
                const data = await resp.json();
                this.setTokens(data.access, null);
                return true;
            }
        } catch (e) {}
        this.clearTokens();
        return false;
    },

    // Auth
    register(userData) { return this.request('POST', '/api/auth/register/', userData); },
    login(email, password) { return this.request('POST', '/api/auth/login/', { email, password }); },
    getProfile() { return this.request('GET', '/api/auth/profile/', null, true); },

    // Products
    getProducts() { return this.request('GET', '/api/products/'); },
    getProduct(id) { return this.request('GET', `/api/products/${id}/`); },
    getCategories() { return this.request('GET', '/api/products/categories/'); },

    // Cart
    getCart() { return this.request('GET', '/api/cart/'); },
    addToCart(productId, quantity = 1) { return this.request('POST', '/api/cart/items/', { product_id: productId, quantity }); },
    updateCartItem(itemId, quantity) { return this.request('PUT', `/api/cart/items/${itemId}/`, { quantity }); },
    removeCartItem(itemId) { return this.request('DELETE', `/api/cart/items/${itemId}/remove/`); },
    clearCart() { return this.request('DELETE', '/api/cart/clear/'); },
    mergeCart() { return this.request('POST', '/api/cart/merge/'); },

    // AI Consultation
    sendChatMessage(message, chatSessionId = null) {
        const data = { message };
        if (chatSessionId) data.chat_session_id = chatSessionId;
        return this.request('POST', '/api/ai/chat/', data);
    },
    getChatHistory(chatSessionId) {
        const qs = chatSessionId ? `?chat_session_id=${chatSessionId}` : '';
        return this.request('GET', `/api/ai/chat/history/${qs}`);
    },
    clearChat(chatSessionId) {
        const qs = chatSessionId ? `?chat_session_id=${chatSessionId}` : '';
        return this.request('DELETE', `/api/ai/chat/clear/${qs}`);
    },

    // Reviews
    getProductReviews(productId) { return this.request('GET', `/api/reviews/product/${productId}/`); },
    getProductReviewSummary(productId) { return this.request('GET', `/api/reviews/product/${productId}/summary/`); },
    createReview(data) { return this.request('POST', '/api/reviews/', data); },
    deleteReview(reviewId) { return this.request('DELETE', `/api/reviews/${reviewId}/`); },
};
