from __future__ import annotations

import json
import logging

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.rag.pipeline import RAGPipeline
from .models import Message, Thread
from .serializers import (
    MessageSerializer,
    SendMessageSerializer,
    ThreadDetailSerializer,
    ThreadSerializer,
)

logger = logging.getLogger(__name__)


class ThreadViewSet(ModelViewSet):
    serializer_class = ThreadSerializer
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return Thread.objects.filter(user=self.request.user).prefetch_related("messages")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ThreadDetailSerializer
        return ThreadSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request: Request, pk=None) -> StreamingHttpResponse:
        """
        Stream a RAG response to the user.
        Uses Server-Sent Events (SSE) format.
        """
        thread = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_content = serializer.validated_data["content"]

        # Save user message
        user_message = Message.objects.create(
            thread=thread, role="user", content=user_content
        )

        # Auto-title thread on first message
        if thread.messages.count() == 1:
            thread.auto_title_from_first_message(user_content)

        # Build conversation history for Claude (excluding the message just saved)
        history = [
            {"role": m.role, "content": m.content}
            for m in thread.messages.exclude(id=user_message.id).order_by("created_at")
        ]

        pipeline = RAGPipeline()

        def generate():
            full_response = ""
            try:
                for chunk in pipeline.stream(user_content, request.user, history):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

                sources = pipeline.get_sources()

                # Save assistant message
                Message.objects.create(
                    thread=thread,
                    role="assistant",
                    content=full_response,
                    sources=sources,
                )
                thread.save()  # update updated_at

                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as exc:
                logger.exception("RAG pipeline error for thread %s", thread.id)
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        response = StreamingHttpResponse(
            generate(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    @action(detail=True, methods=["get"], url_path="messages")
    def list_messages(self, request: Request, pk=None) -> Response:
        thread = self.get_object()
        messages = thread.messages.all()
        return Response(MessageSerializer(messages, many=True).data)
