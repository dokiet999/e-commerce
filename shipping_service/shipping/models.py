from django.db import models


class ShippingMethod(models.Model):
    name = models.CharField(max_length=100)
    carrier = models.CharField(max_length=100)
    base_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_days_min = models.IntegerField(default=1)
    estimated_days_max = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.carrier} - {self.name}"


class Shipment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('failed', 'Failed'),
    ]

    order_id = models.IntegerField(db_index=True)
    method = models.ForeignKey(ShippingMethod, on_delete=models.SET_NULL, null=True)
    tracking_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.TextField()
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Shipment #{self.tracking_number} - Order #{self.order_id}"


class TrackingEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='events')
    status = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    event_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_time']

    def __str__(self):
        return f"{self.status} at {self.location}"
