import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SupabaseNotConfigured(RuntimeError):
    pass


class SupabaseAPIError(RuntimeError):
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _base_url():
    if not settings.SUPABASE_URL:
        raise SupabaseNotConfigured('SUPABASE_URL is not configured')
    return f"{settings.SUPABASE_URL}/rest/v1/{settings.SUPABASE_NOTIFICATIONS_TABLE}"


def _headers(prefer=None):
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    if not key:
        raise SupabaseNotConfigured(
            'SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is not configured'
        )

    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    return headers


def _handle_response(resp):
    if 200 <= resp.status_code < 300:
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    try:
        payload = resp.json()
    except ValueError:
        payload = {'detail': resp.text}
    raise SupabaseAPIError(
        'Supabase API request failed',
        status_code=resp.status_code,
        payload=payload,
    )


def create_notification(data):
    resp = requests.post(
        _base_url(),
        json=data,
        headers=_headers(prefer='return=representation'),
        timeout=10,
    )
    rows = _handle_response(resp) or []
    return rows[0] if rows else None


def list_notifications(user_id, unread_only=False, limit=50):
    params = {
        'user_id': f'eq.{user_id}',
        'order': 'created_at.desc',
        'limit': str(limit),
    }
    if unread_only:
        params['read_at'] = 'is.null'

    resp = requests.get(
        _base_url(),
        params=params,
        headers=_headers(),
        timeout=10,
    )
    return _handle_response(resp) or []


def get_notification(notification_id):
    resp = requests.get(
        _base_url(),
        params={'id': f'eq.{notification_id}', 'limit': '1'},
        headers=_headers(),
        timeout=10,
    )
    rows = _handle_response(resp) or []
    return rows[0] if rows else None


def update_notification(notification_id, data):
    resp = requests.patch(
        _base_url(),
        params={'id': f'eq.{notification_id}'},
        json=data,
        headers=_headers(prefer='return=representation'),
        timeout=10,
    )
    rows = _handle_response(resp) or []
    return rows[0] if rows else None


def mark_all_read(user_id, read_at):
    resp = requests.patch(
        _base_url(),
        params={'user_id': f'eq.{user_id}', 'read_at': 'is.null'},
        json={'read_at': read_at},
        headers=_headers(prefer='return=representation'),
        timeout=10,
    )
    return _handle_response(resp) or []


def delete_notification(notification_id):
    resp = requests.delete(
        _base_url(),
        params={'id': f'eq.{notification_id}'},
        headers=_headers(),
        timeout=10,
    )
    _handle_response(resp)
    return True
