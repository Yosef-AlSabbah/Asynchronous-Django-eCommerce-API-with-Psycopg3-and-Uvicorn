from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "auditlog"
    verbose_name = 'Audit Log'

    def ready(self):
        try:
            # Only connect signals when models are ready
            from .signals import connect_signals
            connect_signals()
        except:
            # Handle import errors during Django startup
            pass
