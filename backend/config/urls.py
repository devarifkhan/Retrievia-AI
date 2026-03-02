from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import LoginView, LogoutView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    # Health check (used by Docker + load balancers)
    path("api/health/", lambda r: JsonResponse({"status": "ok"}), name="health"),
    # Auth
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    # Integrations (connectors + OAuth + sync)
    path("api/integrations/", include("apps.integrations.urls")),
    # Webhooks (public, signature-verified)
    path("api/webhooks/", include("apps.connectors.urls")),
    # Chat
    path("api/chat/", include("apps.chat.urls")),
]
