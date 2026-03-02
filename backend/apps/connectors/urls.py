from django.urls import include, path

urlpatterns = [
    path("slack/", include("apps.connectors.slack.webhook_urls")),
    path("gdrive/", include("apps.connectors.google_drive.webhook_urls")),
]
