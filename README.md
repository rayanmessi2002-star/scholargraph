# ScholarGraph

ScholarGraph is a command-line academic search engine designed to retrieve, normalize, organize, and eventually summarize scientific literature with verifiable citations.

> **Project status:** Early development — version 0.1.0 provides validated publication models and an OpenAlex-powered academic search command.

## Goals

ScholarGraph aims to:

- Search academic publications from external data providers.
- Normalize publication metadata into a consistent format.
- Filter and rank relevant results.
- Generate source-grounded summaries.
- Preserve traceable citations.
- Export results to formats such as Markdown, JSON, and BibTeX.

## Current functionality

- Installable Python package.
- Command-line interface built with Typer.
- Version command.
- Academic search command with configurable result limits.
- Validated and immutable publication and author domain models.
- DOI normalization and validation.
- OpenAlex keyword-search provider.
- OpenAlex response normalization into internal publication models.
- OpenAlex abstract reconstruction.
- Provider-specific HTTP and response validation errors.
- Automated tests without real network requests.
- Static type checking with mypy.
- Linting and formatting with Ruff.
- Continuous integration with GitHub Actions.

## Requirements

- Python 3.13 or newer.
- Git.

## Development setup

Create and activate a virtual environment on Windows:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Install the project and development dependencies:

```cmd
python -m pip install -e ".[dev]"
```

## Command-line usage

Display the installed version:

```cmd
scholargraph version
```

Display the available commands:

```cmd
scholargraph --help
```

Search OpenAlex for academic publications:

```cmd
scholargraph search "graph databases"
```

Limit the number of results:

```cmd
scholargraph search "machine learning" --limit 3
```

The optional `OPENALEX_API_KEY` environment variable can be used to authenticate requests without exposing credentials in command history.

## OpenAlex provider

The OpenAlex provider can also be used directly from Python:

```python
from scholargraph.providers import OpenAlexProvider

with OpenAlexProvider() as provider:
    publications = provider.search("graph databases", limit=5)

for publication in publications:
    print(publication.title)
```

An optional OpenAlex API key can be supplied without storing it in the source code:

```python
import os

from scholargraph.providers import OpenAlexProvider

with OpenAlexProvider(
    api_key=os.getenv("OPENALEX_API_KEY"),
) as provider:
    publications = provider.search("machine learning", limit=5)
```

Secrets and real API keys must never be committed to the repository.

## Quality checks

Run the automated tests:

```cmd
pytest
```

Check formatting, code quality, and types:

```cmd
ruff check .
ruff format --check .
mypy src tests
```

Apply automatic formatting:

```cmd
ruff format .
```

Run tests with a coverage report:

```cmd
pytest --cov=scholargraph --cov-report=term-missing
```

## Continuous integration

GitHub Actions automatically runs the following checks for every pull request targeting `main`:

- Project installation.
- Ruff linting.
- Ruff formatting verification.
- mypy static type checking.
- pytest tests with coverage reporting.

## Project structure

```text
scholargraph/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   └── architecture.md
├── src/
│   └── scholargraph/
│       ├── domain/
│       │   ├── __init__.py
│       │   └── publication.py
│       ├── providers/
│       │   ├── __init__.py
│       │   └── openalex.py
│       ├── __init__.py
│       └── cli.py
├── tests/
│   ├── test_cli.py
│   ├── test_openalex.py
│   └── test_publication.py
├── .env.example
├── .gitattributes
├── .gitignore
├── pyproject.toml
└── README.md
```

## Roadmap

- [x] Create the Python project foundation.
- [x] Add a tested command-line interface.
- [x] Define the publication data model.
- [x] Integrate the first academic data provider.
- [x] Expose academic search through the CLI.
- [ ] Add search filters and pagination.
- [ ] Add result ranking and deduplication.
- [ ] Add citation-preserving summaries.
- [ ] Add Markdown, JSON, and BibTeX exports.
- [ ] Add an API and web interface.

## Design principles

- Citations must always be traceable to retrieved sources.
- The language model must never act as the source of publication metadata.
- External services must remain replaceable.
- Core functionality must be testable without real network requests.
- Domain models must remain independent from provider-specific responses.
- Secrets must never be committed to Git.