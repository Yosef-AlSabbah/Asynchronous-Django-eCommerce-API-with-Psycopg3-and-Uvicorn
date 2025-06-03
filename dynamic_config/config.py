import logging
from typing import Any, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from .models import GlobalConfig, UserConfig

logger = logging.getLogger(__name__)
User = get_user_model()

# Cache timeout in seconds (24 hours)
CACHE_TIMEOUT = getattr(settings, 'CONFIG_CACHE_TIMEOUT', None)

# Special marker to indicate no user config exists
NO_USER_CONFIG_MARKER = "__NO_USER_CONFIG__"


class ConfigManager:
    """
    Centralized configuration manager with Redis caching

    Usage:
        config = ConfigManager()

        # Get value for specific user (checks user config first, then global)
        limit = config.get('money_transfer_limit', user=user, default=1000)

        # Get global value only
        global_limit = config.get_global('money_transfer_limit', default=1000)

        # Set values
        config.set_global('money_transfer_limit', 5000, 'int')
        config.set_user('money_transfer_limit', user, 10000, 'int')
    """

    @staticmethod
    def get(key: str, user: Optional[User] = None, default: Any = None) -> Any:
        """
        Get configuration value with user-specific override support

        Args:
            key: Configuration key
            user: User instance (if None, returns global value only)
            default: Default value if not found

        Returns:
            Configuration value (user-specific if exists, otherwise global, otherwise default)
        """
        if user:
            # First check for user-specific config
            user_value = ConfigManager._get_user_config(key, user.id)
            if user_value is not None:
                return user_value

        # Fall back to global config
        global_value = ConfigManager._get_global_config(key)
        return global_value if global_value is not None else default

    @staticmethod
    def get_global(key: str, default: Any = None) -> Any:
        """Get global configuration value only"""
        value = ConfigManager._get_global_config(key)
        return value if value is not None else default

    @staticmethod
    def get_user(key: str, user: User, default: Any = None) -> Any:
        """Get user-specific configuration value only"""
        value = ConfigManager._get_user_config(key, user.id)
        return value if value is not None else default

    @staticmethod
    def _get_global_config(key: str) -> Optional[Any]:
        """Get global config with caching"""
        cache_key = f"config:global:{key}"

        # Try cache first
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Cache miss -> query database
        try:
            config = GlobalConfig.objects.get(key=key)
            value = config.get_typed_value()

            # Cache the result
            cache.set(cache_key, value, CACHE_TIMEOUT)
            return value
        except GlobalConfig.DoesNotExist:
            # Cache that this key doesn't exist to avoid repeated DB queries
            cache.set(cache_key, NO_USER_CONFIG_MARKER, CACHE_TIMEOUT)
            return None

    @staticmethod
    def _get_user_config(key: str, user_id: int) -> Optional[Any]:
        """Get user config with caching"""
        cache_key = f"config:user:{user_id}:{key}"
        none_cache_key = f"config:user:{user_id}:{key}:none"

        # Try cache first
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Check if we've cached that this user config doesn't exist
        if cache.get(none_cache_key) == NO_USER_CONFIG_MARKER:
            return None

        # Cache miss - query database
        try:
            config = UserConfig.objects.get(user_id=user_id, key=key)
            value = config.get_typed_value()

            # Cache the result
            cache.set(cache_key, value, CACHE_TIMEOUT)
            return value
        except UserConfig.DoesNotExist:
            # Cache that this user config doesn't exist
            cache.set(none_cache_key, NO_USER_CONFIG_MARKER, CACHE_TIMEOUT)
            return None

    @staticmethod
    def set_global(key: str, value: Any, value_type: str = 'str') -> None:
        """Set global configuration value"""
        config, created = GlobalConfig.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value),
                'value_type': value_type
            }
        )

        # Invalidate cache
        cache_key = f"config:global:{key}"
        cache.delete(cache_key)

        logger.info(f"{'Created' if created else 'Updated'} global config: {key} = {value}")

    @staticmethod
    def set_user(key: str, user: User, value: Any, value_type: str = 'str') -> None:
        """Set user-specific configuration value"""
        config, created = UserConfig.objects.update_or_create(
            user=user,
            key=key,
            defaults={
                'value': str(value),
                'value_type': value_type
            }
        )

        # Invalidate cache
        cache_key = f"config:user:{user.id}:{key}"
        none_cache_key = f"config:user:{user.id}:{key}:none"
        cache.delete(cache_key)
        cache.delete(none_cache_key)

        logger.info(f"{'Created' if created else 'Updated'} user config for {user.username}: {key} = {value}")

    @staticmethod
    def delete_global(key: str) -> bool:
        """Delete global configuration"""
        try:
            GlobalConfig.objects.get(key=key).delete()
            cache_key = f"config:global:{key}"
            cache.delete(cache_key)
            return True
        except GlobalConfig.DoesNotExist:
            return False

    @staticmethod
    def delete_user(key: str, user: User) -> bool:
        """Delete user-specific configuration"""
        try:
            UserConfig.objects.get(user=user, key=key).delete()
            cache_key = f"config:user:{user.id}:{key}"
            none_cache_key = f"config:user:{user.id}:{key}:none"
            cache.delete(cache_key)
            cache.delete(none_cache_key)
            return True
        except UserConfig.DoesNotExist:
            return False

    @staticmethod
    def preload_cache(keys: list = None) -> None:
        """Preload commonly used configs into cache"""
        if keys is None:
            # Load all global configs
            global_configs = GlobalConfig.objects.all()
        else:
            global_configs = GlobalConfig.objects.filter(key__in=keys)

        for config in global_configs:
            cache_key = f"config:global:{config.key}"
            cache.set(cache_key, config.get_typed_value(), CACHE_TIMEOUT)


# Convenient module-level functions
def get_config(key: str, user: Optional[User] = None, default: Any = None) -> Any:
    """Convenient function to get configuration value"""
    return ConfigManager.get(key, user, default)


def set_global_config(key: str, value: Any, value_type: str = 'str') -> None:
    """Convenient function to set global configuration"""
    return ConfigManager.set_global(key, value, value_type)


def set_user_config(key: str, user: User, value: Any, value_type: str = 'str') -> None:
    """Convenient function to set user configuration"""
    return ConfigManager.set_user(key, user, value, value_type)
