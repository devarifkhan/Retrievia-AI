import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(queue="ingestion", bind=True, max_retries=3)
def reindex_document(self, source: str, source_item_id: str, integration_id: str) -> dict:
    """
    Re-fetch and re-index a single document.
    Triggered when a source document is edited.
    """
    from apps.connectors.base import BaseConnector
    from apps.integrations.models import Integration

    try:
        integration = Integration.objects.get(id=integration_id)
        connector = _get_connector(integration)
        document = connector.fetch_document(source_item_id)

        if document is None:
            # Document was deleted in source — soft delete our copy
            from .indexer import Indexer

            Indexer().soft_delete(source_item_id, str(integration.organization_id))
            return {"action": "soft_deleted", "source_item_id": source_item_id}

        from .indexer import Indexer

        chunks_count = Indexer().upsert_document(document)
        return {"action": "reindexed", "source_item_id": source_item_id, "chunks": chunks_count}

    except Exception as exc:
        logger.exception("reindex_document failed for %s/%s", source, source_item_id)
        raise self.retry(exc=exc, countdown=60)


@shared_task(queue="ingestion")
def soft_delete_document(source: str, source_item_id: str, organization_id: str) -> dict:
    """
    Soft-delete a document's chunks from Qdrant.
    Triggered when a source document is deleted.
    """
    from .indexer import Indexer

    Indexer().soft_delete(source_item_id, organization_id)
    return {"action": "soft_deleted", "source": source, "source_item_id": source_item_id}


def _get_connector(integration):
    from apps.connectors.google_drive.connector import GoogleDriveConnector
    from apps.connectors.gmail.connector import GmailConnector
    from apps.connectors.notion.connector import NotionConnector
    from apps.connectors.slack.connector import SlackConnector

    connector_map = {
        "slack": SlackConnector,
        "gdrive": GoogleDriveConnector,
        "gmail": GmailConnector,
        "notion": NotionConnector,
    }
    cls = connector_map[integration.source]
    return cls(str(integration.id), str(integration.organization_id))
