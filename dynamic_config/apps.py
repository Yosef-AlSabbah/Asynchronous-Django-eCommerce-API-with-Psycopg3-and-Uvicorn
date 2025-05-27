from django.apps import AppConfig


class DynamicConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dynamic_config'
    verbose_name = 'Dynamic Configuration'

    def ready(self):
        """Import signals when the app is ready"""
        import dynamic_config.signals