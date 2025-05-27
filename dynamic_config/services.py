from django.core.cache import cache

from dynamic_config.models import UserConfig, GlobalConfig


class ConfigService:
    @classmethod
    def get(cls, key, user=None, default=None):
        """
        Retrieve a configuration value by key with caching support.
        This method first checks for a user-specific configuration if a user is provided,
        then falls back to global configuration if no user-specific value is found.
        Values are cached for 5 minutes (300 seconds) to improve performance.

        Args:
            key (str): The configuration key to retrieve
            default: Value to return if the key is not found in any configuration
            cast_type: Type to cast the value to (not currently used)
            user: Django user object for user-specific configurations

        Returns:
            The typed configuration value, or the default if not found
        """
        # Try user-specific config first if user is provided
        if user:
            user_key = f"user_config:{user.id}:{key}"
            cached_val = cache.get(user_key)
            if cached_val is not None:
                return cached_val

            user_config = UserConfig.objects.filter(user=user, key=key).first()
            if user_config:
                typed_value = user_config.get_typed_value()
                cache.set(user_key, typed_value, 300)  # Fixed timeout value
                return typed_value

        # Fall back to global config if no user-specific value found
        global_key = f"global_config:{key}"
        cached_val = cache.get(global_key)
        if cached_val is not None:
            return cached_val

        global_config = GlobalConfig.objects.filter(key=key).first()
        if global_config:
            typed_value = global_config.get_typed_value()
            cache.set(global_key, typed_value, 300)
            return typed_value

        # Return default if no configuration found
        return default
