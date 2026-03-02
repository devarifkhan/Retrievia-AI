from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from qdrant_client.models import ScoredPoint

from apps.ingestion.embedder import Embedder
from apps.ingestion.qdrant_client import get_qdrant_client
from .permission_filter import build_qdrant_filter

logger = logging.getLogger(__name__)

TOP_K = 20  # retrieve top-20, then rerank to top-5


@dataclass
class RetrievedChunk:
    chunk_id: str
    score: float
    source: str
    source_item_id: str
    title: str
    content: str
    source_url: str
    author_email: str
    author_name: str
    created_at: str
    source_metadata: dict


class Retriever:
    def __init__(self) -> None:
        self._embedder = Embedder()
        self._collection = settings.QDRANT_COLLECTION_NAME

    def search(self, query: str, user, top_k: int = TOP_K) -> list[RetrievedChunk]:
        """
        Semantic search with permission-aware filtering.
        Returns top_k chunks the user is allowed to see.
        """
        query_vector = self._embedder.embed(query)
        permission_filter = build_qdrant_filter(user)
        client = get_qdrant_client()

        results = client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=permission_filter,
            limit=top_k,
            with_payload=True,
        )

        chunks = []
        for point in results:
            payload = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(point.id),
                    score=point.score,
                    source=payload.get("source", ""),
                    source_item_id=payload.get("source_item_id", ""),
                    title=payload.get("title", ""),
                    content=payload.get("content", ""),
                    source_url=payload.get("source_url", ""),
                    author_email=payload.get("author_email", ""),
                    author_name=payload.get("author_name", ""),
                    created_at=payload.get("created_at", ""),
                    source_metadata=payload.get("source_metadata", {}),
                )
            )

        logger.debug("Search '%s' returned %d chunks for user %s", query, len(chunks), user.id)
        return chunks
