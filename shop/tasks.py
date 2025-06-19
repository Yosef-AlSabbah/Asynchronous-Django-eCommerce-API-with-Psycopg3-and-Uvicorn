from celery import shared_task

from .models import Product


@shared_task
def update_product_approval_task(product_id, is_approved):
    """
    Asynchronously updates the approval status of a product.
    """
    Product.objects.filter(pk=product_id).update(is_approved=is_approved)
