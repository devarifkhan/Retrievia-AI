from __future__ import annotations

import logging

from django.conf import settings
from django.shortcuts import redirect
from google_auth_oauthlib.flow import Flow
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsOrgAdmin
from apps.integrations.models import Integration

logger = logging.getLogger(__name__)

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _make_flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


class GoogleDriveOAuthInitiateView(APIView):
    permission_classes = [IsOrgAdmin]

    def get(self, request: Request) -> Response:
        flow = _make_flow()
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=f"gdrive:{request.user.organization_id}",
        )
        return Response({"oauth_url": url})


class GoogleOAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state", "")
        source = state.split(":")[0] if ":" in state else "gdrive"

        if source not in ("gdrive", "gmail"):
            source = "gdrive"

        flow = _make_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        token_data = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": list(creds.scopes or []),
        }

        integration, _ = Integration.objects.get_or_create(
            organization=request.user.organization,
            source=source,
        )
        config = integration.get_config()
        config["token"] = token_data
        integration.set_config(config)
        integration.is_active = True
        integration.display_name = f"Google {'Drive' if source == 'gdrive' else 'Gmail'}"
        integration.save()

        return redirect(f"{settings.FRONTEND_URL}/admin/integrations?connected={source}")
