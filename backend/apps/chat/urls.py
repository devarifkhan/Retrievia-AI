from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ThreadViewSet

router = DefaultRouter()
router.register("threads", ThreadViewSet, basename="thread")

urlpatterns = [
    path("", include(router.urls)),
]
