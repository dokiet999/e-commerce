from rest_framework import serializers


class RecommendationItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    score = serializers.FloatField()
    reason = serializers.CharField()
    product = serializers.DictField(required=False)


class RecommendationResponseSerializer(serializers.Serializer):
    recommendations = RecommendationItemSerializer(many=True)
    count = serializers.IntegerField()
    recommendation_type = serializers.CharField()
