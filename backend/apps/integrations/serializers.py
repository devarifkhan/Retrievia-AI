from rest_framework import serializers

from .models import Integration, SyncLog


class IntegrationSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = Integration
        fields = [
            "id",
            "source",
            "source_display",
            "display_name",
            "is_active",
            "last_synced_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "last_synced_at"]


class SyncLogSerializer(serializers.ModelSerializer):
    integration_source = serializers.CharField(source="integration.source", read_only=True)

    class Meta:
        model = SyncLog
        fields = [
            "id",
            "integration",
            "integration_source",
            "started_at",
            "completed_at",
            "status",
            "docs_processed",
            "docs_failed",
            "error_message",
            "triggered_by",
        ]
        read_only_fields = fields
