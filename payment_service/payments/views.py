import os
import uuid
import requests as http_requests
from decimal import Decimal
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import get_user_id, is_admin
from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentSerializer, RefundSerializer


def _get_user_id(request):
    return get_user_id(request)


def _update_order_status(order_id, new_status, request):
    try:
        headers = {}
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            headers['Authorization'] = auth
        headers['X-Service-Token'] = os.environ.get('SERVICE_AUTH_TOKEN', 'change-me-service-token')
        headers['X-Service-Name'] = 'payment_service'
        http_requests.put(
            f"{settings.ORDER_SERVICE_URL}/api/orders/{order_id}/status/",
            json={'status': new_status},
            headers=headers, timeout=10,
        )
    except http_requests.RequestException:
        pass


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_list(request):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        payments = Payment.objects.filter(user_id=user_id)
        return Response(PaymentSerializer(payments, many=True).data)

    serializer = CreatePaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payment = Payment.objects.create(
        order_id=serializer.validated_data['order_id'],
        user_id=user_id,
        amount=serializer.validated_data['amount'],
        currency=serializer.validated_data.get('currency', 'USD'),
        method=serializer.validated_data['method'],
        status='processing',
        transaction_id=str(uuid.uuid4()),
        payment_details=serializer.validated_data.get('payment_details', {}),
    )

    # Simulate payment processing — mark as completed
    payment.status = 'completed'
    payment.save()

    _update_order_status(payment.order_id, 'confirmed', request)

    return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_detail(request, payment_id):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

    if payment.user_id != user_id and not is_admin(request):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    return Response(PaymentSerializer(payment).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def refund_payment(request, payment_id):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

    if payment.user_id != user_id and not is_admin(request):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    if payment.status not in ('completed',):
        return Response({'error': 'Can only refund completed payments'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = RefundSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    refund_amount = serializer.validated_data.get('amount', payment.amount)
    if refund_amount > payment.amount:
        return Response({'error': 'Refund amount exceeds payment amount'}, status=status.HTTP_400_BAD_REQUEST)

    if refund_amount == payment.amount:
        payment.status = 'refunded'
    else:
        payment.status = 'partially_refunded'
    payment.save()

    _update_order_status(payment.order_id, 'refunded', request)

    return Response(PaymentSerializer(payment).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'payment_service'})
