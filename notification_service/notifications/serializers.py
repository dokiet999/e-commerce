from rest_framework import serializers


class NotificationCreateSerializer(serializers.Serializer):
    TYPE_CHOICES = [
        'order',
        'payment',
        'shipping',
        'promotion',
        'review',
        'system',
    ]
    CHANNEL_CHOICES = ['in_app', 'email', 'sms']

    user_id = serializers.IntegerField()
    notification_type = serializers.ChoiceField(
        choices=TYPE_CHOICES,
        default='system',
    )
    channel = serializers.ChoiceField(choices=CHANNEL_CHOICES, default='in_app')
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    order_id = serializers.IntegerField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)


class NotificationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    message = serializers.CharField(required=False)
    read_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False)


class NotificationListQuerySerializer(serializers.Serializer):
    unread_only = serializers.BooleanField(required=False, default=False)
    limit = serializers.IntegerField(required=False, default=50, min_value=1, max_value=100)
