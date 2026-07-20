"""Search orchestration, publication deduplication, and ranking."""

from __future__ import annotations

import unicodedata
from typing import Protocol

from scholargraph.domain import Publication


class PublicationProvider(Protocol):
    """Interface implemented by academic publication providers."""

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        """Retrieve publications matching a search query."""
        ...


class SearchService:
    """Coordinate retrieval, deduplication, and ranking."""

    def __init__(self, provider: PublicationProvider) -> None:
        self._provider = provider

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        """Retrieve, deduplicate, and rank publications."""
        publications = self._provider.search(
            query,
            limit=limit,
            page=page,
            from_year=from_year,
            to_year=to_year,
        )

        unique_publications = deduplicate_publications(publications)

        return rank_publications(
            unique_publications,
            query=query,
        )


def deduplicate_publications(
    publications: list[Publication],
) -> list[Publication]:
    """Remove duplicate publications while retaining richer metadata."""
    unique_publications: list[Publication] = []

    for publication in publications:
        duplicate_index = _find_duplicate_index(
            unique_publications,
            publication,
        )

        if duplicate_index is None:
            unique_publications.append(publication)
            continue

        existing = unique_publications[duplicate_index]

        if _publication_quality(publication) > _publication_quality(existing):
            unique_publications[duplicate_index] = publication

    return unique_publications


def rank_publications(
    publications: list[Publication],
    *,
    query: str,
) -> list[Publication]:
    """Rank publications using transparent and deterministic criteria."""
    normalized_query = _normalize_text(query)
    query_tokens = set(normalized_query.split())

    def ranking_key(
        publication: Publication,
    ) -> tuple[int, int, float, int, int]:
        normalized_title = _normalize_text(publication.title)
        title_tokens = set(normalized_title.split())

        exact_title_match = int(bool(normalized_query) and normalized_title == normalized_query)

        phrase_match = int(bool(normalized_query) and normalized_query in normalized_title)

        overlap_ratio = (
            len(query_tokens & title_tokens) / len(query_tokens) if query_tokens else 0.0
        )

        return (
            exact_title_match,
            phrase_match,
            overlap_ratio,
            publication.cited_by_count,
            publication.publication_year or 0,
        )

    return sorted(
        publications,
        key=ranking_key,
        reverse=True,
    )


def _find_duplicate_index(
    publications: list[Publication],
    candidate: Publication,
) -> int | None:
    """Return the position of a publication matching the candidate."""
    for index, publication in enumerate(publications):
        if _are_duplicates(publication, candidate):
            return index

    return None


def _are_duplicates(
    first: Publication,
    second: Publication,
) -> bool:
    """Determine whether two publications represent the same work."""
    if first.doi is not None and second.doi is not None:
        return first.doi == second.doi

    if first.publication_year is None or second.publication_year is None:
        return False

    return first.publication_year == second.publication_year and _normalize_text(
        first.title
    ) == _normalize_text(second.title)


def _publication_quality(
    publication: Publication,
) -> tuple[int, int, int, int]:
    """Calculate a deterministic metadata-completeness key."""
    completeness = sum(
        (
            int(publication.doi is not None),
            int(publication.abstract is not None),
            int(publication.journal is not None),
            int(publication.url is not None),
            int(publication.publication_year is not None),
            int(bool(publication.authors)),
        )
    )

    return (
        completeness,
        publication.cited_by_count,
        len(publication.abstract or ""),
        len(publication.authors),
    )


def _normalize_text(value: str) -> str:
    """Normalize text for stable comparisons and token matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()

    alphanumeric = "".join(character if character.isalnum() else " " for character in normalized)

    return " ".join(alphanumeric.split())
