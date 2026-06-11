/**
 * Auth state management
 */
function isLoggedIn() {
    return !!localStorage.getItem('access_token');
}

function getUserInfo() {
    const raw = localStorage.getItem('user_info');
    return raw ? JSON.parse(raw) : null;
}

function setUserInfo(info) {
    localStorage.setItem('user_info', JSON.stringify(info));
}

async function handleLogin(email, password) {
    const data = await api.login(email, password);
    api.setTokens(data.access, data.refresh);
    // Fetch profile
    try {
        const profile = await api.getProfile();
        setUserInfo(profile);
    } catch (e) {}
    // Merge guest cart
    try { await api.mergeCart(); } catch (e) {}
    return data;
}

function logout() {
    api.clearTokens();
    window.location.href = '/';
}

function updateAuthUI() {
    const loggedIn = isLoggedIn();
    const user = getUserInfo();

    const greeting = document.getElementById('topGreeting');
    const profileLink = document.getElementById('topProfileLink');
    const logoutLink = document.getElementById('topLogoutLink');
    const signInLink = document.getElementById('topSignInLink');
    const registerLink = document.getElementById('topRegisterLink');

    if (loggedIn && user) {
        if (greeting) greeting.textContent = `Hi, ${user.username || user.email}!`;
        if (profileLink) profileLink.style.display = '';
        if (logoutLink) logoutLink.style.display = '';
        if (signInLink) signInLink.style.display = 'none';
        if (registerLink) registerLink.style.display = 'none';
    } else {
        if (greeting) greeting.textContent = '';
        if (profileLink) profileLink.style.display = 'none';
        if (logoutLink) logoutLink.style.display = 'none';
        if (signInLink) signInLink.style.display = '';
        if (registerLink) registerLink.style.display = '';
    }
}

async function updateCartBadge() {
    try {
        const cart = await api.getCart();
        const badge = document.getElementById('cartBadge');
        const items = cart.items || [];
        const count = items.reduce((sum, item) => sum + item.quantity, 0);
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        }
    } catch (e) {}
}
