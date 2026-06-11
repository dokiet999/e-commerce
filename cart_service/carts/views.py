import requests as http_requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.jwt_utils import get_token_from_header, get_user_id_from_token
from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
)


def _get_cart_identity(request):
    """Return (user_id, session_id) from request headers."""
    token = get_token_from_header(request.META)
    user_id = get_user_id_from_token(token) if token else None
    session_id = request.META.get('HTTP_X_SESSION_ID')
    return user_id, session_id


def _get_or_create_cart(user_id, session_id):
    """Get or create a cart for user or guest session."""
    if user_id:
        cart, _ = Cart.objects.get_or_create(user_id=user_id, defaults={'session_id': None})
        return cart
    if session_id:
        cart, _ = Cart.objects.get_or_create(session_id=session_id, user_id=None)
        return cart
    return None


def _get_cart(user_id, session_id):
    """Get existing cart for user or guest session."""
    if user_id:
        return Cart.objects.filter(user_id=user_id).first()
    if session_id:
        return Cart.objects.filter(session_id=session_id, user_id__isnull=True).first()
    return None


def _fetch_product(product_id):
    """Fetch product info from Product Service."""
    try:
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/"
        resp = http_requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except http_requests.RequestException:
        pass
    return None


@api_view(['GET'])
@permission_classes([AllowAny])
def cart_detail(request):
    user_id, session_id = _get_cart_identity(request)
    if not user_id and not session_id:
        return Response({'items': [], 'total': 0})

    cart = _get_cart(user_id, session_id)
    if not cart:
        return Response({'items': [], 'total': 0})

    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_item(request):
    user_id, session_id = _get_cart_identity(request)
    if not user_id and not session_id:
        return Response(
            {'error': 'Authentication or session required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = AddToCartSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    product_id = serializer.validated_data['product_id']
    quantity = serializer.validated_data['quantity']

    # Validate product exists and get price
    product = _fetch_product(product_id)
    if not product:
        return Response(
            {'error': 'Product not found or unavailable'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart = _get_or_create_cart(user_id, session_id)

    # Add or update item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product_id=product_id,
        defaults={
            'quantity': quantity,
            'price_at_add': product['price'],
        },
    )
    if not created:
        cart_item.quantity += quantity
        cart_item.price_at_add = product['price']
        cart_item.save()

    return Response(
        CartSerializer(cart).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_item(request, item_id):
    user_id, session_id = _get_cart_identity(request)
    cart = _get_cart(user_id, session_id)
    if not cart:
        return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
    except CartItem.DoesNotExist:
        return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UpdateCartItemSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    cart_item.quantity = serializer.validated_data['quantity']
    cart_item.save()

    return Response(CartSerializer(cart).data)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_item(request, item_id):
    user_id, session_id = _get_cart_identity(request)
    cart = _get_cart(user_id, session_id)
    if not cart:
        return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
    except CartItem.DoesNotExist:
        return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    cart_item.delete()
    return Response(CartSerializer(cart).data)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def clear_cart(request):
    user_id, session_id = _get_cart_identity(request)
    cart = _get_cart(user_id, session_id)
    if cart:
        cart.items.all().delete()
    return Response({'message': 'Cart cleared'})


@api_view(['POST'])
@permission_classes([AllowAny])
def merge_cart(request):
    """Merge guest cart into authenticated user's cart.

    Requires both JWT (user_id) and X-Session-Id (guest session).
    Items with the same product_id will have their quantities summed.
    """
    user_id, session_id = _get_cart_identity(request)

    if not user_id:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not session_id:
        return Response(
            {'error': 'No guest session to merge'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    guest_cart = Cart.objects.filter(session_id=session_id, user_id__isnull=True).first()
    if not guest_cart:
        # No guest cart to merge — just return user cart
        user_cart = _get_cart(user_id, None)
        if user_cart:
            return Response(CartSerializer(user_cart).data)
        return Response({'items': [], 'total': 0})

    with transaction.atomic():
        user_cart, _ = Cart.objects.get_or_create(
            user_id=user_id, defaults={'session_id': None}
        )

        for guest_item in guest_cart.items.all():
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product_id=guest_item.product_id,
                defaults={
                    'quantity': guest_item.quantity,
                    'price_at_add': guest_item.price_at_add,
                },
            )
            if not created:
                user_item.quantity += guest_item.quantity
                user_item.save()

        guest_cart.delete()

    return Response(CartSerializer(user_cart).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'cart_service'})
