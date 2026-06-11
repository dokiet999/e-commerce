import os
from dataclasses import dataclass

from .jwt_utils import decode_jwt, get_token_from_header


SERVICE_AUTH_TOKEN = os.environ.get('SERVICE_AUTH_TOKEN', 'change-me-service-token')


@dataclass(frozen=True)
class AuthContext:
    user_id: int | None = None
    role: str | None = None
    is_staff: bool = False
    is_superuser: bool = False
    is_service: bool = False
    service_name: str | None = None

    @property
    def is_authenticated(self):
        return self.user_id is not None

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_staff or self.is_superuser


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _role_from_payload(payload):
    if payload.get('role'):
        return payload.get('role')
    if payload.get('is_staff') or payload.get('is_superuser'):
        return 'admin'
    return 'user'


def is_service_request(request):
    token = request.META.get('HTTP_X_SERVICE_TOKEN') or request.headers.get('X-Service-Token')
    return bool(SERVICE_AUTH_TOKEN and token == SERVICE_AUTH_TOKEN)


def get_auth_context(request):
    token = get_token_from_header(request.META)
    if token:
        payload = decode_jwt(token)
        if payload:
            return AuthContext(
                user_id=_to_int(payload.get('user_id')),
                role=_role_from_payload(payload),
                is_staff=bool(payload.get('is_staff', False)),
                is_superuser=bool(payload.get('is_superuser', False)),
                is_service=is_service_request(request),
                service_name=request.META.get('HTTP_X_SERVICE_NAME'),
            )

    if is_service_request(request):
        return AuthContext(
            user_id=_to_int(request.META.get('HTTP_X_USER_ID') or request.headers.get('X-User-Id')),
            role='service',
            is_service=True,
            service_name=request.META.get('HTTP_X_SERVICE_NAME'),
        )

    return AuthContext()


def get_user_id(request):
    return get_auth_context(request).user_id


def get_role(request):
    return get_auth_context(request).role


def is_authenticated(request):
    return get_auth_context(request).is_authenticated


def is_admin(request):
    return get_auth_context(request).is_admin
