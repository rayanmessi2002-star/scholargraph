"""Tests for the ScholarGraph command-line interface."""

from __future__ import annotations

from types import TracebackType
from typing import ClassVar, Self

import pytest
from typer.testing import CliRunner

from scholargraph.cli import app
from scholargraph.domain import Author, Publication
from scholargraph.providers import OpenAlexProviderError

runner = CliRunner()


class _FakeOpenAlexProvider:
    """Controllable OpenAlex replacement used by CLI tests."""

    publications: ClassVar[list[Publication]] = []
    error: ClassVar[Exception | None] = None
    last_api_key: ClassVar[str | None] = None
    last_query: ClassVar[str | None] = None
    last_limit: ClassVar[int | None] = None
    last_page: ClassVar[int | None] = None
    last_from_year: ClassVar[int | None] = None
    last_to_year: ClassVar[int | None] = None
    closed: ClassVar[bool] = False

    def __init__(self, api_key: str | None = None) -> None:
        type(self).last_api_key = api_key

    def __enter__(self) -> Self:
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
def fake_openalex_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> type[_FakeOpenAlexProvider]:
    """Replace the real network provider and reset its recorded state."""
    _FakeOpenAlexProvider.publications = []
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


def test_version_command() -> None:
    """The version command should display the installed version."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "ScholarGraph 0.1.0" in result.stdout


def test_search_command_displays_publications(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Search should display normalized and filtered OpenAlex results."""
    fake_openalex_provider.publications = [
        Publication(
            source="openalex",
            source_id="W123456",
            title="Graph Databases",
            authors=(Author(name="Ada Lovelace"),),
            publication_year=2025,
            journal="Data Journal",
            doi="10.1000/example",
        )
    ]

    result = runner.invoke(
        app,
        [
            "search",
            "graph databases",
            "--limit",
            "1",
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
    assert "Graph Databases" in result.output
    assert "Ada Lovelace" in result.output
    assert "2025" in result.output
    assert "Page 2" in result.output
    assert "1 publication found." in result.output
    assert fake_openalex_provider.last_query == "graph databases"
    assert fake_openalex_provider.last_limit == 1
    assert fake_openalex_provider.last_page == 2
    assert fake_openalex_provider.last_from_year == 2020
    assert fake_openalex_provider.last_to_year == 2025
    assert fake_openalex_provider.last_api_key == "test-key"
    assert fake_openalex_provider.closed is True


def test_search_command_handles_empty_results(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Search should explain when a page contains no publications."""
    result = runner.invoke(
        app,
        ["search", "unknown topic", "--page", "3"],
    )

    assert result.exit_code == 0
    assert "No publications found on page 3." in result.output
    assert fake_openalex_provider.closed is True


def test_search_command_handles_provider_errors(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Provider failures should produce a clear non-zero CLI result."""
    fake_openalex_provider.error = OpenAlexProviderError("OpenAlex search failed")

    result = runner.invoke(app, ["search", "graph databases"])

    assert result.exit_code == 1
    assert "Search failed" in result.output
    assert "OpenAlex search failed" in result.output
    assert fake_openalex_provider.closed is True


def test_search_command_rejects_invalid_limit(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Typer should reject limits outside the supported range."""
    result = runner.invoke(
        app,
        ["search", "graph databases", "--limit", "0"],
    )

    assert result.exit_code == 2
    assert fake_openalex_provider.last_query is None


def test_search_command_rejects_invalid_page(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Typer should reject page numbers outside the supported range."""
    result = runner.invoke(
        app,
        ["search", "graph databases", "--page", "0"],
    )

    assert result.exit_code == 2
    assert fake_openalex_provider.last_query is None


def test_search_command_rejects_invalid_year_range(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """The first publication year must not exceed the final year."""
    result = runner.invoke(
        app,
        [
            "search",
            "graph databases",
            "--from-year",
            "2026",
            "--to-year",
            "2020",
        ],
    )

    assert result.exit_code == 1
    assert "From year must not be greater than to year" in result.output
    assert fake_openalex_provider.last_query is None


def test_search_command_rejects_deep_basic_paging(
    fake_openalex_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Basic paging should not exceed OpenAlex's 10,000-result limit."""
    result = runner.invoke(
        app,
        [
            "search",
            "graph databases",
            "--limit",
            "100",
            "--page",
            "101",
        ],
    )

    assert result.exit_code == 1
    assert "first 10,000" in result.output
    assert fake_openalex_provider.last_query is None
