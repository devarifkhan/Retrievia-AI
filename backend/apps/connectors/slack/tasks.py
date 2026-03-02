import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue="sync", bind=True, max_retries=3)
def ingest_slack_event(self, payload: dict) -> dict:
    """
    Process a single Slack event from the webhook.
    Extracts the message, converts to Document, indexes to Qdrant.
    """
    from apps.integrations.models import Integration
    from apps.ingestion.indexer import Indexer
    from .connector import SlackConnector

    try:
        event = payload.get("event", {})
        team_id = payload.get("team_id")
        channel_id = event.get("channel")
        ts = event.get("ts")

        if not all([team_id, channel_id, ts]):
            return {"skipped": "missing required fields"}

        # S3: Find integration by team_id to prevent cross-org data leakage
        integrations = Integration.objects.filter(source="slack", is_active=True)
        integration = next(
            (i for i in integrations if i.get_config().get("team_id") == team_id), None
        )
        if not integration:
            logger.warning("No Slack integration found for team %s", team_id)
            return {"skipped": "no integration found"}

        connector = SlackConnector(str(integration.id), str(integration.organization_id))
        connector.authenticate()

        source_item_id = f"{channel_id}:{ts}"
        document = connector.fetch_document(source_item_id)

        if document:
            chunks = Indexer().upsert_document(document)
            return {"indexed": True, "chunks": chunks, "source_item_id": source_item_id}
        return {"indexed": False, "reason": "document not found"}

    except Exception as exc:
        logger.exception("ingest_slack_event failed")
        raise self.retry(exc=exc, countdown=30)


@shared_task(queue="sync", bind=True, max_retries=2)
def full_sync_slack(self, integration_id: str, triggered_by: str = "manual") -> dict:
    """Full sync of all Slack channels for an integration."""
    from apps.integrations.models import Integration, SyncLog
    from .connector import SlackConnector

    integration = Integration.objects.get(id=integration_id)
    sync_log = SyncLog.objects.create(
        integration=integration, triggered_by=triggered_by
    )

    try:
        connector = SlackConnector(integration_id, str(integration.organization_id))
        if not connector.authenticate():
            raise RuntimeError("Slack authentication failed")

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
        raise self.retry(exc=exc, countdown=120)
