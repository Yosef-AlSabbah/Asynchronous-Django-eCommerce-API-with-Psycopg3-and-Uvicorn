from django.db.models.signals import post_save, post_delete
from django.forms.models import model_to_dict
from django.apps import apps
from django.contrib.auth import get_user_model
from .registry import MODEL_REGISTRY
from .tasks import log_action_async

import threading

# Thread-local storage to track the current user (set this in middleware)
_thread_local = threading.local()


def get_current_user():
    """Get the current user from thread-local storage"""
    user_id = getattr(_thread_local, 'user_id', None)
    if user_id:
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass
    return None


def set_current_user(user):
    """Set the current user in thread-local storage"""
    if user and user.is_authenticated:
        _thread_local.user_id = user.id
    else:
        _thread_local.user_id = None


def connect_signals():
    """Connect signals for all registered models"""
    for model in MODEL_REGISTRY:
        post_save.connect(handle_save, sender=model, weak=False)
        post_delete.connect(handle_delete, sender=model, weak=False)


def handle_save(sender, instance, created, **kwargs):
    """Handle post_save signal"""
    # Get current user ID if available
    user = get_current_user()
    user_id = user.id if user else None

    # Model to dict for JSON serialization, excluding file fields
    changes = {}
    for field in instance._meta.fields:
        if field.name not in getattr(instance.auditlog, 'exclude_fields', []):
            value = getattr(instance, field.name)
            if not field.is_relation:
                changes[field.name] = value
            else:
                # Handle foreign keys
                changes[field.name] = str(value) if value else None

    # Send to Celery task
    log_action_async.delay(
        user_id=user_id,
        table=sender.__name__,
        object_id=str(instance.pk),
        action='create' if created else 'update',
        changes=changes
    )


def handle_delete(sender, instance, **kwargs):
    """Handle post_delete signal"""
    # Get current user ID if available
    user = get_current_user()
    user_id = user.id if user else None

    # Send to Celery task
    log_action_async.delay(
        user_id=user_id,
        table=sender.__name__,
        object_id=str(instance.pk),
        action='delete',
        changes=None  # No changes for deletion
    )