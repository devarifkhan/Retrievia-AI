from .base import *  # noqa: F401, F403

DEBUG = True

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

# Disable throttling in dev
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# Allow all origins in dev
CORS_ALLOW_ALL_ORIGINS = True

# Simplified email backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow weak passwords in dev
AUTH_PASSWORD_VALIDATORS = []  # noqa: F405
