import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsOrgAdmin

from .models import Integration, SyncLog
from .serializers import IntegrationSerializer, SyncLogSerializer

logger = logging.getLogger(__name__)


class IntegrationViewSet(ReadOnlyModelViewSet):
    serializer_class = IntegrationSerializer
    permission_classes = [IsOrgAdmin]

    def get_queryset(self):
        return Integration.objects.filter(organization=self.request.user.organization)

    @action(detail=True, methods=["post"], url_path="sync")
    def trigger_sync(self, request: Request, pk=None) -> Response:
        integration = self.get_object()
        from apps.connectors.tasks import dispatch_manual_sync

        task = dispatch_manual_sync.delay(str(integration.id))
        return Response(
            {"message": "Sync triggered.", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )


class SyncLogViewSet(ReadOnlyModelViewSet):
    serializer_class = SyncLogSerializer
    permission_classes = [IsOrgAdmin]
    filterset_fields = ["integration", "status"]

    def get_queryset(self):
        return SyncLog.objects.filter(
            integration__organization=self.request.user.organization
        ).select_related("integration")
