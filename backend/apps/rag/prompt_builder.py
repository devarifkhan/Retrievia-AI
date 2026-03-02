from __future__ import annotations

from apps.search.retriever import RetrievedChunk

SYSTEM_PROMPT_TEMPLATE = """You are Retrievia, an intelligent knowledge assistant for your organization.
Your job is to answer questions using ONLY the information provided in the context below.

Rules:
1. Answer based solely on the provided context. Do not use outside knowledge.
2. For every fact or claim you make, cite the source inline using [Source N] notation.
3. If the context doesn't contain enough information to answer, say: "I don't have enough information in the indexed sources to answer this."
4. At the end of your response, include a "Sources" section listing each cited source with:
   - Source number
   - Title
   - Author
   - Date
   - URL (if available)
5. Be concise and direct. Use markdown formatting for readability.

Context:
{context}
"""


def build_system_prompt(chunks: list[RetrievedChunk]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        source_label = _format_source_label(i, chunk)
        context_parts.append(f"[Source {i}] {source_label}\n{chunk.content}")

    context = "\n\n---\n\n".join(context_parts)
    return SYSTEM_PROMPT_TEMPLATE.format(context=context)


def build_sources_list(chunks: list[RetrievedChunk]) -> list[dict]:
    """Return structured citation objects to save with the Message."""
    sources = []
    for i, chunk in enumerate(chunks, start=1):
        sources.append({
            "index": i,
            "source": chunk.source,
            "title": chunk.title,
            "author_name": chunk.author_name,
            "author_email": chunk.author_email,
            "created_at": chunk.created_at,
            "source_url": chunk.source_url,
            "source_item_id": chunk.source_item_id,
            "excerpt": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "source_metadata": chunk.source_metadata,
        })
    return sources


def _format_source_label(index: int, chunk: RetrievedChunk) -> str:
    source_map = {
        "slack": f"Slack #{chunk.source_metadata.get('channel_name', 'unknown')}",
        "gdrive": f"Google Drive: {chunk.source_metadata.get('mime_type', 'File')}",
        "notion": "Notion",
        "gmail": "Gmail",
    }
    source_display = source_map.get(chunk.source, chunk.source.title())
    date = chunk.created_at[:10] if chunk.created_at else "unknown date"
    return f"{source_display} | {chunk.title} | by {chunk.author_name} | {date}"
