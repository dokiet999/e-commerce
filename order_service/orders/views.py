import requests as http_requests
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import get_user_id, is_admin, is_service_request
from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer, UpdateStatusSerializer


def _get_user_id(request):
    return get_user_id(request)


def _fetch_cart(user_id, request):
    try:
        headers = {}
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            headers['Authorization'] = auth
        headers['X-User-Id'] = str(user_id)
        resp = http_requests.get(
            f"{settings.CART_SERVICE_URL}/api/cart/",
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except http_requests.RequestException:
        pass
    return None


def _fetch_product(product_id):
    try:
        resp = http_requests.get(
            f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/",
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
    except http_requests.RequestException:
        pass
    return None


def _clear_cart(user_id, request):
    try:
        headers = {}
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            headers['Authorization'] = auth
        headers['X-User-Id'] = str(user_id)
        http_requests.delete(
            f"{settings.CART_SERVICE_URL}/api/cart/clear/",
            headers=headers, timeout=10,
        )
    except http_requests.RequestException:
        pass


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def order_list(request):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        orders = Order.objects.filter(user_id=user_id).prefetch_related('items')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    # POST — create order from cart
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    cart = _fetch_cart(user_id, request)
    if not cart or not cart.get('items'):
        return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        order = Order.objects.create(
            user_id=user_id,
            shipping_address=serializer.validated_data['shipping_address'],
            billing_address=serializer.validated_data.get('billing_address', ''),
            notes=serializer.validated_data.get('notes', ''),
            status='pending',
        )

        total = Decimal('0')
        for item in cart['items']:
            product = _fetch_product(item['product_id'])
            product_name = product['name'] if product else f"Product #{item['product_id']}"
            unit_price = Decimal(str(item.get('price_at_add', '0')))
            qty = item['quantity']
            subtotal = unit_price * qty

            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                product_name=product_name,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            total += subtotal

        order.total_amount = total
        order.save()

    _clear_cart(user_id, request)

    return Response(
        OrderSerializer(Order.objects.prefetch_related('items').get(pk=order.pk)).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def order_detail(request, order_id):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        order = Order.objects.prefetch_related('items').get(pk=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    if order.user_id != user_id and not is_admin(request):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    return Response(OrderSerializer(order).data)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_status(request, order_id):
    if not is_admin(request) and not is_service_request(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    order.status = serializer.validated_data['status']
    order.save()
    return Response(OrderSerializer(Order.objects.prefetch_related('items').get(pk=order.pk)).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_order(request, order_id):
    user_id = _get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    if order.user_id != user_id and not is_admin(request):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    if order.status not in ('pending', 'confirmed'):
        return Response(
            {'error': f'Cannot cancel order with status: {order.status}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status = 'cancelled'
    order.save()
    return Response(OrderSerializer(Order.objects.prefetch_related('items').get(pk=order.pk)).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'order_service'})
