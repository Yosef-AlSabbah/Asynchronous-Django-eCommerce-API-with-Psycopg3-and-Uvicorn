from django.contrib import admin
from .models import ActionLog


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'table', 'object_id', 'action', 'user')
    list_filter = ('action', 'table', 'timestamp')
    search_fields = ('table', 'object_id', 'user__username')
    readonly_fields = ('timestamp', 'table', 'object_id', 'action', 'user', 'changes')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False