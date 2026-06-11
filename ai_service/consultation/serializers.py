from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    chat_session_id = serializers.UUIDField(required=False, allow_null=True)


class ChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField())
    chat_session_id = serializers.UUIDField()


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.CharField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField()
