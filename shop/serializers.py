from rest_framework import serializers
from taggit.serializers import TagListSerializerField, TaggitSerializer
from .models import Category, Product, ProductImage, ProductStatus


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for a Category model"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent']
        read_only_fields = ['slug']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage model"""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary']


class ProductApprovalSerializer(serializers.ModelSerializer):
    """Serializer for ProductApproval model"""
    reviewer_name = serializers.ReadOnlyField(source='reviewer.username')

    class Meta:
        model = ProductStatus
        fields = ['id', 'status', 'notes', 'reviewer_name', 'created_at']
        read_only_fields = ['created_at']


class ProductSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for a Product model"""
    tags = TagListSerializerField()
    category_name = serializers.ReadOnlyField(source='categories.name')
    images = ProductImageSerializer(many=True, read_only=True)
    approval_status = serializers.SerializerMethodField()
    user_username = serializers.ReadOnlyField(source='user.username')
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'price',
            'categories', 'category_name', 'available', 'user',
            'user_username', 'tags', 'images', 'primary_image',
            'approval_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'user', 'created_at', 'updated_at']

    def get_approval_status(self, obj):
        """Get the current approval status"""
        latest = obj.current_approval
        if not latest:
            return 'pending'
        return latest.status

    def get_primary_image(self, obj):
        """Get the primary image for the product"""
        primary = obj.primary_image
        if primary:
            request = self.context.get('request')
            if request and hasattr(primary.image, 'url'):
                return request.build_absolute_uri(primary.image.url)
            elif hasattr(primary.image, 'url'):
                return primary.image.url
        return None
