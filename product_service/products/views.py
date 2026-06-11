from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Category, ClothesProduct, ComputerProduct, MobileProduct, Product, SubCategory
from .serializers import (
    CategorySerializer,
    ClothesProductSerializer,
    ComputerProductSerializer,
    MobileProductSerializer,
    ProductSerializer,
    SubCategorySerializer,
)
from shared.rbac import is_admin


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def product_list(request):
    if request.method == 'GET':
        qs = Product.objects.filter(is_active=True).select_related('category', 'subcategory')
        # Filter by category
        category_id = request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        # Filter by subcategory
        subcategory_id = request.query_params.get('subcategory')
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)

    # POST — requires admin
    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def product_detail(request, pk):
    try:
        product = Product.objects.select_related('category', 'subcategory').get(pk=pk)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        product.is_active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def category_list(request):
    if request.method == 'GET':
        categories = Category.objects.prefetch_related('subcategories').all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def subcategory_list(request):
    if request.method == 'GET':
        qs = SubCategory.objects.select_related('category').all()
        category_id = request.query_params.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        serializer = SubCategorySerializer(qs, many=True)
        return Response(serializer.data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    serializer = SubCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def subcategory_detail(request, pk):
    try:
        subcategory = SubCategory.objects.select_related('category').get(pk=pk)
    except SubCategory.DoesNotExist:
        return Response({'error': 'SubCategory not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(SubCategorySerializer(subcategory).data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = SubCategorySerializer(subcategory, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        subcategory.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _domain_queryset(model):
    return model.objects.filter(product__is_active=True).select_related(
        'product', 'product__category', 'product__subcategory'
    )


def _domain_list(request, model, serializer_class):
    if request.method == 'GET':
        serializer = serializer_class(_domain_queryset(model), many=True)
        return Response(serializer.data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = serializer_class(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _domain_detail(request, pk, model, serializer_class, domain_name):
    try:
        item = model.objects.select_related(
            'product', 'product__category', 'product__subcategory'
        ).get(pk=pk)
    except model.DoesNotExist:
        return Response({'error': f'{domain_name} not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(serializer_class(item).data)

    if not is_admin(request):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = serializer_class(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        item.product.is_active = False
        item.product.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def computer_list(request):
    return _domain_list(request, ComputerProduct, ComputerProductSerializer)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def computer_detail(request, pk):
    return _domain_detail(request, pk, ComputerProduct, ComputerProductSerializer, 'Computer product')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def mobile_list(request):
    return _domain_list(request, MobileProduct, MobileProductSerializer)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def mobile_detail(request, pk):
    return _domain_detail(request, pk, MobileProduct, MobileProductSerializer, 'Mobile product')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def clothes_list(request):
    return _domain_list(request, ClothesProduct, ClothesProductSerializer)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def clothes_detail(request, pk):
    return _domain_detail(request, pk, ClothesProduct, ClothesProductSerializer, 'Clothes product')


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'product_service'})
