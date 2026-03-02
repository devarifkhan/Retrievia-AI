from django.urls import path
from .oauth import NotionOAuthCallbackView, NotionOAuthInitiateView

urlpatterns = [
    path("oauth/initiate/", NotionOAuthInitiateView.as_view(), name="notion-oauth-initiate"),
    path("oauth/callback/", NotionOAuthCallbackView.as_view(), name="notion-oauth-callback"),
]
