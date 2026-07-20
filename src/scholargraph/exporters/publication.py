"""Render normalized publications into portable export formats."""

from __future__ import annotations

import csv
import json
import unicodedata
from collections.abc import Callable, Sequence
from enum import StrEnum
from io import StringIO
from pathlib import Path

from scholargraph.domain import Publication


class ExportFormat(StrEnum):
    """Output formats supported by the search command."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    BIBTEX = "bibtex"


def render_publications(
    publications: Sequence[Publication],
    *,
    output_format: ExportFormat,
) -> str:
    """Serialize publications using a machine- or human-readable format."""
    renderers: dict[ExportFormat, Callable[[Sequence[Publication]], str]] = {
        ExportFormat.JSON: _render_json,
        ExportFormat.CSV: _render_csv,
        ExportFormat.MARKDOWN: _render_markdown,
        ExportFormat.BIBTEX: _render_bibtex,
    }

    if output_format is ExportFormat.TABLE:
        raise ValueError("The table format is rendered directly by the CLI")

    return renderers[output_format](publications)


def write_publications(
    publications: Sequence[Publication],
    *,
    output_format: ExportFormat,
    destination: Path,
) -> None:
    """Write serialized publications to a UTF-8 text file."""
    content = render_publications(
        publications,
        output_format=output_format,
    )
    destination.write_text(content, encoding="utf-8", newline="\n")


def _render_json(publications: Sequence[Publication]) -> str:
    records = [_publication_record(publication) for publication in publications]
    return json.dumps(records, ensure_ascii=False, indent=2) + "\n"


def _render_csv(publications: Sequence[Publication]) -> str:
    fieldnames = (
        "source",
        "source_id",
        "title",
        "authors",
        "publication_year",
        "journal",
        "doi",
        "url",
        "cited_by_count",
        "abstract",
    )
    stream = StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        lineterminator="\n",
    )
    writer.writeheader()

    for publication in publications:
        writer.writerow(
            {
                "source": publication.source,
                "source_id": publication.source_id,
                "title": publication.title,
                "authors": "; ".join(author.name for author in publication.authors),
                "publication_year": publication.publication_year,
                "journal": publication.journal,
                "doi": publication.doi,
                "url": str(publication.url) if publication.url else None,
                "cited_by_count": publication.cited_by_count,
                "abstract": publication.abstract,
            }
        )

    return stream.getvalue()


def _render_markdown(publications: Sequence[Publication]) -> str:
    lines = [
        "| # | Title | Year | Citations | Authors | Journal | DOI / URL |",
        "|---:|---|:---:|---:|---|---|---|",
    ]

    for position, publication in enumerate(publications, start=1):
        authors = ", ".join(author.name for author in publication.authors) or "Unknown"
        identifier = publication.doi or (str(publication.url) if publication.url else "—")
        values = (
            str(position),
            publication.title,
            str(publication.publication_year or "—"),
            str(publication.cited_by_count),
            authors,
            publication.journal or "—",
            identifier,
        )
        cells = (_escape_markdown_cell(value) for value in values)
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def _render_bibtex(publications: Sequence[Publication]) -> str:
    entries: list[str] = []
    key_occurrences: dict[str, int] = {}

    for publication in publications:
        base_key = _bibtex_key(publication)
        occurrence = key_occurrences.get(base_key, 0) + 1
        key_occurrences[base_key] = occurrence
        key = base_key if occurrence == 1 else f"{base_key}{occurrence}"

        fields: list[tuple[str, str]] = [("title", publication.title)]

        if publication.authors:
            fields.append(
                (
                    "author",
                    " and ".join(author.name for author in publication.authors),
                )
            )

        if publication.publication_year is not None:
            fields.append(("year", str(publication.publication_year)))

        if publication.journal:
            fields.append(("journal", publication.journal))

        if publication.doi:
            fields.append(("doi", publication.doi))

        if publication.url:
            fields.append(("url", str(publication.url)))

        entry_type = "article" if publication.journal else "misc"
        rendered_fields = ",\n".join(
            f"  {name} = {{{_escape_bibtex(value)}}}" for name, value in fields
        )
        entries.append(f"@{entry_type}{{{key},\n{rendered_fields}\n}}")

    return "\n\n".join(entries) + ("\n" if entries else "")


def _publication_record(publication: Publication) -> dict[str, object]:
    return {
        "source": publication.source,
        "source_id": publication.source_id,
        "title": publication.title,
        "authors": [
            {
                "name": author.name,
                "orcid": author.orcid,
            }
            for author in publication.authors
        ],
        "abstract": publication.abstract,
        "publication_year": publication.publication_year,
        "journal": publication.journal,
        "doi": publication.doi,
        "url": str(publication.url) if publication.url else None,
        "cited_by_count": publication.cited_by_count,
    }


def _escape_markdown_cell(value: str) -> str:
    compact = " ".join(value.split())
    return compact.replace("\\", "\\\\").replace("|", "\\|")


def _bibtex_key(publication: Publication) -> str:
    author_name = publication.authors[0].name if publication.authors else "unknown"
    author_token = author_name.rsplit(maxsplit=1)[-1]
    title_token = next(
        (token for token in _ascii_tokens(publication.title) if len(token) >= 3),
        "work",
    )
    year = str(publication.publication_year or "nd")
    author = "".join(_ascii_tokens(author_token)) or "unknown"
    return f"{author}{year}{title_token}"


def _ascii_tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    return [
        token
        for token in "".join(
            character if character.isalnum() else " " for character in ascii_value
        ).split()
        if token
    ]


def _escape_bibtex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
    }
    return "".join(replacements.get(character, character) for character in value)
