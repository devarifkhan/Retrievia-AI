from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IntegrationViewSet, SyncLogViewSet

router = DefaultRouter()
router.register("", IntegrationViewSet, basename="integration")
router.register("sync-logs", SyncLogViewSet, basename="sync-log")

urlpatterns = [
    path("", include(router.urls)),
    # OAuth flows — delegated to each connector's url module
    path("slack/", include("apps.connectors.slack.urls")),
    path("google/", include("apps.connectors.google_drive.urls")),
    path("notion/", include("apps.connectors.notion.urls")),
    path("gmail/", include("apps.connectors.gmail.urls")),
]
