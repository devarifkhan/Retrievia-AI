from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import UserSourceToken
    from apps.ingestion.document import Document

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Abstract base for all source connectors.
    Each connector implements data fetching for one integration source.
    """

    source: str  # must be set on subclass: "slack"|"gdrive"|"gmail"|"notion"

    def __init__(self, integration_id: str, organization_id: str) -> None:
        self.integration_id = integration_id
        self.organization_id = organization_id

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Verify credentials are valid and refresh if needed.
        Returns True if authenticated successfully.
        """
        ...

    @abstractmethod
    def fetch_documents(self, cursor: dict | None = None) -> tuple[list[Document], dict]:
        """
        Fetch documents from the source, starting from cursor (for incremental sync).
        Returns (documents, next_cursor).
        next_cursor is an opaque dict — pass it back on the next call.
        """
        ...

    @abstractmethod
    def fetch_document(self, source_item_id: str) -> Document | None:
        """
        Fetch a single document by its source-native ID.
        Used for re-indexing on edit events.
        Returns None if document was deleted.
        """
        ...

    @abstractmethod
    def get_allowed_user_ids(self, source_item_id: str) -> list[str]:
        """
        Return list of user UUIDs (from our DB) who have access to this item.
        Used to populate the allowed_user_ids payload field in Qdrant.
        An empty list means public to the whole organization.
        """
        ...

    def run_full_sync(self) -> int:
        """
        Convenience method: paginate through all documents and yield them.
        Calls fetch_documents repeatedly until cursor is exhausted.
        Returns total document count processed.
        """
        from apps.ingestion.indexer import Indexer

        indexer = Indexer()
        cursor = None
        total = 0

        while True:
            documents, next_cursor = self.fetch_documents(cursor=cursor)
            logger.info(
                "Connector %s fetched %d documents (cursor=%s)",
                self.source,
                len(documents),
                cursor,
            )

            for doc in documents:
                try:
                    indexer.upsert_document(doc)
                    total += 1
                except Exception:
                    logger.exception("Failed to index document %s", doc.source_item_id)

            if not next_cursor:
                break
            cursor = next_cursor

        return total
