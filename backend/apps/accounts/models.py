import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from encrypted_model_fields.fields import EncryptedTextField


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Custom user extending Django's AbstractUser.
    source_memberships stores the user's IDs in each source system,
    used for building permission filters at query time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
        null=True,
        blank=True,
    )
    # Stores source-level identifiers: {"slack": ["U123","U456"], "notion": ["p_id"]}
    source_memberships = models.JSONField(default=dict, blank=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email


class UserSourceToken(models.Model):
    """
    Stores per-user OAuth tokens for each integrated source.
    Tokens are encrypted at rest.
    """

    SOURCE_CHOICES = [
        ("slack", "Slack"),
        ("gdrive", "Google Drive"),
        ("gmail", "Gmail"),
        ("notion", "Notion"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="source_tokens")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    raw_token_data = models.JSONField(default=dict, blank=True)  # full token response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_source_tokens"
        unique_together = [("user", "source")]

    def __str__(self) -> str:
        return f"{self.user.email} — {self.source}"
