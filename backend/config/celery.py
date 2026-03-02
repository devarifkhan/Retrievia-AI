import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("retrievia")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ─── Periodic task schedules ──────────────────────────────────────────────────

app.conf.beat_schedule = {
    # Google Drive: every 4 hours at minute 0
    "sync-google-drive": {
        "task": "apps.connectors.google_drive.tasks.scheduled_sync_gdrive",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    # Notion: every 4 hours at minute 30 (staggered from Drive)
    "sync-notion": {
        "task": "apps.connectors.notion.tasks.scheduled_sync_notion",
        "schedule": crontab(minute=30, hour="*/4"),
    },
    # Gmail: every 2 hours at minute 15
    "sync-gmail": {
        "task": "apps.connectors.gmail.tasks.scheduled_sync_gmail",
        "schedule": crontab(minute=15, hour="*/2"),
    },
}

app.conf.task_routes = {
    "apps.connectors.slack.tasks.*": {"queue": "sync"},
    "apps.connectors.google_drive.tasks.*": {"queue": "sync"},
    "apps.connectors.notion.tasks.*": {"queue": "sync"},
    "apps.connectors.gmail.tasks.*": {"queue": "sync"},
    "apps.ingestion.tasks.*": {"queue": "ingestion"},
}
