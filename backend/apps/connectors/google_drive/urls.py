from django.urls import path
from .oauth import GoogleDriveOAuthInitiateView, GoogleOAuthCallbackView

urlpatterns = [
    path("oauth/initiate/", GoogleDriveOAuthInitiateView.as_view(), name="gdrive-oauth-initiate"),
    path("oauth/callback/", GoogleOAuthCallbackView.as_view(), name="google-oauth-callback"),
]
