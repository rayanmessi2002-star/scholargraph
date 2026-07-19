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
            help="Maximum number of publications to retrieve.",
        ),
    ] = 5,
) -> None:
    """Search OpenAlex for academic publications."""
    api_key = os.getenv("OPENALEX_API_KEY")

    try:
        with OpenAlexProvider(api_key=api_key) as provider:
            publications = provider.search(query, limit=limit)
    except (OpenAlexProviderError, ValueError) as error:
        error_console.print(f"[bold red]Search failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    if not publications:
        console.print("[yellow]No publications found.[/yellow]")
        return

    _print_publications(publications, query=query)


def _print_publications(
    publications: list[Publication],
    *,
    query: str,
) -> None:
    """Display normalized publications in a readable table."""
    table = Table(
        title=f"OpenAlex results: {query.strip()}",
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
    console.print(f"[dim]{result_count} {result_label} found.[/dim]")


if __name__ == "__main__":
    app()
