import os
import jwt


JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-jwt-key-change-in-production')
JWT_ALGORITHM = 'HS256'


def decode_jwt(token):
    """Decode and verify a JWT token. Returns payload dict or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_token(token):
    """Extract user_id from JWT token."""
    payload = decode_jwt(token)
    if payload:
        return payload.get('user_id')
    return None


def get_token_from_header(request_meta):
    """Extract token from Authorization header (Bearer <token>)."""
    auth_header = request_meta.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None
