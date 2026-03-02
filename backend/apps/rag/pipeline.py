from __future__ import annotations

import logging
from typing import Iterator

from apps.search.retriever import Retriever
from apps.search.reranker import Reranker
from .claude_client import ClaudeClient
from .prompt_builder import build_system_prompt, build_sources_list

logger = logging.getLogger(__name__)

RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 5


class RAGPipeline:
    """
    End-to-end RAG pipeline:
    query → embed → retrieve → rerank → build prompt → stream LLM response
    """

    def __init__(self) -> None:
        self._retriever = Retriever()
        self._reranker = Reranker()
        self._llm = ClaudeClient()

    def stream(
        self,
        query: str,
        user,
        conversation_history: list[dict],
    ) -> Iterator[str]:
        """
        Stream the RAG response for a user query.
        Yields text chunks as they arrive from Claude.

        After streaming is complete, call get_sources() to retrieve citation data.
        """
        # Step 1: Retrieve
        raw_chunks = self._retriever.search(query, user, top_k=RETRIEVAL_TOP_K)

        if not raw_chunks:
            yield "I don't have any relevant information in the indexed sources to answer this question."
            self._last_sources = []
            return

        # Step 2: Rerank
        ranked_chunks = self._reranker.rerank(query, raw_chunks, top_k=RERANK_TOP_K)

        # Step 3: Build prompt
        system_prompt = build_system_prompt(ranked_chunks)
        self._last_sources = build_sources_list(ranked_chunks)

        # Step 4: Build messages (conversation history + new user message)
        messages = list(conversation_history)  # copy prior turns
        messages.append({"role": "user", "content": query})

        # Step 5: Stream from Claude
        logger.debug(
            "RAG pipeline: %d chunks → reranked to %d → streaming from Claude",
            len(raw_chunks),
            len(ranked_chunks),
        )
        yield from self._llm.stream_completion(system_prompt, messages)

    def get_sources(self) -> list[dict]:
        """Return citation data from the most recent stream() call."""
        return getattr(self, "_last_sources", [])
