from django.contrib import admin
from .models import Message, Thread


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "created_at", "updated_at"]
    search_fields = ["user__email", "title"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["thread", "role", "created_at"]
    list_filter = ["role"]
