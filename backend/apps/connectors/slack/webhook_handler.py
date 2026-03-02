from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class SlackEventsView(View):
    """
    Handles Slack Events API webhook payloads.
    Verifies Slack request signature before processing.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        if not self._verify_signature(request):
            return HttpResponse("Unauthorized", status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse("Bad Request", status=400)

        event_type = payload.get("type")

        # Slack URL verification challenge
        if event_type == "url_verification":
            return JsonResponse({"challenge": payload.get("challenge")})

        if event_type == "event_callback":
            self._handle_event(payload)

        return HttpResponse(status=200)

    def _handle_event(self, payload: dict) -> None:
        from .tasks import ingest_slack_event

        event = payload.get("event", {})
        event_type = event.get("type")

        # Only handle new messages and message edits
        if event_type == "message":
            subtype = event.get("subtype")
            if subtype == "message_deleted":
                self._handle_deletion(payload, event)
            elif subtype == "message_changed":
                self._handle_edit(payload, event)
            elif subtype is None:
                # New message
                ingest_slack_event.delay(payload)

    def _handle_deletion(self, payload: dict, event: dict) -> None:
        from apps.ingestion.tasks import soft_delete_document
        from apps.integrations.models import Integration

        channel_id = event.get("channel")
        ts = event.get("deleted_ts") or event.get("previous_message", {}).get("ts")
        if not channel_id or not ts:
            return

        integration = self._get_integration(payload)
        if not integration:
            return

        source_item_id = f"{channel_id}:{ts}"
        soft_delete_document.delay(
            source="slack",
            source_item_id=source_item_id,
            organization_id=str(integration.organization_id),
        )

    def _handle_edit(self, payload: dict, event: dict) -> None:
        from apps.ingestion.tasks import reindex_document
        from apps.integrations.models import Integration

        channel_id = event.get("channel")
        ts = event.get("message", {}).get("ts")
        if not channel_id or not ts:
            return

        integration = self._get_integration(payload)
        if not integration:
            return

        source_item_id = f"{channel_id}:{ts}"
        reindex_document.delay(
            source="slack",
            source_item_id=source_item_id,
            integration_id=str(integration.id),
        )

    def _get_integration(self, payload: dict):
        from apps.integrations.models import Integration

        team_id = payload.get("team_id") or payload.get("team", {}).get("id")
        if not team_id:
            return None
        # S3: Match by team_id in config to prevent cross-org data leakage in multi-tenant setup
        integrations = Integration.objects.filter(source="slack", is_active=True)
        return next(
            (i for i in integrations if i.get_config().get("team_id") == team_id), None
        )

    def _verify_signature(self, request: HttpRequest) -> bool:
        signing_secret = settings.SLACK_SIGNING_SECRET
        if not signing_secret:
            # S2: Fail closed — reject all requests when secret is not configured
            logger.error("SLACK_SIGNING_SECRET not configured — rejecting webhook request")
            return False

        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Reject old messages (replay attack protection)
        try:
            if abs(time.time() - int(timestamp)) > 60 * 5:
                return False
        except (ValueError, TypeError):
            return False

        sig_basestring = f"v0:{timestamp}:{request.body.decode('utf-8')}"
        mac = hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        )
        computed = "v0=" + mac.hexdigest()

        return hmac.compare_digest(computed, signature)
