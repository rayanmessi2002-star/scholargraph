"""Command-line interface for ScholarGraph."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from scholargraph import __version__
from scholargraph.domain import Publication
from scholargraph.providers import OpenAlexProvider, OpenAlexProviderError

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
) -> None:
    """Search OpenAlex for academic publications."""
    api_key = os.getenv("OPENALEX_API_KEY")

    try:
        _validate_search_options(
            limit=limit,
            page=page,
            from_year=from_year,
            to_year=to_year,
        )

        with OpenAlexProvider(api_key=api_key) as provider:
            publications = provider.search(
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

    _print_publications(
        publications,
        query=query,
        page=page,
    )


def _validate_search_options(
    *,
    limit: int,
    page: int,
    from_year: int | None,
    to_year: int | None,
) -> None:
    """Validate option combinations that depend on each other."""
    if page * limit > 10_000:
        raise ValueError("Page and limit cannot request results beyond the first 10,000")

    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("From year must not be greater than to year")


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

    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Year", justify="center", no_wrap=True)
    table.add_column("Authors")
    table.add_column("Journal")
    table.add_column("DOI / URL")

    for position, publication in enumerate(publications, start=1):
        authors = ", ".join(author.name for author in publication.authors)
        identifier = publication.doi

        if not identifier and publication.url:
            identifier = str(publication.url)

        table.add_row(
            str(position),
            publication.title,
            str(publication.publication_year or "—"),
            authors or "Unknown",
            publication.journal or "—",
            identifier or "—",
        )

    console.print(table)

    result_count = len(publications)
    result_label = "publication" if result_count == 1 else "publications"

    console.print(f"[dim]Page {page} · {result_count} {result_label} found.[/dim]")


if __name__ == "__main__":
    app()
