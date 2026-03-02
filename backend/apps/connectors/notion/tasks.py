import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue="sync", bind=True, max_retries=2)
def scheduled_sync_notion(self) -> dict:
    from apps.integrations.models import Integration

    integrations = Integration.objects.filter(source="notion", is_active=True)
    results = []
    for integration in integrations:
        task = full_sync_notion.delay(str(integration.id), triggered_by="scheduled")
        results.append({"integration_id": str(integration.id), "task_id": task.id})
    return {"dispatched": len(results)}


@shared_task(queue="sync", bind=True, max_retries=2)
def full_sync_notion(self, integration_id: str, triggered_by: str = "scheduled") -> dict:
    from apps.integrations.models import Integration, SyncLog
    from .connector import NotionConnector

    integration = Integration.objects.get(id=integration_id)
    sync_log = SyncLog.objects.create(integration=integration, triggered_by=triggered_by)

    try:
        connector = NotionConnector(integration_id, str(integration.organization_id))
        if not connector.authenticate():
            raise RuntimeError("Notion authentication failed")

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
