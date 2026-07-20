"""Tests for search-command export options."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from types import TracebackType

import pytest
from typer.testing import CliRunner

from scholargraph.cli import app
from scholargraph.domain import Author, Publication

runner = CliRunner()


class _FakeOpenAlexProvider:
    """Network-free provider used by export CLI tests."""

    publications: list[Publication] = []
    opened = False

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def __enter__(self) -> _FakeOpenAlexProvider:
        type(self).opened = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        type(self).opened = False

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        return list(self.publications)


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> type[_FakeOpenAlexProvider]:
    """Replace OpenAlex with deterministic publication data."""
    _FakeOpenAlexProvider.publications = [
        Publication(
            source="openalex",
            source_id="W123",
            title="Graph Databases",
            authors=(Author(name="Ada Lovelace"),),
            publication_year=2025,
            journal="Data Journal",
            doi="10.1000/example",
            cited_by_count=42,
        )
    ]
    _FakeOpenAlexProvider.opened = False
    monkeypatch.setattr(
        "scholargraph.cli.OpenAlexProvider",
        _FakeOpenAlexProvider,
    )
    return _FakeOpenAlexProvider


def test_search_can_print_json(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Structured exports should be printable to standard output."""
    result = runner.invoke(
        app,
        ["search", "graph databases", "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload[0]["title"] == "Graph Databases"
    assert payload[0]["cited_by_count"] == 42
    assert fake_provider.opened is False


def test_search_can_write_csv_file(
    fake_provider: type[_FakeOpenAlexProvider],
    tmp_path: Path,
) -> None:
    """The output option should persist the selected export format."""
    destination = tmp_path / "results.csv"

    result = runner.invoke(
        app,
        [
            "search",
            "graph databases",
            "--format",
            "csv",
            "--output",
            str(destination),
        ],
    )

    assert result.exit_code == 0, result.output
    rows = list(csv.DictReader(StringIO(destination.read_text(encoding="utf-8"))))
    assert rows[0]["title"] == "Graph Databases"
    assert "Exported 1 publication as csv" in result.output
    assert fake_provider.opened is False


def test_output_requires_portable_format(
    fake_provider: type[_FakeOpenAlexProvider],
    tmp_path: Path,
) -> None:
    """A Rich table should not be redirected into a plain-text file."""
    destination = tmp_path / "results.txt"

    result = runner.invoke(
        app,
        ["search", "graph databases", "--output", str(destination)],
    )

    assert result.exit_code == 1
    assert "--output requires --format" in result.output
    assert not destination.exists()
    assert fake_provider.opened is False


def test_invalid_export_format_is_rejected(
    fake_provider: type[_FakeOpenAlexProvider],
) -> None:
    """Typer should list and validate supported formats."""
    result = runner.invoke(
        app,
        ["search", "graph databases", "--format", "xml"],
    )

    assert result.exit_code == 2
    assert "Invalid value" in result.output
    assert fake_provider.opened is False
