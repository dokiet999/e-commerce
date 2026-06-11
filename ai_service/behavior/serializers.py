from rest_framework import serializers
from .models import BehaviorEvent, UserBehaviorProfile


class BehaviorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorEvent
        fields = [
            'id', 'user_id', 'session_id', 'event_type',
            'product_id', 'category_id', 'search_query',
            'metadata', 'created_at',
        ]
        read_only_fields = ['id', 'user_id', 'session_id', 'created_at']


class BehaviorEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorEvent
        fields = [
            'event_type', 'product_id', 'category_id',
            'search_query', 'metadata',
        ]


class UserBehaviorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBehaviorProfile
        fields = [
            'user_id', 'session_id', 'total_views', 'total_cart_actions',
            'total_searches', 'preferred_categories', 'price_range_preference',
            'activity_pattern', 'behavior_cluster', 'predicted_intent',
            'purchase_likelihood', 'last_updated',
        ]
        read_only_fields = fields
