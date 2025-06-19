from django.conf import settings
from django.db import models
from django.db.models import TextChoices
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from slugify import slugify
from taggit.managers import TaggableManager

from auditlog.records import AuditLogRecords
from shop.utils import validate_image, product_image_path


class Category(models.Model):
    """Product category model"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug'], name='category_slug_idx'),
        ]

    def __str__(self) -> str:
        """
        Returns the string representation of the category.

        Returns:
            str: The name of the category.
        """
        return self.name

    def save(self, *args, **kwargs) -> None:
        """
        Saves the category instance, automatically generating a slug from the name.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        from django.db import IntegrityError

        try:
            self.slug = slugify(self.name)
            super().save(*args, **kwargs)
        except IntegrityError as e:
            print(e)
            # Handle duplicate name (slug) error here
            raise IntegrityError(_("A category with this name already exists."))

    def get_absolute_url(self) -> str:
        """
        Returns the absolute URL for the category detail page.

        Returns:
            str: The URL for the category detail view.
        """
        return reverse('shop:category_detail', args=[self.slug])


class Product(models.Model):
    """Product model"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)

    # User who submitted the product
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )

    thumbnail = models.ImageField(
        upload_to=product_image_path,
        validators=[validate_image],
        help_text=_("Upload a product image (JPEG, PNG, max 1MB)"),
        blank=True,
    )

    tags = TaggableManager(blank=True)

    auditlog = AuditLogRecords(exclude_fields=['thumbnail'])  # Enable audit logging

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['-created_at']
        # Create a compound unique constraint for owner + product
        unique_together = ['owner', 'id']

    def __str__(self) -> str:
        """
        Returns the string representation of the product.

        Returns:
            str: The name of the product.
        """
        return self.name

    def save(self, *args, **kwargs) -> None:
        """
        Saves the product instance, automatically generating a slug from the name.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        from datetime import datetime
        slug_base = slugify(self.name)
        if not self.pk:  # Only add timestamp on creation
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.slug = f"{slug_base}-{timestamp}"
        else:
            self.slug = slug_base
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        """
        Returns the absolute URL for the product detail page.

        Returns:
            str: The URL for the product detail view.
        """
        return reverse('shop:product_detail', args=[self.slug])

    @property
    def current_approval(self) -> 'ProductStatus | None':
        """Get the latest approval status, or None if never reviewed"""
        return self.approval_history.order_by('-created_at').first()


class ProductStatus(models.Model):
    """Model to track approval history for products"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='approval_history'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class StatusChoices(TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='product_reviews',
        null=True,
    )

    notes = models.TextField(
        blank=True,
        help_text=_("Notes about the approval/rejection decision")
    )

    class Meta:
        verbose_name = _("Product Approval")
        verbose_name_plural = _("Product Approvals")
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __str__(self) -> str:
        """
        Returns the string representation of the product approval status.

        Returns:
            str: The status and product name.
        """
        return f"{self.get_status_display()} for {self.product.name}"
