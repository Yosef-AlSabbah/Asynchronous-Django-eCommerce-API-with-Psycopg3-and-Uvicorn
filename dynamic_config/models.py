import json

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class GlobalConfig(models.Model):
    """Global configuration values that can be changed at runtime"""
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField()
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('int', 'Integer'),
            ('float', 'Float'),
            ('str', 'String'),
            ('bool', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='str'
    )
    description = models.TextField(blank=True, help_text="What this config does")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dynamic_config_global'
        verbose_name = 'Global Configuration'
        verbose_name_plural = 'Global Configurations'

    def __str__(self):
        return f"{self.key}: {self.value}"

    def get_typed_value(self):
        """Convert stored value to its proper type"""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            return json.loads(self.value)
        return self.value


class UserConfig(models.Model):
    """User-specific configuration overrides"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    key = models.CharField(max_length=100, db_index=True)
    value = models.TextField()
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('int', 'Integer'),
            ('float', 'Float'),
            ('str', 'String'),
            ('bool', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='str'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dynamic_config_user'
        unique_together = ('user', 'key')
        verbose_name = 'User Configuration'
        verbose_name_plural = 'User Configurations'

    def __str__(self):
        return f"{self.user.username} - {self.key}: {self.value}"

    def get_typed_value(self):
        """Convert stored value to its proper type"""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            return json.loads(self.value)
        return self.value
