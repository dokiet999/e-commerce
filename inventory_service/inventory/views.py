from django.db import models, transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import is_admin, is_service_request
from .models import InventoryItem, StockMovement
from .serializers import InventoryItemSerializer, StockActionSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def inventory_detail(request, product_id):
    try:
        item = InventoryItem.objects.get(product_id=product_id)
    except InventoryItem.DoesNotExist:
        return Response({'error': 'Inventory item not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(InventoryItemSerializer(item).data)


def _stock_action(request, action_type):
    serializer = StockActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    product_id = serializer.validated_data['product_id']
    quantity = serializer.validated_data['quantity']
    reference_id = serializer.validated_data.get('reference_id', '')
    notes = serializer.validated_data.get('notes', '')

    with transaction.atomic():
        item, created = InventoryItem.objects.select_for_update().get_or_create(
            product_id=product_id,
            defaults={'quantity_available': 0, 'quantity_reserved': 0},
        )

        if action_type == 'reserve':
            if item.quantity_available < quantity:
                return Response(
                    {'error': 'Insufficient stock', 'available': item.quantity_available},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.quantity_available -= quantity
            item.quantity_reserved += quantity

        elif action_type == 'release':
            release_qty = min(quantity, item.quantity_reserved)
            item.quantity_reserved -= release_qty
            item.quantity_available += release_qty

        elif action_type == 'deduct':
            deduct_qty = min(quantity, item.quantity_reserved)
            item.quantity_reserved -= deduct_qty

        elif action_type == 'restock':
            item.quantity_available += quantity

        item.save()

        StockMovement.objects.create(
            inventory=item,
            movement_type=action_type,
            quantity=quantity,
            reference_id=reference_id,
            notes=notes,
        )

    return Response(InventoryItemSerializer(item).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def reserve_stock(request):
    if not is_service_request(request):
        return Response({'error': 'Service access required'}, status=status.HTTP_403_FORBIDDEN)
    return _stock_action(request, 'reserve')


@api_view(['POST'])
@permission_classes([AllowAny])
def release_stock(request):
    if not is_service_request(request):
        return Response({'error': 'Service access required'}, status=status.HTTP_403_FORBIDDEN)
    return _stock_action(request, 'release')


@api_view(['POST'])
@permission_classes([AllowAny])
def deduct_stock(request):
    if not is_service_request(request):
        return Response({'error': 'Service access required'}, status=status.HTTP_403_FORBIDDEN)
    return _stock_action(request, 'deduct')


@api_view(['POST'])
@permission_classes([AllowAny])
def restock(request):
    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    return _stock_action(request, 'restock')


@api_view(['GET'])
@permission_classes([AllowAny])
def low_stock(request):
    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    items = InventoryItem.objects.filter(
        quantity_available__lte=models.F('low_stock_threshold')
    )
    return Response(InventoryItemSerializer(items, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'inventory_service'})
