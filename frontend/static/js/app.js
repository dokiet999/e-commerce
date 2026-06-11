/**
 * Global app initialization — runs on every page
 */
document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI();
    updateCartBadge();
    loadCategories();
});

// Toast notification
function showToast(message, type = '') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Load categories into nav
async function loadCategories() {
    try {
        const categories = await api.getCategories();
        const nav = document.getElementById('categoryNav');
        if (!nav) return;
        categories.forEach(cat => {
            const li = document.createElement('li');
            li.innerHTML = `<a href="/?category=${cat.id}" class="cat-link" data-cat="${cat.id}">${cat.name}</a>`;
            nav.appendChild(li);
        });
        // Highlight active
        const params = new URLSearchParams(window.location.search);
        const activeCat = params.get('category') || '';
        nav.querySelectorAll('.cat-link').forEach(link => {
            link.classList.toggle('active', link.dataset.cat === activeCat);
        });
    } catch (e) {}
}

// Search
function searchProducts() {
    const q = document.getElementById('searchInput').value.trim();
    const cat = document.getElementById('searchCategory').value;
    if (q) tracker.trackSearch(q, cat || null);
    if (cat && !q) tracker.trackCategoryFilter(parseInt(cat));
    let url = '/?';
    if (q) url += `q=${encodeURIComponent(q)}&`;
    if (cat) url += `category=${cat}&`;
    window.location.href = url;
}

// Price formatter
function formatPrice(price) {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
}
