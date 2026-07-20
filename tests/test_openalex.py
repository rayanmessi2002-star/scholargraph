"""Tests for the OpenAlex academic data provider."""

import httpx
import pytest

from scholargraph.providers import (
    OPENALEX_BASE_URL,
    OpenAlexProvider,
    OpenAlexProviderError,
)


def _sample_openalex_work() -> dict[str, object]:
    """Return a representative OpenAlex work response."""
    return {
        "id": "https://openalex.org/W123456",
        "title": "Machine Learning for Scientific Discovery",
        "authorships": [
            {
                "author": {
                    "display_name": "Ada Lovelace",
                    "orcid": "https://orcid.org/0000-0000-0000-0001",
                }
            }
        ],
        "abstract_inverted_index": {
            "Machine": [0],
            "learning": [1],
            "works": [2],
        },
        "publication_year": 2026,
        "primary_location": {
            "landing_page_url": "https://example.org/publication",
            "source": {
                "display_name": "Journal of Examples",
            },
        },
        "doi": "https://doi.org/10.1000/EXAMPLE",
        "cited_by_count": 42,
    }


def test_search_maps_openalex_response() -> None:
    """Search results should be converted into Publication models."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/works"
        assert request.url.params["search"] == "machine learning"
        assert request.url.params["per_page"] == "2"
        assert request.url.params["page"] == "2"
        assert request.url.params["filter"] == ("publication_year:2020-2026")
        assert request.url.params["api_key"] == "test-key"
        assert "abstract_inverted_index" in request.url.params["select"]
        assert "cited_by_count" in request.url.params["select"]

        return httpx.Response(
            status_code=200,
            json={"results": [_sample_openalex_work()]},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url=OPENALEX_BASE_URL,
    ) as client:
        provider = OpenAlexProvider(api_key="test-key", client=client)
        publications = provider.search(
            "  machine learning  ",
            limit=2,
            page=2,
            from_year=2020,
            to_year=2026,
        )

    assert len(publications) == 1

    publication = publications[0]

    assert publication.source == "openalex"
    assert publication.source_id == "W123456"
    assert publication.title == "Machine Learning for Scientific Discovery"
    assert publication.authors[0].name == "Ada Lovelace"
    assert publication.abstract == "Machine learning works"
    assert publication.publication_year == 2026
    assert publication.journal == "Journal of Examples"
    assert publication.doi == "10.1000/example"
    assert str(publication.url) == "https://example.org/publication"
    assert publication.cited_by_count == 42


@pytest.mark.parametrize(
    ("from_year", "to_year", "expected_filter"),
    [
        (2020, None, "publication_year:>2019"),
        (None, 2026, "publication_year:<2027"),
        (2026, 2026, "publication_year:2026"),
    ],
)
def test_search_builds_supported_year_filters(
    from_year: int | None,
    to_year: int | None,
    expected_filter: str,
) -> None:
    """One-sided and exact-year filters should use OpenAlex syntax."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["filter"] == expected_filter

        return httpx.Response(
            status_code=200,
            json={"results": []},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url=OPENALEX_BASE_URL,
    ) as client:
        provider = OpenAlexProvider(client=client)
        publications = provider.search(
            "graph databases",
            from_year=from_year,
            to_year=to_year,
        )

    assert publications == []


@pytest.mark.parametrize("query", ["", "   ", "\t"])
def test_search_rejects_blank_query(query: str) -> None:
    """Blank search queries should be rejected before an HTTP request."""
    with httpx.Client(base_url=OPENALEX_BASE_URL) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(ValueError, match="must not be blank"):
            provider.search(query)


@pytest.mark.parametrize("limit", [0, 101])
def test_search_rejects_invalid_limit(limit: int) -> None:
    """OpenAlex accepts between 1 and 100 results per page."""
    with httpx.Client(base_url=OPENALEX_BASE_URL) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(ValueError, match="between 1 and 100"):
            provider.search("machine learning", limit=limit)


@pytest.mark.parametrize("page", [0, 501])
def test_search_rejects_invalid_page(page: int) -> None:
    """OpenAlex basic page numbers should remain in the supported range."""
    with httpx.Client(base_url=OPENALEX_BASE_URL) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(ValueError, match="between 1 and 500"):
            provider.search("machine learning", page=page)


def test_search_rejects_results_beyond_basic_paging_limit() -> None:
    """Basic pagination should not request results beyond 10,000."""
    with httpx.Client(base_url=OPENALEX_BASE_URL) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(ValueError, match="first 10,000"):
            provider.search(
                "machine learning",
                limit=100,
                page=101,
            )


@pytest.mark.parametrize(
    ("from_year", "to_year"),
    [
        (999, None),
        (2101, None),
        (None, 999),
        (None, 2101),
        (2026, 2020),
    ],
)
def test_search_rejects_invalid_year_filters(
    from_year: int | None,
    to_year: int | None,
) -> None:
    """Invalid publication-year ranges should be rejected."""
    with httpx.Client(base_url=OPENALEX_BASE_URL) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(ValueError):
            provider.search(
                "machine learning",
                from_year=from_year,
                to_year=to_year,
            )


def test_search_wraps_openalex_http_errors() -> None:
    """HTTP failures should be exposed as provider-specific errors."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=503,
            json={"error": "Service unavailable"},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url=OPENALEX_BASE_URL,
    ) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(OpenAlexProviderError, match="OpenAlex search failed"):
            provider.search("machine learning")


def test_search_wraps_invalid_citation_metadata() -> None:
    """Invalid citation counts should be exposed as provider errors."""

    def handler(request: httpx.Request) -> httpx.Response:
        work = _sample_openalex_work()
        work["cited_by_count"] = -1

        return httpx.Response(
            status_code=200,
            json={"results": [work]},
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url=OPENALEX_BASE_URL,
    ) as client:
        provider = OpenAlexProvider(client=client)

        with pytest.raises(OpenAlexProviderError, match="OpenAlex search failed"):
            provider.search("machine learning")
