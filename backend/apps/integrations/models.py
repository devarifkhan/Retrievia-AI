import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedTextField

from apps.accounts.models import Organization


SOURCE_CHOICES = [
    ("slack", "Slack"),
    ("gdrive", "Google Drive"),
    ("gmail", "Gmail"),
    ("notion", "Notion"),
]


class Integration(models.Model):
    """
    Represents one connected data source for an organization.
    e.g. one Slack workspace, one Google Drive, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="integrations"
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    display_name = models.CharField(max_length=255, blank=True)

    # Encrypted config: workspace IDs, bot tokens for org-level access
    config = EncryptedTextField(default="{}")

    # Incremental sync cursors (per-source format)
    sync_cursor = models.JSONField(default=dict, blank=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations"
        unique_together = [("organization", "source")]

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.source}"

    def get_config(self) -> dict:
        import json

        return json.loads(self.config or "{}")

    def set_config(self, data: dict) -> None:
        import json

        self.config = json.dumps(data)


class SyncLog(models.Model):
    """Records each sync job run for audit and monitoring."""

    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("partial", "Partial"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="sync_logs")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    docs_processed = models.IntegerField(default=0)
    docs_failed = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    triggered_by = models.CharField(
        max_length=20,
        choices=[("scheduled", "Scheduled"), ("webhook", "Webhook"), ("manual", "Manual")],
        default="scheduled",
    )

    class Meta:
        db_table = "sync_logs"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.integration} sync at {self.started_at} — {self.status}"
