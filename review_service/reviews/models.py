from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    product_id = models.IntegerField(db_index=True)
    user_id = models.IntegerField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200, blank=True, default='')
    comment = models.TextField(blank=True, default='')
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product_id', 'user_id')

    def __str__(self):
        return f"Review by User #{self.user_id} for Product #{self.product_id} - {self.rating}/5"
