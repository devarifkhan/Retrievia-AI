from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Document:
    """
    Unified representation of a document from any source connector.
    This is the canonical data transfer object between connectors and the ingestion pipeline.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    source: str  # "slack" | "gdrive" | "gmail" | "notion"
    source_item_id: str  # original ID in the source system
    organization_id: str  # UUID string

    # ── Content ───────────────────────────────────────────────────────────────
    title: str
    content: str  # full extracted text

    # ── Provenance ────────────────────────────────────────────────────────────
    source_url: str
    author_email: str
    author_name: str
    created_at: datetime
    updated_at: datetime

    # ── Access Control ────────────────────────────────────────────────────────
    # Empty list = accessible to all org members (public channel, shared doc, etc.)
    allowed_user_ids: list[str] = field(default_factory=list)
    is_private: bool = False

    # ── Source-specific metadata ──────────────────────────────────────────────
    source_metadata: dict = field(default_factory=dict)
    # Slack:       channel_name, channel_id, thread_ts, message_ts
    # Google Drive: folder_path, mime_type, is_ocr
    # Notion:      parent_page_id, child_page_ids, database_id
    # Gmail:       label_names, has_attachments, attachment_names, thread_id

    def is_empty(self) -> bool:
        return not self.content or not self.content.strip()

    def word_count(self) -> int:
        return len(self.content.split()) if self.content else 0
