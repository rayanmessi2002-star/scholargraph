"""Command-line interface for ScholarGraph."""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from scholargraph import __version__
from scholargraph.domain import CitationSummary, Publication
from scholargraph.exporters import ExportFormat, render_publications, write_publications
from scholargraph.providers import OpenAlexProvider, OpenAlexProviderError
from scholargraph.providers.openai_synthesis import (
    OpenAIModelClient,
    OpenAIResponsesTransport,
)
from scholargraph.services import ExtractiveSynthesizer, SearchService, SynthesisError
from scholargraph.services.model_synthesis import ModelAssistedSynthesizer


class SummaryGenerator(StrEnum):
    """Available summary-generation strategies."""

    EXTRACTIVE = "extractive"
    MODEL = "model"


app = typer.Typer(
    name="scholargraph",
    help="Search academic literature and generate verifiable summaries.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
error_console = Console(stderr=True)


@app.callback()
def main() -> None:
    """ScholarGraph academic search engine."""


@app.command()
def version() -> None:
    """Display the installed ScholarGraph version."""
    console.print(f"ScholarGraph {__version__}")


@app.command()
def search(
    query: Annotated[
        str,
        typer.Argument(help="Academic topic or keywords to search for."),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            min=1,
            max=100,
            help="Number of publications to retrieve per page.",
        ),
    ] = 5,
    page: Annotated[
        int,
        typer.Option(
            "--page",
            "-p",
            min=1,
            max=500,
            help="Results page to retrieve.",
        ),
    ] = 1,
    from_year: Annotated[
        int | None,
        typer.Option(
            "--from-year",
            min=1000,
            max=2100,
            help="Include publications from this year onwards.",
        ),
    ] = None,
    to_year: Annotated[
        int | None,
        typer.Option(
            "--to-year",
            min=1000,
            max=2100,
            help="Include publications up to this year.",
        ),
    ] = None,
    output_format: Annotated[
        ExportFormat,
        typer.Option(
            "--format",
            "-f",
            case_sensitive=False,
            help="Output format: table, json, csv, markdown, or bibtex.",
        ),
    ] = ExportFormat.TABLE,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            dir_okay=False,
            resolve_path=True,
            help="Write exported results to this file.",
        ),
    ] = None,
) -> None:
    """Search OpenAlex for academic publications."""
    api_key = os.getenv("OPENALEX_API_KEY")

    try:
        _validate_search_options(
            limit=limit,
            page=page,
            from_year=from_year,
            to_year=to_year,
            output_format=output_format,
            output=output,
        )

        with OpenAlexProvider(api_key=api_key) as provider:
            service = SearchService(provider)

            publications = service.search(
                query,
                limit=limit,
                page=page,
                from_year=from_year,
                to_year=to_year,
            )
    except (OpenAlexProviderError, ValueError) as error:
        error_console.print(f"[bold red]Search failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    if not publications:
        console.print(f"[yellow]No publications found on page {page}.[/yellow]")
        return

    if output_format is ExportFormat.TABLE:
        _print_publications(
            publications,
            query=query,
            page=page,
        )
        return

    try:
        _export_publications(
            publications,
            output_format=output_format,
            output=output,
        )
    except OSError as error:
        error_console.print(f"[bold red]Export failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error


@app.command()
def summarize(
    query: Annotated[
        str,
        typer.Argument(help="Academic topic or keywords to summarize."),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            min=1,
            max=100,
            help="Number of publications to retrieve as evidence.",
        ),
    ] = 10,
    max_sources: Annotated[
        int,
        typer.Option(
            "--max-sources",
            "-s",
            min=1,
            max=10,
            help="Maximum number of publications cited by the summary.",
        ),
    ] = 3,
    page: Annotated[
        int,
        typer.Option(
            "--page",
            "-p",
            min=1,
            max=500,
            help="Results page to use as evidence.",
        ),
    ] = 1,
    from_year: Annotated[
        int | None,
        typer.Option(
            "--from-year",
            min=1000,
            max=2100,
            help="Include publications from this year onwards.",
        ),
    ] = None,
    to_year: Annotated[
        int | None,
        typer.Option(
            "--to-year",
            min=1000,
            max=2100,
            help="Include publications up to this year.",
        ),
    ] = None,
    generator: Annotated[
        SummaryGenerator,
        typer.Option(
            "--generator",
            case_sensitive=False,
            help="Summary generator: extractive or model.",
        ),
    ] = SummaryGenerator.EXTRACTIVE,
) -> None:
    """Create a citation-preserving summary from OpenAlex abstracts."""
    openalex_api_key = os.getenv("OPENALEX_API_KEY")
    openai_api_key: str | None = None
    openai_model: str | None = None

    try:
        if generator is SummaryGenerator.MODEL:
            openai_api_key = _required_environment_variable("OPENAI_API_KEY")
            openai_model = _required_environment_variable("OPENAI_MODEL")

        _validate_result_window(
            limit=limit,
            page=page,
            from_year=from_year,
            to_year=to_year,
        )

        with OpenAlexProvider(api_key=openalex_api_key) as provider:
            search_service = SearchService(provider)
            publications = search_service.search(
                query,
                limit=limit,
                page=page,
                from_year=from_year,
                to_year=to_year,
            )

        if not publications:
            console.print(f"[yellow]No publications found on page {page}.[/yellow]")
            return

        if generator is SummaryGenerator.MODEL:
            assert openai_api_key is not None
            assert openai_model is not None

            transport = OpenAIResponsesTransport.from_api_key(
                api_key=openai_api_key,
            )
            model_client = OpenAIModelClient(
                model=openai_model,
                transport=transport,
            )
            summary = ModelAssistedSynthesizer(
                client=model_client,
            ).synthesize(
                query,
                publications,
                max_sources=max_sources,
            )
        else:
            summary = ExtractiveSynthesizer().synthesize(
                query,
                publications,
                max_sources=max_sources,
            )
    except (
        OpenAlexProviderError,
        RuntimeError,
        SynthesisError,
        ValueError,
    ) as error:
        error_console.print(f"[bold red]Summary failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    _print_summary(summary)


def _required_environment_variable(name: str) -> str:
    """Return a required non-blank environment variable."""
    value = os.getenv(name)

    if not value or not value.strip():
        raise ValueError(f"{name} is required when --generator model is used")

    return value.strip()


def _validate_search_options(
    *,
    limit: int,
    page: int,
    from_year: int | None,
    to_year: int | None,
    output_format: ExportFormat,
    output: Path | None,
) -> None:
    """Validate option combinations that depend on each other."""
    _validate_result_window(
        limit=limit,
        page=page,
        from_year=from_year,
        to_year=to_year,
    )

    if output is not None and output_format is ExportFormat.TABLE:
        raise ValueError("--output requires --format json, csv, markdown, or bibtex")


def _validate_result_window(
    *,
    limit: int,
    page: int,
    from_year: int | None,
    to_year: int | None,
) -> None:
    """Validate pagination and publication-year combinations."""
    if page * limit > 10_000:
        raise ValueError("Page and limit cannot request results beyond the first 10,000")

    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("From year must not be greater than to year")


def _export_publications(
    publications: list[Publication],
    *,
    output_format: ExportFormat,
    output: Path | None,
) -> None:
    """Print an export to standard output or save it to a file."""
    if output is None:
        content = render_publications(
            publications,
            output_format=output_format,
        )
        typer.echo(content, nl=False)
        return

    write_publications(
        publications,
        output_format=output_format,
        destination=output,
    )

    result_count = len(publications)
    result_label = "publication" if result_count == 1 else "publications"
    console.print(
        f"[green]Exported {result_count} {result_label} "
        f"as {output_format.value} to {output}.[/green]"
    )


def _print_publications(
    publications: list[Publication],
    *,
    query: str,
    page: int,
) -> None:
    """Display normalized publications in a readable table."""
    table = Table(
        title=f"OpenAlex results: {query.strip()} — page {page}",
        show_lines=True,
    )

    table.add_column(
        "#",
        justify="right",
        style="cyan",
        no_wrap=True,
    )
    table.add_column("Title", style="bold")
    table.add_column(
        "Year",
        justify="center",
        no_wrap=True,
    )
    table.add_column(
        "Citations",
        justify="right",
        no_wrap=True,
    )
    table.add_column("Authors")
    table.add_column("Journal")
    table.add_column("DOI / URL")

    for position, publication in enumerate(
        publications,
        start=1,
    ):
        authors = ", ".join(author.name for author in publication.authors)
        identifier = publication.doi

        if not identifier and publication.url:
            identifier = str(publication.url)

        table.add_row(
            str(position),
            publication.title,
            str(publication.publication_year or "—"),
            str(publication.cited_by_count),
            authors or "Unknown",
            publication.journal or "—",
            identifier or "—",
        )

    console.print(table)

    result_count = len(publications)
    result_label = "publication" if result_count == 1 else "publications"

    console.print(f"[dim]Page {page} · {result_count} {result_label} found.[/dim]")


def _print_summary(summary: CitationSummary) -> None:
    """Display a citation-preserving summary and its source list."""
    console.print(f"[bold]Summary: {summary.query}[/bold]")
    console.print()

    for claim in summary.claims:
        labels = " ".join(f"[{label}]" for label in claim.citations)
        console.print(
            f"• {claim.text} {labels}",
            markup=False,
        )

    console.print()

    sources = Table(
        title="Sources",
        show_lines=True,
    )
    sources.add_column(
        "Citation",
        style="cyan",
        no_wrap=True,
    )
    sources.add_column(
        "Title",
        style="bold",
    )
    sources.add_column(
        "Year",
        justify="center",
        no_wrap=True,
    )
    sources.add_column("DOI / URL / Source ID")

    for citation in summary.citations:
        publication = citation.publication
        identifier = publication.doi

        if not identifier and publication.url:
            identifier = str(publication.url)

        sources.add_row(
            f"[{citation.label}]",
            publication.title,
            str(publication.publication_year or "—"),
            identifier or publication.source_id,
        )

    console.print(sources)
    console.print(f"[dim]Generator: {summary.generator or 'unknown'}[/dim]")


if __name__ == "__main__":
    app()
