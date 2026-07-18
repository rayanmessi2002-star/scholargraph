"""Command-line interface for ScholarGraph."""

import typer
from rich.console import Console

from scholargraph import __version__

app = typer.Typer(
    name="scholargraph",
    help="Search academic literature and generate verifiable summaries.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.callback()
def main() -> None:
    """ScholarGraph academic search engine."""


@app.command()
def version() -> None:
    """Display the installed ScholarGraph version."""
    console.print(f"ScholarGraph {__version__}")


if __name__ == "__main__":
    app()
