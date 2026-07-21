"""Tests for the citation-preserving summary command."""

from __future__ import annotations

from types import TracebackType

import pytest
from typer.testing import CliRunner

from scholargraph.cli import app
from scholargraph.domain import Publication
from scholargraph.providers import OpenAlexProviderError

runner = CliRunner()


class _FakeOpenAlexProvider:
    """Network-free provider used by summary CLI tests."""

    publications: list[Publication] = []
    error: Exception | None = None
    last_api_key: str | None = None
    last_query: str | None = None
    last_limit: int | None = None
    last_page: int | None = None
    last_from_year: int | None = None
    last_to_year: int | None = None
    closed = False

    def __init__(self, api_key: str | None = None) -> None:
        type(self).last_api_key = api_key

    def __enter__(self) -> _FakeOpenAlexProvider:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        type(self).closed = True

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        type(self).last_query = query
        type(self).last_limit = limit
        type(self).last_page = page
        type(self).last_from_year = from_year
        type(self).last_to_year = to_year

        if self.error:
            raise self.error

        return list(self.publications)


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> type[_FakeOpenAlexProvider]:
    """Replace OpenAlex and reset all recorded provider state."""
    _FakeOpenAlexProvider.publications = [
        Publication(
            source="openalex",
            source_id="W1",
            title="Graph Databases",
            abstract="Graph databases represent entities and relationships.",
            publication_year=2024,
            doi="10.1000/graph",
            cited_by_count=50,
        ),
        Publication(
            source="openalex",
            source_id="W2",
            title="Graph Query Languages",
            abstract="Graph query languages navigate graph relationships.",
            publication_year=2025,
            doi="10.1000/query",
            cited_by_count=25,
        ),
    ]
    _FakeOpenAlexProvider.error = None
    _FakeOpenAlexProvider.last_api_key = None
    _FakeOpenAlexProvider.last_query = None
    _FakeOpenAlexProvider.last_limit = None
    _FakeOpenAlexProvider.last_page = None
    _FakeOpenAlexProvider.last_from_year = None
    _FakeOpenAlexProvider.last_to_year = None
    _FakeOpenAlexProvider.closed = False
    monkeypatch.setattr(
        "scholargraph.cli.OpenAlexProvider",
        _FakeOpenAlexProvider,
    )
    return _FakeOpenAlexProvider


def test_summarize_command_displays_claims_and_sources(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Summary output should connect claims to traceable publications."""
    result = runner.invoke(
        app,
        ["summarize", "graph databases"],
    )

    assert result.exit_code == 0, result.output
    assert "Summary: graph databases" in result.output
    assert "Graph databases represent entities" in result.output
    assert "Graph query languages navigate" in result.output
    assert "[S1]" in result.output
    assert "[S2]" in result.output
    assert "Sources" in result.output
    assert "10.1000/graph" in result.output
    assert "Generator: extractive-v1" in result.output
    assert fake_provider.closed is True


def test_summarize_command_forwards_search_options(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Summary retrieval should honor filters and authentication."""
    result = runner.invoke(
        app,
        [
            "summarize",
            "graph databases",
            "--limit",
            "20",
            "--page",
            "2",
            "--from-year",
            "2020",
            "--to-year",
            "2025",
        ],
        env={"OPENALEX_API_KEY": "test-key"},
    )

    assert result.exit_code == 0, result.output
    assert fake_provider.last_query == "graph databases"
    assert fake_provider.last_limit == 20
    assert fake_provider.last_page == 2
    assert fake_provider.last_from_year == 2020
    assert fake_provider.last_to_year == 2025
    assert fake_provider.last_api_key == "test-key"
    assert fake_provider.closed is True


def test_summarize_command_limits_sources(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """The CLI should pass the requested source cap to synthesis."""
    result = runner.invoke(
        app,
        ["summarize", "graph", "--max-sources", "1"],
    )

    assert result.exit_code == 0, result.output
    assert "[S1]" in result.output
    assert "[S2]" not in result.output


def test_summarize_command_handles_empty_results(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """An empty result page should produce a clear successful response."""
    fake_provider.publications = []

    result = runner.invoke(
        app,
        ["summarize", "unknown topic", "--page", "3"],
    )

    assert result.exit_code == 0
    assert "No publications found on page 3." in result.output
    assert fake_provider.closed is True


def test_summarize_command_handles_provider_errors(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Provider failures should produce a non-zero summary result."""
    fake_provider.error = OpenAlexProviderError("OpenAlex search failed")

    result = runner.invoke(app, ["summarize", "graph databases"])

    assert result.exit_code == 1
    assert "Summary failed" in result.output
    assert "OpenAlex search failed" in result.output
    assert fake_provider.closed is True


def test_summarize_command_requires_abstract_evidence(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Metadata without abstracts should never produce claims."""
    fake_provider.publications = [
        Publication(
            source="openalex",
            source_id="W1",
            title="Graph Databases",
        )
    ]

    result = runner.invoke(app, ["summarize", "graph databases"])

    assert result.exit_code == 1
    assert "Summary failed" in result.output
    assert "No publication abstracts" in result.output


def test_summarize_command_requires_relevant_evidence(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Unrelated abstracts should never produce summary claims."""
    fake_provider.publications = [
        Publication(
            source="openalex",
            source_id="W1",
            title="Unrelated Work",
            abstract="Marine ecosystems contain diverse organisms.",
        )
    ]

    result = runner.invoke(app, ["summarize", "graph databases"])

    assert result.exit_code == 1
    assert "No abstract evidence matches" in result.output


@pytest.mark.parametrize("max_sources", [0, 11])
def test_summarize_command_rejects_invalid_source_limit(
    fake_provider: type[_FakeOpenAlexProvider],
    max_sources: int,
) -> None:
    """Typer should reject unsafe source limits before retrieval."""
    result = runner.invoke(
        app,
        ["summarize", "graph", "--max-sources", str(max_sources)],
    )

    assert result.exit_code == 2
    assert fake_provider.last_query is None


def test_summarize_command_rejects_invalid_year_range(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Summary retrieval should reject reversed year filters."""
    result = runner.invoke(
        app,
        [
            "summarize",
            "graph",
            "--from-year",
            "2026",
            "--to-year",
            "2020",
        ],
    )

    assert result.exit_code == 1
    assert "From year must not be greater" in result.output
    assert fake_provider.last_query is None


def test_summarize_command_rejects_deep_paging(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Summary retrieval should respect OpenAlex paging limits."""
    result = runner.invoke(
        app,
        ["summarize", "graph", "--limit", "100", "--page", "101"],
    )

    assert result.exit_code == 1
    assert "first 10,000" in result.output
    assert fake_provider.last_query is None


def test_help_lists_summarize_command() -> None:
    """The root help should advertise the new public command."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "summarize" in result.output
