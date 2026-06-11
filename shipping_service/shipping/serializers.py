from rest_framework import serializers
from .models import ShippingMethod, Shipment, TrackingEvent


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = '__all__'


class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = '__all__'


class ShipmentSerializer(serializers.ModelSerializer):
    events = TrackingEventSerializer(many=True, read_only=True)
    method_detail = ShippingMethodSerializer(source='method', read_only=True)

    class Meta:
        model = Shipment
        fields = '__all__'


class CreateShipmentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    method_id = serializers.IntegerField()
    shipping_address = serializers.CharField()
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)


class CalculateShippingSerializer(serializers.Serializer):
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, default=1)
