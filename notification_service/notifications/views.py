from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import get_user_id, is_admin, is_service_request
from .serializers import (
    NotificationCreateSerializer,
    NotificationListQuerySerializer,
    NotificationUpdateSerializer,
)
from .supabase_client import (
    SupabaseAPIError,
    SupabaseNotConfigured,
    create_notification,
    delete_notification,
    get_notification,
    list_notifications,
    mark_all_read,
    update_notification,
)


def _supabase_error_response(exc):
    if isinstance(exc, SupabaseNotConfigured):
        return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, SupabaseAPIError):
        return Response(
            {'error': str(exc), 'detail': exc.payload},
            status=exc.status_code or status.HTTP_502_BAD_GATEWAY,
        )
    return Response(
        {'error': 'Notification storage unavailable'},
        status=status.HTTP_502_BAD_GATEWAY,
    )


def _can_access_notification(request, notification):
    user_id = get_user_id(request)
    return (
        is_admin(request)
        or is_service_request(request)
        or (user_id and int(notification.get('user_id')) == int(user_id))
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def notification_list(request):
    if request.method == 'GET':
        user_id = get_user_id(request)
        if not user_id and not is_admin(request):
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        query = NotificationListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        requested_user_id = request.query_params.get('user_id')
        if is_admin(request) and requested_user_id:
            user_id = requested_user_id

        try:
            notifications = list_notifications(
                user_id=user_id,
                unread_only=query.validated_data['unread_only'],
                limit=query.validated_data['limit'],
            )
        except Exception as exc:
            return _supabase_error_response(exc)

        return Response(notifications)

    if not (is_service_request(request) or is_admin(request)):
        return Response({'error': 'Service or admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = NotificationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    payload = dict(serializer.validated_data)
    payload.setdefault('metadata', {})

    try:
        notification = create_notification(payload)
    except Exception as exc:
        return _supabase_error_response(exc)

    return Response(notification, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def notification_detail(request, notification_id):
    try:
        notification = get_notification(notification_id)
    except Exception as exc:
        return _supabase_error_response(exc)

    if not notification:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    if not _can_access_notification(request, notification):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(notification)

    if request.method == 'DELETE':
        try:
            delete_notification(notification_id)
        except Exception as exc:
            return _supabase_error_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = NotificationUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        updated = update_notification(notification_id, serializer.validated_data)
    except Exception as exc:
        return _supabase_error_response(exc)
    return Response(updated)


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_read(request, notification_id):
    try:
        notification = get_notification(notification_id)
    except Exception as exc:
        return _supabase_error_response(exc)

    if not notification:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    if not _can_access_notification(request, notification):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    try:
        updated = update_notification(
            notification_id,
            {'read_at': timezone.now().isoformat()},
        )
    except Exception as exc:
        return _supabase_error_response(exc)
    return Response(updated)


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_all_read_view(request):
    user_id = get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        updated = mark_all_read(user_id, timezone.now().isoformat())
    except Exception as exc:
        return _supabase_error_response(exc)
    return Response({'updated': len(updated), 'notifications': updated})


@api_view(['GET'])
@permission_classes([AllowAny])
def unread_count(request):
    user_id = get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        notifications = list_notifications(user_id=user_id, unread_only=True, limit=100)
    except Exception as exc:
        return _supabase_error_response(exc)
    return Response({'unread_count': len(notifications)})


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'notification_service'})
