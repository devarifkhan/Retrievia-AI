from __future__ import annotations

import base64
import logging

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsOrgAdmin
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"


class NotionOAuthInitiateView(APIView):
    permission_classes = [IsOrgAdmin]

    def get(self, request: Request) -> Response:
        url = (
            f"{NOTION_AUTH_URL}"
            f"?client_id={settings.NOTION_CLIENT_ID}"
            f"&response_type=code"
            f"&owner=user"
            f"&redirect_uri={settings.NOTION_REDIRECT_URI}"
            f"&state={request.user.organization_id}"
        )
        return Response({"oauth_url": url})


class NotionOAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        code = request.query_params.get("code")
        if not code:
            return redirect(f"{settings.FRONTEND_URL}/admin/integrations?error=notion_denied")

        credentials = base64.b64encode(
            f"{settings.NOTION_CLIENT_ID}:{settings.NOTION_CLIENT_SECRET}".encode()
        ).decode()

        response = requests.post(
            NOTION_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.NOTION_REDIRECT_URI,
            },
            headers={"Authorization": f"Basic {credentials}"},
        )
        response.raise_for_status()
        data = response.json()

        integration, _ = Integration.objects.get_or_create(
            organization=request.user.organization,
            source="notion",
        )
        config = {
            "access_token": data["access_token"],
            "workspace_id": data.get("workspace_id"),
            "workspace_name": data.get("workspace_name"),
            "bot_id": data.get("bot_id"),
        }
        integration.set_config(config)
        integration.display_name = f"Notion: {data.get('workspace_name', 'Workspace')}"
        integration.is_active = True
        integration.save()

        return redirect(f"{settings.FRONTEND_URL}/admin/integrations?connected=notion")
