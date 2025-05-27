from django.conf import settings
from django.db import models


class ActionLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )

    # Who made the change (nullable for system actions)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        help_text='User who performed the action'
    )

    # What was changed
    table = models.CharField(max_length=100, help_text='Model name')
    object_id = models.CharField(max_length=100, help_text='Primary key of the object')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    # What was the change
    changes = models.JSONField(null=True, blank=True, help_text='Changed data')

    # When the change happened
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Action Log'
        verbose_name_plural = 'Action Logs'
        indexes = [
            models.Index(fields=['table', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.table}:{self.object_id} at {self.timestamp}"
