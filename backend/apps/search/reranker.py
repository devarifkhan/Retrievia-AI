from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

RERANK_TOP_K = 5


class Reranker:
    """
    Cross-encoder reranker using sentence-transformers ms-marco model.
    Falls back to score-based ordering if model not available.
    """

    def __init__(self) -> None:
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Reranker model loaded.")
        except Exception as exc:
            logger.warning("Reranker model not available (%s), using score order.", exc)
            self._model = None

    def rerank(self, query: str, chunks: list, top_k: int = RERANK_TOP_K) -> list:
        """
        Rerank chunks by relevance to query.
        Returns top_k most relevant chunks.
        """
        if not chunks:
            return []

        if self._model is None:
            # Fallback: return top_k by original embedding score
            return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]

        pairs = [(query, chunk.content) for chunk in chunks]
        scores = self._model.predict(pairs)

        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked[:top_k]]
