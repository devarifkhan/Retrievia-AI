from __future__ import annotations

import logging
import uuid

from django.conf import settings
from qdrant_client.models import PointStruct

from .chunker import Chunk, Chunker
from .document import Document
from .embedder import Embedder
from .qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


class Indexer:
    """
    Orchestrates the full ingestion pipeline:
    Document → Chunks → Embeddings → Qdrant upsert
    """

    def __init__(self) -> None:
        self._chunker = Chunker()
        self._embedder = Embedder()
        self._collection = settings.QDRANT_COLLECTION_NAME

    def upsert_document(self, document: Document) -> int:
        """
        Chunk, embed, and upsert a document into Qdrant.
        First soft-deletes any existing chunks for the same source_item_id,
        then inserts fresh chunks (re-index on edit behaviour).
        Returns the number of chunks upserted.
        """
        if document.is_empty():
            logger.warning("Skipping empty document: %s", document.source_item_id)
            return 0

        # Soft-delete stale chunks before re-indexing
        self._soft_delete_by_source_item_id(document.source_item_id, document.organization_id)

        chunks = self._chunker.chunk(document)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_batch(texts)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=self._chunk_to_payload(chunk),
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        client = get_qdrant_client()
        client.upsert(collection_name=self._collection, points=points, wait=True)

        logger.info(
            "Indexed %d chunks for document %s (source=%s)",
            len(points),
            document.source_item_id,
            document.source,
        )
        return len(points)

    def soft_delete(self, source_item_id: str, organization_id: str) -> None:
        """
        Mark all chunks for a source_item_id as deleted.
        They remain in Qdrant but are hidden from search results.
        """
        self._soft_delete_by_source_item_id(source_item_id, organization_id)
        logger.info("Soft-deleted chunks for source_item_id=%s", source_item_id)

    def _soft_delete_by_source_item_id(self, source_item_id: str, organization_id: str) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, SetPayload

        client = get_qdrant_client()
        client.set_payload(
            collection_name=self._collection,
            payload={"is_deleted": True},
            points=Filter(
                must=[
                    FieldCondition(
                        key="source_item_id",
                        match=MatchValue(value=source_item_id),
                    ),
                    FieldCondition(
                        key="organization_id",
                        match=MatchValue(value=organization_id),
                    ),
                ]
            ),
        )

    @staticmethod
    def _chunk_to_payload(chunk: Chunk) -> dict:
        return {
            "document_id": chunk.document_id,
            "source": chunk.source,
            "source_item_id": chunk.source_item_id,
            "organization_id": chunk.organization_id,
            "title": chunk.title,
            "content": chunk.text,  # stored for citation display
            "source_url": chunk.source_url,
            "author_email": chunk.author_email,
            "author_name": chunk.author_name,
            "created_at": chunk.created_at.isoformat(),
            "updated_at": chunk.updated_at.isoformat(),
            "allowed_user_ids": chunk.allowed_user_ids,
            "is_private": chunk.is_private,
            "is_deleted": chunk.is_deleted,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "source_metadata": chunk.source_metadata,
        }
