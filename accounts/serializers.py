from adrf import serializers as adrf_serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import ValidationError

from .models import WebAccountLink, TelegramAccountLink

User = get_user_model()


class UserSerializer(adrf_serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "phone",
            "balance",
            "date_joined",
            "is_active",
            "is_staff",
        )
        read_only_fields = ("id", "date_joined", "is_active", "is_staff", 'username', 'balance')


class UserRegistrationSerializer(adrf_serializers.ModelSerializer):
    """
    Serializer for user registration with validation.
    """
    password = drf_serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'password', 'phone', 'first_name', 'last_name')

    def validate_password(self, value):
        """
        Custom password validation requiring:
        - At least 8 characters long
        """
        if len(value) < 8:
            raise drf_serializers.ValidationError(_("Password must be at least 8 characters long."))

        return value

    def validate_phone(self, value):
        """
        Custom phone validation to ensure it is unique and properly formatted.
        """
        from accounts.utils import validate_phone, normalize_and_validate_phone

        try:
            # First validate the basic format
            validate_phone(value)

            # Then normalize to the standard format
            normalized_value = normalize_and_validate_phone(value)

            # Check if phone number is already in use
            if User.objects.filter(phone=normalized_value).exists():
                raise drf_serializers.ValidationError(_("A user with this phone number already exists."))

            return normalized_value
        except ValidationError as e:
            # Handle validation errors from the utility functions
            raise drf_serializers.ValidationError(str(e))

    def create(self, validated_data):
        """
        Create and return a new user with encrypted password.
        """
        user = User(
            username=validated_data['username'],
            phone=validated_data['phone'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class AccountLinkSerializer(adrf_serializers.ModelSerializer):
    """Base serializer for account links with common fields."""
    user = drf_serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = None  # To be specified by child classes
        fields = ("user", "created_at", "is_active")
        read_only_fields = ("created_at",)


class WebAccountLinkSerializer(AccountLinkSerializer):
    class Meta(AccountLinkSerializer.Meta):
        model = WebAccountLink
        fields = AccountLinkSerializer.Meta.fields + ("session_id",)


class TelegramAccountLinkSerializer(AccountLinkSerializer):
    class Meta(AccountLinkSerializer.Meta):
        model = TelegramAccountLink
        fields = AccountLinkSerializer.Meta.fields + ("telegram_id",)


class RefreshTokenSerializer(adrf_serializers.Serializer):
    refresh = drf_serializers.CharField(required=True, help_text="Refresh token to be blacklisted")
