from __future__ import annotations

import logging
from typing import Iterator

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_TOKENS = 2048
TEMPERATURE = 0.2  # Low temp for factual, grounded responses


class ClaudeClient:
    """Anthropic Claude API wrapper with streaming support."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    def stream_completion(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> Iterator[str]:
        """
        Stream a response from Claude.
        Yields text deltas as they arrive.

        messages: list of {"role": "user"|"assistant", "content": str}
        """
        with self._client.messages.stream(
            model=self._model,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        """Non-streaming completion. Returns full response text."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
