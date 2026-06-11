from django.db import models


class ProductSimilarity(models.Model):
    SIMILARITY_TYPES = [
        ('content', 'Content-Based'),
        ('semantic', 'Semantic'),
        ('hybrid', 'Hybrid'),
    ]

    product_a_id = models.IntegerField(db_index=True)
    product_b_id = models.IntegerField(db_index=True)
    similarity_score = models.FloatField()
    similarity_type = models.CharField(max_length=20, choices=SIMILARITY_TYPES, default='hybrid')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_similarity'
        unique_together = [('product_a_id', 'product_b_id', 'similarity_type')]
        indexes = [
            models.Index(fields=['product_a_id', 'similarity_score']),
            models.Index(fields=['product_b_id', 'similarity_score']),
        ]

    def __str__(self):
        return f"Similarity({self.product_a_id} → {self.product_b_id}: {self.similarity_score:.3f})"


class ProductCoOccurrence(models.Model):
    product_a_id = models.IntegerField(db_index=True)
    product_b_id = models.IntegerField(db_index=True)
    co_occurrence_count = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_co_occurrence'
        unique_together = [('product_a_id', 'product_b_id')]
        indexes = [
            models.Index(fields=['product_a_id', 'co_occurrence_count']),
        ]

    def __str__(self):
        return f"CoOccur({self.product_a_id} → {self.product_b_id}: {self.co_occurrence_count})"


class RecommendationLog(models.Model):
    REC_TYPES = [
        ('personalized', 'Personalized'),
        ('similar', 'Similar Products'),
        ('also_bought', 'Also Bought'),
        ('trending', 'Trending'),
        ('cart', 'Cart-Based'),
    ]

    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    product_id = models.IntegerField()
    recommendation_type = models.CharField(max_length=20, choices=REC_TYPES)
    position = models.IntegerField(default=0)
    clicked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recommendation_log'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['recommendation_type', 'created_at']),
        ]

    def __str__(self):
        return f"RecLog({self.recommendation_type}: product {self.product_id})"
