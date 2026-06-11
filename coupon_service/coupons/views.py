from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.rbac import get_user_id, is_admin
from .models import Coupon, CouponUsage
from .serializers import (
    CouponSerializer, ValidateCouponSerializer, ApplyCouponSerializer,
    CreateCouponSerializer,
)


def _validate_coupon_logic(code, order_amount, user_id=None):
    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
    except Coupon.DoesNotExist:
        return None, 'Coupon not found or inactive'

    now = timezone.now()
    if now < coupon.valid_from or now > coupon.valid_until:
        return None, 'Coupon is expired or not yet valid'

    if coupon.usage_limit and coupon.times_used >= coupon.usage_limit:
        return None, 'Coupon usage limit reached'

    if order_amount < coupon.min_order_amount:
        return None, f'Minimum order amount is ${coupon.min_order_amount}'

    if user_id and CouponUsage.objects.filter(coupon=coupon, user_id=user_id).exists():
        return None, 'You have already used this coupon'

    if coupon.discount_type == 'percentage':
        discount = order_amount * coupon.discount_value / Decimal('100')
        if coupon.max_discount:
            discount = min(discount, coupon.max_discount)
    else:
        discount = min(coupon.discount_value, order_amount)

    return coupon, discount


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_coupon(request):
    serializer = ValidateCouponSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = get_user_id(request)
    coupon, result = _validate_coupon_logic(
        serializer.validated_data['code'],
        serializer.validated_data['order_amount'],
        user_id,
    )

    if coupon is None:
        return Response({'valid': False, 'error': result}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'valid': True,
        'coupon': CouponSerializer(coupon).data,
        'discount': str(result),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def apply_coupon(request):
    user_id = get_user_id(request)
    if not user_id:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = ApplyCouponSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    coupon, result = _validate_coupon_logic(
        serializer.validated_data['code'],
        serializer.validated_data['order_amount'],
        user_id,
    )

    if coupon is None:
        return Response({'error': result}, status=status.HTTP_400_BAD_REQUEST)

    discount = result
    CouponUsage.objects.create(
        coupon=coupon,
        user_id=user_id,
        order_id=serializer.validated_data['order_id'],
        discount_applied=discount,
    )
    coupon.times_used += 1
    coupon.save()

    return Response({
        'coupon': CouponSerializer(coupon).data,
        'discount_applied': str(discount),
        'final_amount': str(serializer.validated_data['order_amount'] - discount),
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def coupon_list(request):
    if request.method == 'GET':
        if is_admin(request):
            coupons = Coupon.objects.all()
        else:
            coupons = Coupon.objects.filter(is_active=True, valid_until__gte=timezone.now())
        return Response(CouponSerializer(coupons, many=True).data)

    # POST — admin only
    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = CreateCouponSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    coupon = Coupon.objects.create(**serializer.validated_data)
    return Response(CouponSerializer(coupon).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def coupon_detail(request, coupon_id):
    try:
        coupon = Coupon.objects.get(pk=coupon_id)
    except Coupon.DoesNotExist:
        return Response({'error': 'Coupon not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CouponSerializer(coupon).data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    for field in ['code', 'description', 'discount_type', 'discount_value',
                   'min_order_amount', 'max_discount', 'usage_limit',
                   'valid_from', 'valid_until', 'is_active',
                   'applicable_categories', 'applicable_products']:
        if field in request.data:
            setattr(coupon, field, request.data[field])
    coupon.save()
    return Response(CouponSerializer(coupon).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'coupon_service'})
