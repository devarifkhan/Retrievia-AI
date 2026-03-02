from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Organization, User, UserSourceToken


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "organization", "is_admin", "is_active", "created_at"]
    list_filter = ["is_admin", "is_active", "organization"]
    search_fields = ["email", "username"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Retrievia", {"fields": ("organization", "is_admin", "source_memberships")}),
    )


@admin.register(UserSourceToken)
class UserSourceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "source", "expires_at", "created_at"]
    list_filter = ["source"]
    search_fields = ["user__email"]
