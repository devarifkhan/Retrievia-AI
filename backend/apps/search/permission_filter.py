from __future__ import annotations

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)


def build_qdrant_filter(user) -> Filter:
    """
    Build a Qdrant filter that:
    1. Scopes to the user's organization
    2. Excludes soft-deleted chunks
    3. Only returns chunks the user has access to:
       - is_private=False (public to whole org), OR
       - allowed_user_ids contains this user's UUID
    """
    return Filter(
        must=[
            FieldCondition(
                key="organization_id",
                match=MatchValue(value=str(user.organization_id)),
            ),
            FieldCondition(
                key="is_deleted",
                match=MatchValue(value=False),
            ),
        ],
        should=[
            FieldCondition(
                key="is_private",
                match=MatchValue(value=False),
            ),
            FieldCondition(
                key="allowed_user_ids",
                match=MatchAny(any=[str(user.id)]),
            ),
        ],
        minimum_should_match=1,
    )
