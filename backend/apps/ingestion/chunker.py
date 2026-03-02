from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .document import Document

logger = logging.getLogger(__name__)

# Chunk configuration
CHUNK_SIZE = 1500  # characters (~375 tokens for English text)
CHUNK_OVERLAP = 200  # characters overlap between consecutive chunks
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

MIN_CHUNK_LENGTH = 50  # discard chunks shorter than this


@dataclass
class Chunk:
    """A chunk of text derived from a Document, ready for embedding."""

    # Parent document identity
    document_id: str  # will be set to source_item_id by indexer
    source: str
    source_item_id: str
    organization_id: str

    # Chunk content
    text: str
    chunk_index: int
    total_chunks: int  # filled in after all chunks are known

    # Inherited metadata (copied from Document)
    title: str
    source_url: str
    author_email: str
    author_name: str
    created_at: datetime
    updated_at: datetime
    allowed_user_ids: list[str] = field(default_factory=list)
    is_private: bool = False
    is_deleted: bool = False
    source_metadata: dict = field(default_factory=dict)


class Chunker:
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            length_function=len,
        )

    def chunk(self, document: Document) -> list[Chunk]:
        if document.is_empty():
            logger.warning("Document %s has no content, skipping.", document.source_item_id)
            return []

        raw_chunks = self._splitter.split_text(document.content)
        # Filter empty / tiny chunks
        raw_chunks = [c for c in raw_chunks if len(c.strip()) >= MIN_CHUNK_LENGTH]

        if not raw_chunks:
            logger.warning(
                "Document %s produced no valid chunks.", document.source_item_id
            )
            return []

        chunks = []
        for idx, text in enumerate(raw_chunks):
            chunk = Chunk(
                document_id=document.source_item_id,
                source=document.source,
                source_item_id=document.source_item_id,
                organization_id=document.organization_id,
                text=text.strip(),
                chunk_index=idx,
                total_chunks=len(raw_chunks),
                title=document.title,
                source_url=document.source_url,
                author_email=document.author_email,
                author_name=document.author_name,
                created_at=document.created_at,
                updated_at=document.updated_at,
                allowed_user_ids=document.allowed_user_ids,
                is_private=document.is_private,
                source_metadata=document.source_metadata,
            )
            chunks.append(chunk)

        logger.debug(
            "Chunked document %s into %d chunks", document.source_item_id, len(chunks)
        )
        return chunks
