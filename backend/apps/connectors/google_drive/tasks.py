import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue="sync", bind=True, max_retries=2)
def scheduled_sync_gdrive(self) -> dict:
    """Triggered by Celery Beat every 4 hours."""
    from apps.integrations.models import Integration

    integrations = Integration.objects.filter(source="gdrive", is_active=True)
    results = []
    for integration in integrations:
        task = full_sync_gdrive.delay(str(integration.id), triggered_by="scheduled")
        results.append({"integration_id": str(integration.id), "task_id": task.id})
    return {"dispatched": len(results), "tasks": results}


@shared_task(queue="sync", bind=True, max_retries=2)
def full_sync_gdrive(self, integration_id: str, triggered_by: str = "scheduled") -> dict:
    from apps.integrations.models import Integration, SyncLog
    from .connector import GoogleDriveConnector

    integration = Integration.objects.get(id=integration_id)
    sync_log = SyncLog.objects.create(
        integration=integration, triggered_by=triggered_by
    )

    try:
        connector = GoogleDriveConnector(integration_id, str(integration.organization_id))
        if not connector.authenticate():
            raise RuntimeError("Google Drive authentication failed")

        total = connector.run_full_sync()

        integration.last_synced_at = timezone.now()
        integration.save(update_fields=["last_synced_at"])

        sync_log.status = "success"
        sync_log.docs_processed = total
        sync_log.completed_at = timezone.now()
        sync_log.save()

        return {"status": "success", "docs_processed": total}

    except Exception as exc:
        sync_log.status = "failed"
        sync_log.error_message = str(exc)
        sync_log.completed_at = timezone.now()
        sync_log.save()
        raise self.retry(exc=exc, countdown=300)


@shared_task(queue="sync")
def handle_gdrive_push(resource_id: str, resource_uri: str, integration_id: str) -> dict:
    """Handle a Google Drive push notification (file change)."""
    from apps.ingestion.tasks import reindex_document

    reindex_document.delay(
        source="gdrive",
        source_item_id=resource_id,
        integration_id=integration_id,
    )
    return {"queued": resource_id}
