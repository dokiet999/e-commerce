from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class CreatePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    method = serializers.ChoiceField(choices=Payment.METHOD_CHOICES)
    payment_details = serializers.JSONField(required=False, default=dict)


class RefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    reason = serializers.CharField(max_length=500, required=False, default='')
