from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='subcategories'
    )

    class Meta:
        db_table = 'subcategories'
        verbose_name_plural = 'subcategories'
        unique_together = [('category', 'name')]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} > {self.name}"


class Product(models.Model):
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    subcategory = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    image_url = models.URLField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'

    def clean(self):
        if self.subcategory and self.category:
            if self.subcategory.category_id != self.category_id:
                raise ValidationError({
                    'subcategory': 'Subcategory must belong to the selected category.'
                })

        if self.subcategory and not self.category:
            self.category = self.subcategory.category

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ComputerProduct(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='computer_details'
    )
    brand = models.CharField(max_length=120)
    ram = models.CharField(max_length=80)
    storage = models.CharField(max_length=120)
    cpu = models.CharField(max_length=160)
    screen_size = models.CharField(max_length=80)

    class Meta:
        db_table = 'computer_products'

    def __str__(self):
        return f"Computer: {self.product.name}"


class MobileProduct(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='mobile_details'
    )
    brand = models.CharField(max_length=120)
    screen_size = models.CharField(max_length=80)
    battery = models.CharField(max_length=80)
    operating_system = models.CharField(max_length=120)

    class Meta:
        db_table = 'mobile_products'

    def __str__(self):
        return f"Mobile: {self.product.name}"


class ClothesProduct(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='clothes_details'
    )
    size = models.CharField(max_length=40)
    color = models.CharField(max_length=80)
    material = models.CharField(max_length=120)
    gender = models.CharField(max_length=40)

    class Meta:
        db_table = 'clothes_products'

    def __str__(self):
        return f"Clothes: {self.product.name}"
