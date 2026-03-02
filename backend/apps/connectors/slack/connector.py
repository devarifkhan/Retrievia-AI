from __future__ import annotations

import logging
from datetime import datetime, timezone

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from apps.connectors.base import BaseConnector
from apps.ingestion.document import Document

logger = logging.getLogger(__name__)

PAGE_SIZE = 200


class SlackConnector(BaseConnector):
    source = "slack"

    def __init__(self, integration_id: str, organization_id: str) -> None:
        super().__init__(integration_id, organization_id)
        self._client: WebClient | None = None
        self._bot_token: str | None = None

    def authenticate(self) -> bool:
        from apps.integrations.models import Integration

        integration = Integration.objects.get(id=self.integration_id)
        config = integration.get_config()
        self._bot_token = config.get("bot_token")
        if not self._bot_token:
            logger.error("No bot_token in Slack integration config")
            return False
        self._client = WebClient(token=self._bot_token)
        try:
            self._client.auth_test()
            return True
        except SlackApiError as exc:
            logger.error("Slack auth failed: %s", exc)
            return False

    def fetch_documents(self, cursor: dict | None = None) -> tuple[list[Document], dict]:
        if not self._client:
            self.authenticate()

        documents: list[Document] = []
        next_cursor: dict = {}

        # Paginate through channels
        channel_cursor = cursor.get("channel_cursor") if cursor else None
        channel_response = self._client.conversations_list(
            types="public_channel,private_channel",
            limit=200,
            cursor=channel_cursor,
        )
        channels = channel_response["channels"]

        for channel in channels:
            channel_docs, _ = self._fetch_channel_messages(channel)
            documents.extend(channel_docs)

        if channel_response.get("response_metadata", {}).get("next_cursor"):
            next_cursor["channel_cursor"] = channel_response["response_metadata"]["next_cursor"]

        return documents, next_cursor

    def _fetch_channel_messages(
        self, channel: dict, oldest: str | None = None
    ) -> tuple[list[Document], dict]:
        documents: list[Document] = []
        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)
        is_private = channel.get("is_private", False)

        # Get channel members for permission mapping
        allowed_user_ids = self._get_channel_member_db_ids(channel_id)

        try:
            history = self._client.conversations_history(
                channel=channel_id,
                limit=PAGE_SIZE,
                oldest=oldest or "0",
            )
        except SlackApiError as exc:
            if exc.response["error"] == "not_in_channel":
                logger.warning("Bot not in channel %s, joining...", channel_name)
                try:
                    self._client.conversations_join(channel=channel_id)
                    history = self._client.conversations_history(
                        channel=channel_id, limit=PAGE_SIZE
                    )
                except SlackApiError:
                    return [], {}
            else:
                logger.error("Error fetching %s: %s", channel_name, exc)
                return [], {}

        for message in history.get("messages", []):
            doc = self._message_to_document(message, channel, allowed_user_ids, is_private)
            if doc:
                documents.append(doc)

        return documents, {}

    def _message_to_document(
        self,
        message: dict,
        channel: dict,
        allowed_user_ids: list[str],
        is_private: bool,
    ) -> Document | None:
        text = message.get("text", "").strip()
        if not text or message.get("subtype") in ("bot_message", "channel_join", "channel_leave"):
            return None

        ts = message.get("ts", "0")
        created_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)

        # Resolve user display name
        author_email, author_name = self._resolve_user(message.get("user", ""))

        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)
        workspace_domain = self._get_workspace_domain()

        return Document(
            source="slack",
            source_item_id=f"{channel_id}:{ts}",
            organization_id=self.organization_id,
            title=f"#{channel_name} — {author_name}",
            content=text,
            source_url=f"https://slack.com/app_redirect?channel={channel_id}&message_ts={ts}",
            author_email=author_email,
            author_name=author_name,
            created_at=created_at,
            updated_at=created_at,
            allowed_user_ids=allowed_user_ids,
            is_private=is_private,
            source_metadata={
                "channel_id": channel_id,
                "channel_name": channel_name,
                "thread_ts": message.get("thread_ts"),
                "message_ts": ts,
                "reactions": len(message.get("reactions", [])),
            },
        )

    def fetch_document(self, source_item_id: str) -> Document | None:
        if not self._client:
            self.authenticate()
        channel_id, ts = source_item_id.split(":", 1)
        try:
            result = self._client.conversations_history(
                channel=channel_id,
                oldest=ts,
                latest=ts,
                inclusive=True,
                limit=1,
            )
            messages = result.get("messages", [])
            if not messages:
                return None
            channel_info = self._client.conversations_info(channel=channel_id)["channel"]
            allowed_user_ids = self._get_channel_member_db_ids(channel_id)
            return self._message_to_document(
                messages[0], channel_info, allowed_user_ids, channel_info.get("is_private", False)
            )
        except SlackApiError:
            return None

    def get_allowed_user_ids(self, source_item_id: str) -> list[str]:
        channel_id = source_item_id.split(":")[0]
        return self._get_channel_member_db_ids(channel_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_channel_member_db_ids(self, channel_id: str) -> list[str]:
        """Return our DB user UUIDs for all members of a Slack channel."""
        from apps.accounts.models import User

        try:
            result = self._client.conversations_members(channel=channel_id, limit=1000)
            slack_user_ids = result.get("members", [])
        except SlackApiError:
            return []

        # Map Slack user IDs → our DB UUIDs via source_memberships
        db_users = User.objects.filter(
            organization_id=self.organization_id,
        )
        matched = []
        for user in db_users:
            slack_ids = user.source_memberships.get("slack", [])
            if any(sid in slack_user_ids for sid in slack_ids):
                matched.append(str(user.id))
        return matched

    def _resolve_user(self, slack_user_id: str) -> tuple[str, str]:
        if not slack_user_id:
            return ("unknown@slack", "Unknown User")
        try:
            info = self._client.users_info(user=slack_user_id)
            profile = info["user"]["profile"]
            return (
                profile.get("email", f"{slack_user_id}@slack"),
                profile.get("real_name", slack_user_id),
            )
        except SlackApiError:
            return (f"{slack_user_id}@slack", slack_user_id)

    def _get_workspace_domain(self) -> str:
        try:
            return self._client.team_info()["team"]["domain"]
        except SlackApiError:
            return "slack"
