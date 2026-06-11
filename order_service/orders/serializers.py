from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user_id', 'status', 'total_amount',
            'shipping_address', 'billing_address',
            'payment_id', 'shipping_id', 'notes',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'total_amount', 'created_at', 'updated_at']


class CreateOrderSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()
    billing_address = serializers.CharField(required=False, default='')
    notes = serializers.CharField(required=False, default='')


class UpdateStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
