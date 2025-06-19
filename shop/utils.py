import os
import uuid

from PIL import Image
from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


def validate_image(image):
    """Validate image dimensions, size and format"""
    img = Image.open(image)

    # Validate format
    if img.format not in settings.PRODUCT_IMAGE_FORMATS:
        valid_formats = ', '.join(settings.PRODUCT_IMAGE_FORMATS)
        raise ValidationError(_(f"Image format must be one of: {valid_formats}"))

    # Validate dimensions
    min_width, min_height = settings.PRODUCT_IMAGE_MIN_RESOLUTION
    max_width, max_height = settings.PRODUCT_IMAGE_MAX_RESOLUTION

    if img.width < min_width or img.height < min_height:
        raise ValidationError(
            _(f"Image resolution is too small. Minimum resolution is {min_width}x{min_height}")
        )

    if img.width > max_width or img.height > max_height:
        raise ValidationError(
            _(f"Image resolution is too large. Maximum resolution is {max_width}x{max_height}")
        )

    # Validate file size
    if image.size > settings.PRODUCT_IMAGE_MAX_SIZE:
        max_size_mb = settings.PRODUCT_IMAGE_MAX_SIZE / (1024 * 1024)
        raise ValidationError(_(f"Image file size must not exceed {max_size_mb}MB"))


def product_image_path(instance, filename):
    """Generate a unique path for product images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('products', str(instance.product.id), filename)


def search_products(queryset, search_term):
    """
    Centralized search function to filter products by name and description similarity.
    """
    if search_term:
        return queryset.annotate(
            name_similarity=TrigramSimilarity('name', search_term),
            description_similarity=TrigramSimilarity('short_description', search_term),
        ).filter(
            name_similarity__gt=0.1,
            description_similarity__gt=0.05,
        ).order_by('-name_similarity', '-description_similarity')
    return queryset
