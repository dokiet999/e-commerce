import uuid
from django.db import models


class BehaviorEvent(models.Model):
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('product_view', 'Product View'),
        ('add_to_cart', 'Add to Cart'),
        ('remove_from_cart', 'Remove from Cart'),
        ('search', 'Search'),
        ('category_filter', 'Category Filter'),
        ('checkout', 'Checkout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    product_id = models.IntegerField(null=True, blank=True)
    category_id = models.IntegerField(null=True, blank=True)
    search_query = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'event_type']),
            models.Index(fields=['session_id', 'event_type']),
            models.Index(fields=['user_id', 'created_at']),
        ]

    def __str__(self):
        identifier = self.user_id or self.session_id or 'unknown'
        return f"{self.event_type} by {identifier} at {self.created_at}"


class UserBehaviorProfile(models.Model):
    INTENT_CHOICES = [
        ('browsing', 'Browsing'),
        ('buying', 'Buying'),
        ('comparing', 'Comparing'),
        ('returning', 'Returning'),
    ]

    user_id = models.IntegerField(unique=True, null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    total_views = models.IntegerField(default=0)
    total_cart_actions = models.IntegerField(default=0)
    total_searches = models.IntegerField(default=0)
    preferred_categories = models.JSONField(default=dict, blank=True)
    price_range_preference = models.JSONField(default=dict, blank=True)
    activity_pattern = models.JSONField(default=dict, blank=True)
    behavior_cluster = models.IntegerField(null=True, blank=True)
    predicted_intent = models.CharField(
        max_length=20, choices=INTENT_CHOICES, null=True, blank=True
    )
    purchase_likelihood = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user_id__isnull=False) | models.Q(session_id__isnull=False),
                name='behavior_profile_has_identifier',
            )
        ]

    def __str__(self):
        identifier = self.user_id or self.session_id
        return f"Profile: {identifier} (intent={self.predicted_intent})"
