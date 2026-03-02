from rest_framework import serializers
from .models import Message, Thread


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "sources", "created_at"]
        read_only_fields = ["id", "created_at"]


class ThreadSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = ["id", "title", "last_message", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_last_message(self, obj: Thread) -> str | None:
        last = obj.messages.last()
        return last.content[:100] if last else None


class ThreadDetailSerializer(ThreadSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ThreadSerializer.Meta):
        fields = ThreadSerializer.Meta.fields + ["messages"]


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=4000)
