from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.web import WebClient

from apps.accounts.permissions import IsOrgAdmin
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)

SLACK_SCOPES = [
    "channels:read",
    "channels:history",
    "groups:read",
    "groups:history",
    "users:read",
    "users:read.email",
    "team:read",
    "conversations.connect:read",
]


class SlackOAuthInitiateView(APIView):
    permission_classes = [IsOrgAdmin]

    def get(self, request: Request) -> Response:
        generator = AuthorizeUrlGenerator(
            client_id=settings.SLACK_CLIENT_ID,
            scopes=SLACK_SCOPES,
            redirect_uri=settings.SLACK_REDIRECT_URI,
        )
        url = generator.generate(state=str(request.user.organization_id))
        return Response({"oauth_url": url})


class SlackOAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            logger.error("Slack OAuth error: %s", error)
            return redirect(f"{settings.FRONTEND_URL}/admin/integrations?error=slack_oauth_failed")

        client = WebClient()
        response = client.oauth_v2_access(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=settings.SLACK_REDIRECT_URI,
        )

        bot_token = response["access_token"]
        team = response["team"]

        integration, _ = Integration.objects.get_or_create(
            organization=request.user.organization,
            source="slack",
        )
        config = {
            "bot_token": bot_token,
            "team_id": team["id"],
            "team_name": team["name"],
        }
        integration.set_config(config)
        integration.display_name = f"Slack: {team['name']}"
        integration.is_active = True
        integration.save()

        logger.info("Slack integration saved for org %s", request.user.organization_id)
        return redirect(f"{settings.FRONTEND_URL}/admin/integrations?connected=slack")
