from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import GlobalConfig, UserConfig


@receiver(post_save, sender=GlobalConfig)
def handle_global_config_save(sender, instance, **kwargs):
    """Update cache when a global config is saved"""
    global_key = f"global_config:{instance.key}"
    # Delete old cache entry first
    cache.delete(global_key)
    # Set new value
    cache.set(global_key, instance.get_typed_value())


@receiver(post_delete, sender=GlobalConfig)
def handle_global_config_delete(sender, instance, **kwargs):
    """Delete cache entries when a global config is deleted"""
    # Delete the global config cache entry
    global_key = f"global_config:{instance.key}"
    cache.delete(global_key)

    # Delete all user configs for this key using pattern matching
    pattern = f"user_config:*:{instance.key}"
    cache.delete_pattern(pattern)


@receiver(post_save, sender=UserConfig)
def handle_user_config_save(sender, instance, **kwargs):
    """Update cache when a user config is saved"""
    user_key = f"user_config:{instance.user.id}:{instance.key}"
    # Delete old cache entry first
    cache.delete(user_key)
    # Set new value
    cache.set(user_key, instance.get_typed_value())


@receiver(post_delete, sender=UserConfig)
def handle_user_config_delete(sender, instance, **kwargs):
    """Delete cache when a user config is deleted"""
    user_key = f"user_config:{instance.user.id}:{instance.key}"
    cache.delete(user_key)
