"""
Decorators for easy configuration usage
"""
from functools import wraps
from typing import Any, Optional, Callable
from .config import config


def cached_config(key: str, default: Any = None, user_param: str = 'user',
                  inject_as: Optional[str] = None, timeout: Optional[int] = None):
    """
    Decorator to inject configuration values into functions/views

    Usage:
        @cached_config('max_uploads', default=10)
        def upload_view(request, max_uploads=None):
            # max_uploads will be automatically injected
            pass

        @cached_config('rate_limit', user_param='request.user', inject_as='limit')
        def api_view(request, limit=None):
            # limit will contain the rate_limit config value
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user from arguments
            user = None
            if user_param:
                # Support nested attribute access like 'request.user'
                parts = user_param.split('.')
                obj = None

                # Find the object in args/kwargs
                if parts[0] in kwargs:
                    obj = kwargs[parts[0]]
                else:
                    # Try to find in args by position (for common patterns)
                    if parts[0] == 'request' and args:
                        obj = args[0]  # Usually request is first arg in views
                    elif parts[0] == 'user' and len(args) > 1:
                        obj = args[1]  # User might be second arg

                # Navigate through the attribute path
                if obj:
                    for part in parts[1:]:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        else:
                            obj = None
                            break
                    user = obj

            # Get configuration value
            value = config.get(key, user, default)

            # Inject into function
            param_name = inject_as or key.replace('-', '_').replace(' ', '_')
            kwargs[param_name] = value

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_config(key: str, error_message: Optional[str] = None, user_param: str = 'user'):
    """
    Decorator that requires a configuration to be set

    Usage:
        @require_config('feature_enabled', 'Feature is disabled')
        def feature_view(request):
            # Only executes if feature_enabled is truthy
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user (similar to cached_config)
            user = None
            if user_param and args:
                if user_param == 'request.user' and hasattr(args[0], 'user'):
                    user = args[0].user
                elif user_param == 'user':
                    user = kwargs.get('user') or (args[1] if len(args) > 1 else None)

            # Check configuration
            value = config.get(key, user)
            if not value:
                from django.http import HttpResponseForbidden
                message = error_message or f"Configuration '{key}' is required but not set"
                return HttpResponseForbidden(message)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def config_cache_key(key_template: str, user_param: str = 'user'):
    """
    Generate cache keys based on configuration and user

    Usage:
        @config_cache_key('user_data_{user.id}_{feature_flag}')
        def get_user_data(request):
            # Cache key will be dynamically generated
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would integrate with Django's cache framework
            # Implementation depends on specific caching needs
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Shorthand decorators for common cases
def user_limit(limit_key: str, default: int = 100):
    """Shorthand for user limits"""
    return cached_config(f'limit_{limit_key}', default=default, inject_as=f'{limit_key}_limit')


def feature_flag(flag_key: str, default: bool = False):
    """Shorthand for feature flags"""
    return cached_config(f'feature_{flag_key}', default=default, inject_as=f'{flag_key}_enabled')


def rate_limit(limit_key: str, default: int = 1000):
    """Shorthand for rate limits"""
    return cached_config(f'rate_limit_{limit_key}', default=default, inject_as=f'{limit_key}_rate_limit')