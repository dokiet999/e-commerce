import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR.parent))

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-jwt-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'corsheaders',
    'proxy',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'proxy.middleware.SessionIdMiddleware',
    'proxy.middleware.JWTAuthMiddleware',
]

ROOT_URLCONF = 'gateway.urls'

WSGI_APPLICATION = 'gateway.wsgi.application'

# No database needed for the gateway
DATABASES = {}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Service URLs — fallback if registry is unavailable
SERVICE_URLS = {
    'auth_service': os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8001'),
    'product_service': os.environ.get('PRODUCT_SERVICE_URL', 'http://localhost:8002'),
    'cart_service': os.environ.get('CART_SERVICE_URL', 'http://localhost:8003'),
    'ai_service': os.environ.get('AI_SERVICE_URL', 'http://localhost:8004'),
    'order_service': os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8005'),
    'payment_service': os.environ.get('PAYMENT_SERVICE_URL', 'http://localhost:8006'),
    'inventory_service': os.environ.get('INVENTORY_SERVICE_URL', 'http://localhost:8007'),
    'notification_service': os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:8008'),
    'review_service': os.environ.get('REVIEW_SERVICE_URL', 'http://localhost:8009'),
    'shipping_service': os.environ.get('SHIPPING_SERVICE_URL', 'http://localhost:8010'),
    'coupon_service': os.environ.get('COUPON_SERVICE_URL', 'http://localhost:8011'),
}

# Service Registry
SERVICE_NAME = 'api_gateway'
SERVICE_HOST = os.environ.get('GATEWAY_HOST', 'localhost')
SERVICE_PORT = int(os.environ.get('GATEWAY_PORT', 8000))

# Routes: prefix → service name
ROUTE_MAP = {
    'auth': 'auth_service',
    'products': 'product_service',
    'cart': 'cart_service',
    'ai': 'ai_service',
    'orders': 'order_service',
    'payments': 'payment_service',
    'inventory': 'inventory_service',
    'notifications': 'notification_service',
    'reviews': 'review_service',
    'shipping': 'shipping_service',
    'coupons': 'coupon_service',
}

# Paths that do NOT require JWT authentication. Rules ending with * are prefix matches.
PUBLIC_PATHS = [
    ('POST', '/api/auth/register/'),
    ('POST', '/api/auth/login/'),
    ('POST', '/api/auth/refresh/'),
    ('GET', '/api/auth/health/'),
    ('GET', '/api/products/*'),
    ('GET', '/api/cart/'),
    ('POST', '/api/cart/items/'),
    ('GET', '/api/cart/health/'),
    ('POST', '/api/ai/events/'),
    ('GET', '/api/ai/health/'),
    ('POST', '/api/ai/chat/'),
    ('GET', '/api/ai/chat/history/'),
    ('GET', '/api/ai/recommendations/*'),
    ('GET', '/api/orders/health/'),
    ('GET', '/api/payments/health/'),
    ('GET', '/api/inventory/health/'),
    ('GET', '/api/notifications/health/'),
    ('GET', '/api/reviews/*'),
    ('GET', '/api/shipping/methods/'),
    ('POST', '/api/shipping/calculate/'),
    ('GET', '/api/shipping/health/'),
    ('GET', '/api/coupons/*'),
    ('POST', '/api/coupons/validate/'),
    ('GET', '/api/coupons/health/'),
]
