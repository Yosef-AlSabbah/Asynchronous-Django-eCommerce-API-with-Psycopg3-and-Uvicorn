from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class SignatureAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'signature_auth'
    verbose_name = 'Signature Authentication'

    def ready(self):
        """Validate configuration and setup on app ready"""
        self._validate_configuration()
        self._check_cache_configuration()

    def _validate_configuration(self):
        """Validate required settings"""
        from django.conf import settings

        # Check secret key
        secret_key = getattr(settings, 'SIGNATURE_AUTH_SECRET_KEY', None)
        if not secret_key:
            raise ImproperlyConfigured(
                "SIGNATURE_AUTH_SECRET_KEY is required. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        # Validate secret key strength
        from .utils import validate_secret_key
        validation = validate_secret_key(secret_key)

        if not validation['valid']:
            raise ImproperlyConfigured(f"Invalid secret key: {validation['warnings']}")

        if validation['strength'] == 'weak':
            import warnings
            warnings.warn(
                f"Weak secret key detected: {validation['warnings']}. "
                f"Recommendations: {validation['recommendations']}",
                UserWarning
            )

    def _check_cache_configuration(self):
        """Check cache configuration and warn if needed"""
        from django.core.cache import cache
        from django.conf import settings
        import warnings

        try:
            # Test cache availability
            cache.set('signature_auth_test', 'test', 1)
            cache.delete('signature_auth_test')
        except Exception as e:
            use_fallback = getattr(settings, 'SIGNATURE_AUTH_USE_CACHE_FALLBACK', True)

            if use_fallback:
                warnings.warn(
                    f"Django cache unavailable ({e}), using in-memory fallback. "
                    "For production, configure a proper cache backend.",
                    UserWarning
                )
            else:
                raise ImproperlyConfigured(
                    f"Cache is unavailable ({e}) and fallback is disabled. "
                    "Configure Django cache or enable SIGNATURE_AUTH_USE_CACHE_FALLBACK."
                )