from rest_framework import serializers
from taggit.serializers import TagListSerializerField, TaggitSerializer

from .models import Category, Product, ProductStatus


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for a Category model"""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
        ]
        read_only_fields = ["slug"]


class ProductApprovalSerializer(serializers.ModelSerializer):
    """Serializer for ProductApproval model"""

    reviewer_name = serializers.ReadOnlyField(source="reviewer.username")

    class Meta:
        model = ProductStatus
        fields = [
            "id",
            "status",
            "notes",
            "reviewer_name",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ProductSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for a Product model"""

    # Field for handling product tags through taggit integration
    tags = TagListSerializerField()
    # Read-only field that displays the category name instead of just the ID
    category_name = serializers.ReadOnlyField(source="category.name")
    # Configurable image field for product thumbnail with validation settings
    thumbnail = serializers.ImageField(
        allow_null=True,
        required=False,
        use_url=True,
        help_text="Primary image for the product (JPEG, PNG, max 1MB)",
    )
    # Method field that retrieves the current product approval status
    approval_status = serializers.SerializerMethodField()
    # Read-only field that shows the username of the product owner
    user_username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "price",
            "category_name",
            "owner",
            "user_username",
            "tags",
            "thumbnail",
            "approval_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "slug",
            "owner",
            "created_at",
            "updated_at",
            "approval_status",
        ]

    def get_approval_status(self, obj):
        """Get the current approval status"""
        latest = obj.current_approval
        if not latest:
            return "pending"
        return latest.status

    def get_primary_image(self, obj):
        """Get the primary image for the product"""
        primary = obj.primary_image
        if primary:
            request = self.context.get("request")
            if request and hasattr(primary.image, "url"):
                return request.build_absolute_uri(primary.image.url)
            elif hasattr(primary.image, "url"):
                return primary.image.url
        return None
