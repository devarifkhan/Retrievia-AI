from django.urls import path
from .webhook_handler import SlackEventsView

urlpatterns = [
    path("events/", SlackEventsView.as_view(), name="slack-webhook-events"),
]
