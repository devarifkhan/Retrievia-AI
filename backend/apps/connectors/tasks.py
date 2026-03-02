import logging

from celery import shared_task
from django.utils import timezone

from apps.integrations.models import Integration, SyncLog

logger = logging.getLogger(__name__)


@shared_task(queue="sync")
def dispatch_manual_sync(integration_id: str) -> dict:
    """
    Manual sync trigger — dispatches to the correct connector task.
    Called from the admin dashboard Sync Now button.
    """
    try:
        integration = Integration.objects.get(id=integration_id)
    except Integration.DoesNotExist:
        logger.error("Integration %s not found", integration_id)
        return {"error": "Integration not found"}

    task_map = {
        "slack": "apps.connectors.slack.tasks.full_sync_slack",
        "gdrive": "apps.connectors.google_drive.tasks.full_sync_gdrive",
        "notion": "apps.connectors.notion.tasks.full_sync_notion",
        "gmail": "apps.connectors.gmail.tasks.full_sync_gmail",
    }

    task_name = task_map.get(integration.source)
    if not task_name:
        return {"error": f"Unknown source: {integration.source}"}

    from celery import current_app

    task = current_app.send_task(
        task_name,
        args=[integration_id],
        kwargs={"triggered_by": "manual"},
        queue="sync",
    )
    return {"task_id": task.id, "source": integration.source}
