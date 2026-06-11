from rest_framework import serializers
from .models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'


class CouponUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponUsage
        fields = '__all__'


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_id = serializers.IntegerField()
    order_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class CreateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, default='')
    discount_type = serializers.ChoiceField(choices=Coupon.DISCOUNT_TYPE_CHOICES)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    usage_limit = serializers.IntegerField(required=False, allow_null=True)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()
    applicable_categories = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    applicable_products = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
