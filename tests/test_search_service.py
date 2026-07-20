"""Tests for search orchestration, deduplication, and ranking."""

from scholargraph.domain import Publication
from scholargraph.services import (
    SearchService,
    deduplicate_publications,
    rank_publications,
)


def _publication(
    source_id: str,
    title: str,
    *,
    doi: str | None = None,
    publication_year: int | None = 2024,
    cited_by_count: int = 0,
    abstract: str | None = None,
    journal: str | None = None,
    authors: tuple[str, ...] = (),
    url: str | None = None,
) -> Publication:
    """Create a publication with concise test metadata."""
    data: dict[str, object] = {
        "source": "openalex",
        "source_id": source_id,
        "title": title,
        "publication_year": publication_year,
        "cited_by_count": cited_by_count,
        "authors": [{"name": name} for name in authors],
    }

    if doi is not None:
        data["doi"] = doi

    if abstract is not None:
        data["abstract"] = abstract

    if journal is not None:
        data["journal"] = journal

    if url is not None:
        data["url"] = url

    return Publication.model_validate(data)


class _FakeProvider:
    """Provider test double that records search arguments."""

    def __init__(self, publications: list[Publication]) -> None:
        self._publications = publications
        self.last_query: str | None = None
        self.last_limit: int | None = None
        self.last_page: int | None = None
        self.last_from_year: int | None = None
        self.last_to_year: int | None = None

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        """Return configured publications and record the search."""
        self.last_query = query
        self.last_limit = limit
        self.last_page = page
        self.last_from_year = from_year
        self.last_to_year = to_year

        return list(self._publications)


def test_deduplication_uses_normalized_doi() -> None:
    """Equivalent DOI formats should identify the same publication."""
    sparse = _publication(
        "W1",
        "Graph Databases",
        doi="https://doi.org/10.1000/EXAMPLE",
    )
    complete = _publication(
        "W2",
        "Graph Databases",
        doi="10.1000/example",
        abstract="A complete abstract.",
        journal="Data Journal",
        authors=("Ada Lovelace",),
        url="https://example.org/publication",
        cited_by_count=42,
    )

    result = deduplicate_publications([sparse, complete])

    assert result == [complete]


def test_deduplication_uses_normalized_title_and_year() -> None:
    """Title and year should identify duplicates when a DOI is absent."""
    sparse = _publication(
        "W1",
        "Graph Databases: An Introduction",
        publication_year=2024,
    )
    complete = _publication(
        "W2",
        "graph databases an introduction",
        publication_year=2024,
        abstract="A complete abstract.",
        journal="Data Journal",
    )

    result = deduplicate_publications([sparse, complete])

    assert result == [complete]


def test_deduplication_keeps_same_title_from_different_years() -> None:
    """Different editions or yearly publications must remain separate."""
    first = _publication(
        "W1",
        "Graph Databases",
        publication_year=2023,
    )
    second = _publication(
        "W2",
        "Graph Databases",
        publication_year=2024,
    )

    result = deduplicate_publications([first, second])

    assert result == [first, second]


def test_deduplication_keeps_distinct_dois() -> None:
    """Different DOI identifiers must not be merged."""
    first = _publication(
        "W1",
        "Graph Databases",
        doi="10.1000/first",
    )
    second = _publication(
        "W2",
        "Graph Databases",
        doi="10.1000/second",
    )

    result = deduplicate_publications([first, second])

    assert result == [first, second]


def test_ranking_prioritizes_query_relevance() -> None:
    """Title relevance should be the primary ranking criterion."""
    unrelated = _publication(
        "W1",
        "Relational Storage Systems",
        cited_by_count=10_000,
    )
    relevant = _publication(
        "W2",
        "Graph Database Systems",
        cited_by_count=1,
    )

    result = rank_publications(
        [unrelated, relevant],
        query="graph database",
    )

    assert result == [relevant, unrelated]


def test_ranking_prioritizes_exact_title_match() -> None:
    """An exact title should outrank a phrase match with more citations."""
    phrase_match = _publication(
        "W1",
        "Keyword Search on Graph Databases",
        cited_by_count=1_000,
    )
    exact_match = _publication(
        "W2",
        "Graph Databases",
        cited_by_count=1,
    )

    result = rank_publications(
        [phrase_match, exact_match],
        query="graph databases",
    )

    assert result == [exact_match, phrase_match]


def test_ranking_uses_citations_for_equal_relevance() -> None:
    """Citation count should break equal-relevance ties."""
    less_cited = _publication(
        "W1",
        "Graph Database Alpha",
        cited_by_count=10,
    )
    more_cited = _publication(
        "W2",
        "Graph Database Beta",
        cited_by_count=100,
    )

    result = rank_publications(
        [less_cited, more_cited],
        query="graph database",
    )

    assert result == [more_cited, less_cited]


def test_ranking_uses_publication_year_after_citations() -> None:
    """Newer publications should win remaining ranking ties."""
    older = _publication(
        "W1",
        "Graph Database Alpha",
        publication_year=2020,
        cited_by_count=10,
    )
    newer = _publication(
        "W2",
        "Graph Database Beta",
        publication_year=2025,
        cited_by_count=10,
    )

    result = rank_publications(
        [older, newer],
        query="graph database",
    )

    assert result == [newer, older]


def test_search_service_orchestrates_provider_and_processing() -> None:
    """The service should retrieve, deduplicate, and rank results."""
    duplicate_sparse = _publication(
        "W1",
        "Graph Systems",
        publication_year=2024,
    )
    duplicate_complete = _publication(
        "W2",
        "graph systems",
        publication_year=2024,
        journal="Data Journal",
        cited_by_count=5,
    )
    unrelated = _publication(
        "W3",
        "Relational Theory",
        publication_year=2025,
        cited_by_count=1_000,
    )

    provider = _FakeProvider(
        [
            unrelated,
            duplicate_sparse,
            duplicate_complete,
        ]
    )
    service = SearchService(provider)

    result = service.search(
        "graph systems",
        limit=20,
        page=2,
        from_year=2020,
        to_year=2025,
    )

    assert result == [duplicate_complete, unrelated]
    assert provider.last_query == "graph systems"
    assert provider.last_limit == 20
    assert provider.last_page == 2
    assert provider.last_from_year == 2020
    assert provider.last_to_year == 2025
