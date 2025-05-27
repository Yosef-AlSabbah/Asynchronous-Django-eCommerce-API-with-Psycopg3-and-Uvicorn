from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from accounts.utils import validate_phone
from auditlog.records import AuditLogRecords


class User(AbstractUser):
    # User's phone number must be unique
    phone = models.CharField(
        max_length=16,
        unique=True,
        validators=[validate_phone],
    )
    # User's account balance cannot be negative
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
        ],
    )
    # Date and time when the user joined
    date_joined = models.DateTimeField(auto_now_add=True)

    auditlog = AuditLogRecords()  # Enable audit logging

    def clean(self) -> None:
        super().clean()
        from .utils import normalize_and_validate_phone

        # Normalize and validate the phone number before saving
        self.phone = normalize_and_validate_phone(self.phone)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class AccountLink(models.Model):
    # Reference to the user who owns this account link
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_links",  # Dynamic related_name based on child class
        on_delete=models.CASCADE,
    )
    # Timestamp when the link was created
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def clean(self) -> None:
        from dynamic_config.config import get_config

        super().clean()
        max_number_of_links = get_config(
            "max_account_links", 2
        )  # Default to 2 if not set
        if (
            self.user.webaccountlink_links.count()
            + self.user.telegramaccountlink_links.count()
            >= max_number_of_links
            and not self.pk
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                f"A user can have at most {max_number_of_links} account links."
            )

    class Meta:
        abstract = True  # This is an abstract base class
        indexes = [
            models.Index(
                fields=["user", "created_at"],
            ),
        ]
        ordering = ["-created_at"]
        verbose_name = "Account Link"
        verbose_name_plural = "Account Links"


class WebAccountLink(AccountLink):
    # Session ID for the web account link
    session_id = models.CharField(max_length=100)

    class Meta(AccountLink.Meta):
        verbose_name = "Web Account Link"
        verbose_name_plural = "Web Account Links"


class TelegramAccountLink(AccountLink):
    # Telegram user ID for the linked account
    telegram_id = models.CharField(max_length=10)

    class Meta(AccountLink.Meta):
        verbose_name = "Telegram Account Link"
        verbose_name_plural = "Telegram Account Links"
