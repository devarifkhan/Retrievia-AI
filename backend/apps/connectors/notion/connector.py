from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError

from apps.connectors.base import BaseConnector
from apps.ingestion.document import Document

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


class NotionConnector(BaseConnector):
    source = "notion"

    def __init__(self, integration_id: str, organization_id: str) -> None:
        super().__init__(integration_id, organization_id)
        self._client: NotionClient | None = None

    def authenticate(self) -> bool:
        from apps.integrations.models import Integration

        integration = Integration.objects.get(id=self.integration_id)
        config = integration.get_config()
        token = config.get("access_token")
        if not token:
            logger.error("No access_token in Notion config")
            return False
        self._client = NotionClient(auth=token)
        try:
            self._client.users.me()
            return True
        except APIResponseError as exc:
            logger.error("Notion auth failed: %s", exc)
            return False

    def fetch_documents(self, cursor: dict | None = None) -> tuple[list[Document], dict]:
        if not self._client:
            self.authenticate()

        documents: list[Document] = []
        start_cursor = cursor.get("start_cursor") if cursor else None

        kwargs: dict[str, Any] = {"page_size": PAGE_SIZE}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        response = self._client.search(**kwargs)
        results = response.get("results", [])

        for item in results:
            if item["object"] == "page":
                doc = self._page_to_document(item)
                if doc:
                    documents.append(doc)
            elif item["object"] == "database":
                # Index database entries too
                db_docs = self._fetch_database_entries(item["id"])
                documents.extend(db_docs)

        next_cursor = {}
        if response.get("has_more") and response.get("next_cursor"):
            next_cursor["start_cursor"] = response["next_cursor"]

        return documents, next_cursor

    def _page_to_document(self, page: dict) -> Document | None:
        page_id = page["id"]
        try:
            content = self._extract_page_content(page_id)
        except APIResponseError as exc:
            logger.warning("Could not extract page %s: %s", page_id, exc)
            return None

        if not content:
            return None

        title = self._get_page_title(page)
        author_email, author_name = self._get_author(page)
        created_at = self._parse_dt(page.get("created_time"))
        updated_at = self._parse_dt(page.get("last_edited_time"))

        # Collect child page IDs for link preservation
        child_ids = self._get_child_page_ids(page_id)
        parent = page.get("parent", {})
        parent_page_id = parent.get("page_id") if parent.get("type") == "page_id" else None
        database_id = parent.get("database_id") if parent.get("type") == "database_id" else None

        return Document(
            source="notion",
            source_item_id=page_id,
            organization_id=self.organization_id,
            title=title,
            content=content,
            source_url=page.get("url", ""),
            author_email=author_email,
            author_name=author_name,
            created_at=created_at,
            updated_at=updated_at,
            allowed_user_ids=[],  # Notion doesn't expose per-user page access via API
            is_private=False,  # Workspace-level access assumed
            source_metadata={
                "parent_page_id": parent_page_id,
                "child_page_ids": child_ids,
                "database_id": database_id,
                "notion_object": "page",
            },
        )

    def _fetch_database_entries(self, database_id: str) -> list[Document]:
        """Fetch all entries from a Notion database."""
        documents = []
        has_more = True
        start_cursor = None

        while has_more:
            kwargs: dict[str, Any] = {"database_id": database_id, "page_size": PAGE_SIZE}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            try:
                response = self._client.databases.query(**kwargs)
            except APIResponseError as exc:
                logger.warning("Could not query database %s: %s", database_id, exc)
                break

            for entry in response.get("results", []):
                doc = self._page_to_document(entry)
                if doc:
                    doc.source_metadata["database_id"] = database_id
                    doc.source_metadata["notion_object"] = "database_entry"
                    documents.append(doc)

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        return documents

    def _extract_page_content(self, page_id: str) -> str:
        """Recursively extract text from all blocks in a page."""
        blocks = self._get_all_blocks(page_id)
        return self._blocks_to_text(blocks)

    def _get_all_blocks(self, block_id: str) -> list[dict]:
        blocks = []
        cursor = None
        while True:
            kwargs: dict[str, Any] = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._client.blocks.children.list(**kwargs)
            blocks.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
        return blocks

    def _blocks_to_text(self, blocks: list[dict], depth: int = 0) -> str:
        lines = []
        indent = "  " * depth

        for block in blocks:
            block_type = block.get("type")
            if not block_type:
                continue

            block_data = block.get(block_type, {})
            rich_text = block_data.get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)

            if text:
                lines.append(f"{indent}{text}")

            # Recursively process children
            if block.get("has_children"):
                try:
                    children = self._get_all_blocks(block["id"])
                    child_text = self._blocks_to_text(children, depth + 1)
                    if child_text:
                        lines.append(child_text)
                except APIResponseError:
                    pass

        return "\n".join(lines)

    def _get_page_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for key in ("title", "Name", "Title"):
            prop = props.get(key, {})
            rich_text = prop.get("title", [])
            if rich_text:
                return "".join(rt.get("plain_text", "") for rt in rich_text)
        return "Untitled"

    def _get_author(self, page: dict) -> tuple[str, str]:
        created_by = page.get("created_by", {})
        if created_by.get("type") == "person":
            email = created_by.get("person", {}).get("email", "unknown@notion")
            name = created_by.get("name", "Unknown")
            return email, name
        return "unknown@notion", "Unknown"

    def _get_child_page_ids(self, page_id: str) -> list[str]:
        try:
            blocks = self._get_all_blocks(page_id)
            return [
                b["id"]
                for b in blocks
                if b.get("type") == "child_page"
            ]
        except APIResponseError:
            return []

    def fetch_document(self, source_item_id: str) -> Document | None:
        if not self._client:
            self.authenticate()
        try:
            page = self._client.pages.retrieve(page_id=source_item_id)
            return self._page_to_document(page)
        except APIResponseError as exc:
            if exc.status == 404:
                return None
            raise

    def get_allowed_user_ids(self, source_item_id: str) -> list[str]:
        # Notion API v1 doesn't expose per-user page permissions
        # All workspace members are assumed to have access
        return []

    @staticmethod
    def _parse_dt(dt_str: str | None) -> datetime:
        if not dt_str:
            return datetime.now(tz=timezone.utc)
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
