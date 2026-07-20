"""Application services exposed by ScholarGraph."""

from scholargraph.services.search import (
    PublicationProvider,
    SearchService,
    deduplicate_publications,
    rank_publications,
)

__all__ = [
    "PublicationProvider",
    "SearchService",
    "deduplicate_publications",
    "rank_publications",
]
