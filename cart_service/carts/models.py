from django.db import models


class Cart(models.Model):
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user_id__isnull=False) | models.Q(session_id__isnull=False)
                ),
                name='cart_must_have_owner',
            ),
        ]

    def __str__(self):
        if self.user_id:
            return f"Cart(user={self.user_id})"
        return f"Cart(session={self.session_id})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product_id']

    def __str__(self):
        return f"CartItem(product={self.product_id}, qty={self.quantity})"
