"""Tests for publication export formats."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

import pytest
from pydantic import HttpUrl

from scholargraph.domain import Author, Publication
from scholargraph.exporters import (
    ExportFormat,
    render_publications,
    write_publications,
)


@pytest.fixture
def publications() -> list[Publication]:
    """Return representative normalized publications."""
    return [
        Publication(
            source="openalex",
            source_id="W123",
            title="Graph Databases | A Survey",
            authors=(
                Author(name="Ada Lovelace", orcid="0000-0001"),
                Author(name="René Descartes"),
            ),
            abstract="A reproducible survey.",
            publication_year=2025,
            journal="Data & Systems",
            doi="10.1000/graph_data",
            url=HttpUrl("https://example.com/work"),
            cited_by_count=42,
        )
    ]


def test_json_export_preserves_structured_metadata(
    publications: list[Publication],
) -> None:
    """JSON should retain nested authors and normalized metadata."""
    rendered = render_publications(
        publications,
        output_format=ExportFormat.JSON,
    )
    payload = json.loads(rendered)

    assert payload[0]["title"] == "Graph Databases | A Survey"
    assert payload[0]["authors"][1]["name"] == "René Descartes"
    assert payload[0]["doi"] == "10.1000/graph_data"
    assert payload[0]["cited_by_count"] == 42


def test_csv_export_uses_stable_columns(publications: list[Publication]) -> None:
    """CSV should be readable by standard tooling."""
    rendered = render_publications(
        publications,
        output_format=ExportFormat.CSV,
    )
    rows = list(csv.DictReader(StringIO(rendered)))

    assert len(rows) == 1
    assert rows[0]["title"] == "Graph Databases | A Survey"
    assert rows[0]["authors"] == "Ada Lovelace; René Descartes"
    assert rows[0]["cited_by_count"] == "42"


def test_markdown_export_escapes_table_separators(
    publications: list[Publication],
) -> None:
    """Markdown content should not break table columns."""
    rendered = render_publications(
        publications,
        output_format=ExportFormat.MARKDOWN,
    )

    assert "Graph Databases \\| A Survey" in rendered
    assert "| 1 |" in rendered
    assert "| 42 |" in rendered


def test_bibtex_export_creates_traceable_entry(
    publications: list[Publication],
) -> None:
    """BibTeX should include a deterministic key and source identifiers."""
    rendered = render_publications(
        publications,
        output_format=ExportFormat.BIBTEX,
    )

    assert "@article{lovelace2025graph," in rendered
    assert "author = {Ada Lovelace and René Descartes}" in rendered
    assert r"doi = {10.1000/graph\_data}" in rendered


def test_bibtex_export_disambiguates_duplicate_keys(
    publications: list[Publication],
) -> None:
    """Multiple works with the same generated key should remain valid."""
    duplicate_key_publication = publications[0].model_copy(update={"source_id": "W456"})

    rendered = render_publications(
        [publications[0], duplicate_key_publication],
        output_format=ExportFormat.BIBTEX,
    )

    assert "@article{lovelace2025graph," in rendered
    assert "@article{lovelace2025graph2," in rendered


def test_table_format_is_reserved_for_cli(
    publications: list[Publication],
) -> None:
    """The Rich table should not be handled by text exporters."""
    with pytest.raises(ValueError, match="rendered directly by the CLI"):
        render_publications(
            publications,
            output_format=ExportFormat.TABLE,
        )


def test_export_writes_utf8_file(
    publications: list[Publication],
    tmp_path: Path,
) -> None:
    """File exports should preserve Unicode metadata."""
    destination = tmp_path / "results.json"

    write_publications(
        publications,
        output_format=ExportFormat.JSON,
        destination=destination,
    )

    content = destination.read_text(encoding="utf-8")
    assert "René Descartes" in content
