from __future__ import annotations

import logging
import threading

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    KeywordIndexParams,
    PayloadSchemaType,
    VectorParams,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client_instance: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Thread-safe singleton Qdrant client."""
    global _client_instance
    if _client_instance is None:
        with _lock:
            if _client_instance is None:
                _client_instance = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY,
                )
                logger.info("Qdrant client initialized: %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
    return _client_instance


def ensure_collection() -> None:
    """
    Create the Qdrant collection if it doesn't exist.
    Also creates payload indexes for fast filtering.
    Call once at startup.
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME
    dim = settings.QDRANT_EMBEDDING_DIM

    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", collection_name, dim)

        # Create payload indexes for permission filtering and soft deletes
        _create_payload_indexes(client, collection_name)
    else:
        logger.debug("Qdrant collection '%s' already exists", collection_name)


def _create_payload_indexes(client: QdrantClient, collection_name: str) -> None:
    """Create keyword indexes on fields used in filters."""
    indexed_fields = [
        ("organization_id", PayloadSchemaType.KEYWORD),
        ("source", PayloadSchemaType.KEYWORD),
        ("is_deleted", PayloadSchemaType.BOOL),
        ("is_private", PayloadSchemaType.BOOL),
        ("allowed_user_ids", PayloadSchemaType.KEYWORD),
        ("source_item_id", PayloadSchemaType.KEYWORD),
        ("document_id", PayloadSchemaType.KEYWORD),
        ("author_email", PayloadSchemaType.KEYWORD),
    ]
    for field_name, schema_type in indexed_fields:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema_type,
            )
            logger.debug("Created payload index on '%s'", field_name)
        except Exception as exc:
            logger.warning("Could not create index on '%s': %s", field_name, exc)
