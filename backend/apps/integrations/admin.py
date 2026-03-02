from django.contrib import admin

from .models import Integration, SyncLog


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ["organization", "source", "display_name", "is_active", "last_synced_at"]
    list_filter = ["source", "is_active"]
    search_fields = ["organization__name", "display_name"]
    readonly_fields = ["last_synced_at", "sync_cursor"]


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = [
        "integration",
        "status",
        "docs_processed",
        "docs_failed",
        "triggered_by",
        "started_at",
        "completed_at",
    ]
    list_filter = ["status", "triggered_by"]
    readonly_fields = list_display
