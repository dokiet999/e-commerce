import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import is_admin, is_service_request
from .models import ShippingMethod, Shipment, TrackingEvent
from .serializers import (
    ShippingMethodSerializer, ShipmentSerializer, CreateShipmentSerializer,
    CalculateShippingSerializer,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def shipping_methods(request):
    methods = ShippingMethod.objects.filter(is_active=True)
    return Response(ShippingMethodSerializer(methods, many=True).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_shipping(request):
    serializer = CalculateShippingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    weight = serializer.validated_data.get('weight', Decimal('1'))
    methods = ShippingMethod.objects.filter(is_active=True)
    results = []
    for method in methods:
        cost = method.base_cost + (method.cost_per_kg * weight)
        results.append({
            'method_id': method.id,
            'name': method.name,
            'carrier': method.carrier,
            'cost': str(cost),
            'estimated_days': f"{method.estimated_days_min}-{method.estimated_days_max}",
        })
    return Response(results)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_shipment(request):
    if not is_service_request(request):
        return Response({'error': 'Service access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = CreateShipmentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        method = ShippingMethod.objects.get(pk=serializer.validated_data['method_id'], is_active=True)
    except ShippingMethod.DoesNotExist:
        return Response({'error': 'Shipping method not found'}, status=status.HTTP_404_NOT_FOUND)

    weight = serializer.validated_data.get('weight', Decimal('0'))
    cost = method.base_cost + (method.cost_per_kg * weight)
    tracking_number = f"TRK-{uuid.uuid4().hex[:12].upper()}"

    shipment = Shipment.objects.create(
        order_id=serializer.validated_data['order_id'],
        method=method,
        tracking_number=tracking_number,
        shipping_address=serializer.validated_data['shipping_address'],
        weight=weight,
        cost=cost,
    )

    TrackingEvent.objects.create(
        shipment=shipment,
        status='pending',
        description='Shipment created, awaiting pickup.',
    )

    return Response(ShipmentSerializer(shipment).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def track_shipment(request, tracking_number):
    try:
        shipment = Shipment.objects.prefetch_related('events').get(tracking_number=tracking_number)
    except Shipment.DoesNotExist:
        return Response({'error': 'Shipment not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(ShipmentSerializer(shipment).data)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_shipment_status(request, shipment_id):
    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        shipment = Shipment.objects.get(pk=shipment_id)
    except Shipment.DoesNotExist:
        return Response({'error': 'Shipment not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)

    valid_statuses = [c[0] for c in Shipment.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response({'error': f'Invalid status. Must be one of: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

    shipment.status = new_status
    if new_status == 'picked_up':
        shipment.shipped_at = timezone.now()
    elif new_status == 'delivered':
        shipment.delivered_at = timezone.now()
    shipment.save()

    TrackingEvent.objects.create(
        shipment=shipment,
        status=new_status,
        location=request.data.get('location', ''),
        description=request.data.get('description', f'Status updated to {new_status}'),
    )

    return Response(ShipmentSerializer(Shipment.objects.prefetch_related('events').get(pk=shipment.pk)).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'shipping_service'})
