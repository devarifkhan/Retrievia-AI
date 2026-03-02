from django.urls import path
from .oauth import SlackOAuthCallbackView, SlackOAuthInitiateView

urlpatterns = [
    path("oauth/initiate/", SlackOAuthInitiateView.as_view(), name="slack-oauth-initiate"),
    path("oauth/callback/", SlackOAuthCallbackView.as_view(), name="slack-oauth-callback"),
]
