from rest_framework import serializers
from .models import InventoryItem, StockMovement


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'


class StockActionSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reference_id = serializers.CharField(max_length=100, required=False, default='')
    notes = serializers.CharField(required=False, default='')
