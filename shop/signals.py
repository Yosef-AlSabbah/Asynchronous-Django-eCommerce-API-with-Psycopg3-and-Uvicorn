from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProductStatus
from .tasks import update_product_approval_task


@receiver(post_save, sender=ProductStatus)
def update_product_approval_status(sender, instance, created, **kwargs):
    """
    Update the `is_approved` field on the related `Product` when a
    `ProductStatus` is created.
    """
    if not created:
        return

    product = instance.product

    # To avoid redundant updates, only proceed if the product's approval
    is_approved = (instance.status == ProductStatus.StatusChoices.APPROVED)
    # status is different from the new status.
    if product.is_approved != is_approved:
        # Asynchronously update the product's is_approved field.
        update_product_approval_task.delay(product.pk, is_approved)
