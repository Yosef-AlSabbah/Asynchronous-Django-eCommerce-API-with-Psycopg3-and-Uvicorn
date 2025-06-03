from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, WebAccountLink, TelegramAccountLink


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    readonly_fields = ('date_joined',) + tuple(getattr(BaseUserAdmin, 'readonly_fields', ()))


@admin.register(WebAccountLink)
class WebAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "session_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "user__phone", "session_id")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"


@admin.register(TelegramAccountLink)
class TelegramAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "user__phone", "telegram_id")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"