class AuditLogRecords:
    """
    Add this as a field to any model you want to track:
    class MyModel(models.Model):
        # Your fields...
        auditlog = AuditLogRecords()
    """

    def __init__(self, exclude_fields=None):
        self.exclude_fields = exclude_fields or []

    def contribute_to_class(self, cls, name):
        """Django calls this when the model class is created"""
        from .registry import register_model
        register_model(cls)
        setattr(cls, name, self)
