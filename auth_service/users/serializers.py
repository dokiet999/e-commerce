from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


def get_user_role(user):
    return 'admin' if user.is_staff or user.is_superuser else 'user'


class RBACTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = get_user_role(user)
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'password2', 'phone', 'address']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        return get_user_role(obj)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'address', 'date_joined',
            'role', 'is_staff', 'is_superuser',
        ]
        read_only_fields = ['id', 'date_joined', 'role', 'is_staff', 'is_superuser']
