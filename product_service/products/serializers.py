from rest_framework import serializers
from .models import Category, ClothesProduct, ComputerProduct, MobileProduct, Product, SubCategory


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'description', 'slug', 'category', 'category_name']
        read_only_fields = ['slug']


class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'slug', 'subcategories']
        read_only_fields = ['slug']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, default=None)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock',
            'category', 'category_name',
            'subcategory', 'subcategory_name',
            'image_url', 'is_active',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        category = attrs.get('category')
        subcategory = attrs.get('subcategory')

        if self.instance:
            category = category if 'category' in attrs else self.instance.category
            subcategory = subcategory if 'subcategory' in attrs else self.instance.subcategory

        if subcategory and category and subcategory.category_id != category.id:
            raise serializers.ValidationError({
                'subcategory': 'Subcategory must belong to the selected category.'
            })

        if subcategory and not category:
            attrs['category'] = subcategory.category

        return attrs


class ComputerProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source='product', queryset=Product.objects.all(), write_only=True
    )

    class Meta:
        model = ComputerProduct
        fields = [
            'id', 'product', 'product_id',
            'brand', 'ram', 'storage', 'cpu', 'screen_size',
        ]


class MobileProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source='product', queryset=Product.objects.all(), write_only=True
    )

    class Meta:
        model = MobileProduct
        fields = [
            'id', 'product', 'product_id',
            'brand', 'screen_size', 'battery', 'operating_system',
        ]


class ClothesProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source='product', queryset=Product.objects.all(), write_only=True
    )

    class Meta:
        model = ClothesProduct
        fields = [
            'id', 'product', 'product_id',
            'size', 'color', 'material', 'gender',
        ]
