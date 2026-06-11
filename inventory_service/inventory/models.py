from django.db import models


class InventoryItem(models.Model):
    product_id = models.IntegerField(unique=True)
    quantity_available = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inventory for Product #{self.product_id} - Available: {self.quantity_available}"


class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('restock', 'Restock'),
        ('reserve', 'Reserve'),
        ('release', 'Release'),
        ('deduct', 'Deduct'),
        ('adjustment', 'Adjustment'),
    ]

    inventory = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.movement_type} {self.quantity} for Product #{self.inventory.product_id}"
