from __future__ import annotations

import logging
import time

import openai
from django.conf import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs; 100 is safe
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds


class Embedder:
    """Wraps OpenAI text-embedding-3-small with batching and retry logic."""

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a float vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts. Automatically batches requests.
        Returns list of embedding vectors in the same order as input.
        """
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            embeddings = self._embed_with_retry(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.embeddings.create(
                    model=self._model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except openai.RateLimitError:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (2**attempt)
                    logger.warning("OpenAI rate limit hit, retrying in %.1fs...", wait)
                    time.sleep(wait)
                else:
                    raise
            except openai.APIError as exc:
                logger.error("OpenAI API error: %s", exc)
                raise

        raise RuntimeError("Max retries exceeded for embedding")
