# Generated by Django 5.2.1 on 2025-05-26 08:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(db_index=True, max_length=100, unique=True)),
                ("value", models.TextField()),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("int", "Integer"),
                            ("float", "Float"),
                            ("str", "String"),
                            ("bool", "Boolean"),
                            ("json", "JSON"),
                        ],
                        default="str",
                        max_length=20,
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, help_text="What this config does"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Global Configuration",
                "verbose_name_plural": "Global Configurations",
                "db_table": "dynamic_config_global",
            },
        ),
        migrations.CreateModel(
            name="UserConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(db_index=True, max_length=100)),
                ("value", models.TextField()),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("int", "Integer"),
                            ("float", "Float"),
                            ("str", "String"),
                            ("bool", "Boolean"),
                            ("json", "JSON"),
                        ],
                        default="str",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Configuration",
                "verbose_name_plural": "User Configurations",
                "db_table": "dynamic_config_user",
                "unique_together": {("user", "key")},
            },
        ),
    ]
