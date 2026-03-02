from django.urls import path
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name="dispatch")
class GDrivePushView(View):
    def post(self, request):
        resource_id = request.headers.get("X-Goog-Resource-ID", "")
        resource_uri = request.headers.get("X-Goog-Resource-URI", "")
        state = request.headers.get("X-Goog-Resource-State", "")

        if state not in ("update", "change", "add"):
            return JsonResponse({"skipped": state}, status=200)

        from apps.integrations.models import Integration
        from apps.connectors.google_drive.tasks import handle_gdrive_push

        integration = Integration.objects.filter(source="gdrive", is_active=True).first()
        if integration:
            handle_gdrive_push.delay(resource_id, resource_uri, str(integration.id))

        return JsonResponse({"received": True}, status=200)


urlpatterns = [
    path("push/", GDrivePushView.as_view(), name="gdrive-webhook-push"),
]
