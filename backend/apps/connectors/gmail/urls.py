from django.urls import path
from apps.connectors.google_drive.oauth import GoogleOAuthCallbackView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings


class GmailOAuthInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from google_auth_oauthlib.flow import Flow

        GMAIL_SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ]
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=f"gmail:{request.user.organization_id}",
        )
        return Response({"oauth_url": url})


urlpatterns = [
    path("oauth/initiate/", GmailOAuthInitiateView.as_view(), name="gmail-oauth-initiate"),
    # Callback is shared with Google Drive
    path("oauth/callback/", GoogleOAuthCallbackView.as_view(), name="gmail-oauth-callback"),
]
