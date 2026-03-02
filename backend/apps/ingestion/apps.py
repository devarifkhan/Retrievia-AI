from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingestion"

    def ready(self):
        # Ensure the Qdrant collection exists when Django starts
        try:
            from .qdrant_client import ensure_collection
            ensure_collection()
        except Exception:
            pass  # Don't crash startup if Qdrant is not yet available
