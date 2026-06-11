import uuid
from django.http import JsonResponse
from django.conf import settings
from shared.jwt_utils import decode_jwt
from shared.rbac import is_service_request


class SessionIdMiddleware:
    """Create/forward session_id cookie for guest (unauthenticated) users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_id = request.COOKIES.get('session_id')
        request._gateway_session_id = session_id
        request._new_session = False

        response = self.get_response(request)

        # If guest (no JWT) and no session_id cookie, set one
        if not getattr(request, '_gateway_user_id', None) and not session_id:
            new_session_id = uuid.uuid4().hex
            response.set_cookie(
                'session_id',
                new_session_id,
                max_age=30 * 24 * 3600,  # 30 days
                httponly=True,
                samesite='Lax',
            )
            request._gateway_session_id = new_session_id
            request._new_session = True

        return response


class JWTAuthMiddleware:
    """Decode JWT and enforce auth on protected routes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._gateway_user_id = None
        request._gateway_role = None
        request._gateway_is_admin = False
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = decode_jwt(token)
            if payload:
                request._gateway_user_id = payload.get('user_id')
                request._gateway_role = payload.get('role') or (
                    'admin' if payload.get('is_staff') or payload.get('is_superuser') else 'user'
                )
                request._gateway_is_admin = (
                    request._gateway_role == 'admin'
                    or bool(payload.get('is_staff'))
                    or bool(payload.get('is_superuser'))
                )

        if self._is_public(request):
            return self.get_response(request)

        if self._is_service_only(request):
            if is_service_request(request):
                return self.get_response(request)
            return JsonResponse({'error': 'Service access required'}, status=403)

        if self._is_admin_or_service(request):
            if is_service_request(request) or request._gateway_is_admin:
                return self.get_response(request)
            if not request._gateway_user_id:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return JsonResponse({'error': 'Admin access required'}, status=403)

        if self._is_admin_only(request):
            if request._gateway_is_admin:
                return self.get_response(request)
            if not request._gateway_user_id:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return JsonResponse({'error': 'Admin access required'}, status=403)

        if not request._gateway_user_id and not self._allows_guest_session(request):
            return JsonResponse({'error': 'Authentication required'}, status=401)

        return self.get_response(request)

    def _is_public(self, request):
        method = request.method
        path = request.path

        for pub_method, pub_path in settings.PUBLIC_PATHS:
            if method == pub_method:
                if self._matches(path, pub_path):
                    return True
        return False

    def _matches(self, path, rule_path):
        if rule_path.endswith('*'):
            return path.startswith(rule_path[:-1])
        return path == rule_path

    def _allows_guest_session(self, request):
        if not request._gateway_session_id:
            return False
        return request.path.startswith('/api/cart/') or request.path.startswith('/api/ai/')

    def _is_service_only(self, request):
        method = request.method
        path = request.path
        return (
            (method == 'POST' and path == '/api/notifications/')
            or (method == 'POST' and path in {
                '/api/inventory/reserve/',
                '/api/inventory/release/',
                '/api/inventory/deduct/',
                '/api/shipping/',
            })
        )

    def _is_admin_or_service(self, request):
        return (
            request.method == 'PUT'
            and request.path.startswith('/api/orders/')
            and request.path.endswith('/status/')
        )

    def _is_admin_only(self, request):
        method = request.method
        path = request.path

        if path.startswith('/api/products/') and method in {'POST', 'PUT', 'DELETE'}:
            return True
        if path == '/api/coupons/' and method == 'POST':
            return True
        if path.startswith('/api/coupons/') and method == 'PUT':
            return True
        if path in {'/api/inventory/restock/', '/api/inventory/low-stock/'}:
            return True
        if method == 'PUT' and path.startswith('/api/shipping/') and path.endswith('/status/'):
            return True
        return False
