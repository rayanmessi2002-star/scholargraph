# ScholarGraph

ScholarGraph is a command-line academic search engine designed to retrieve, normalize, deduplicate, rank, and eventually summarize scientific literature with verifiable citations.

> **Project status:** Early development — version 0.1.0 provides OpenAlex-powered academic search, portable exports, and deterministic citation-preserving summaries from retrieved abstracts.

## Goals

ScholarGraph aims to:

- Search academic publications from external data providers.
- Normalize publication metadata into a consistent format.
- Remove duplicate search results.
- Rank publications using transparent criteria.
- Generate source-grounded summaries.
- Preserve traceable citations.
- Export results to JSON, CSV, Markdown, and BibTeX.

## Current functionality

- Installable Python package.
- Command-line interface built with Typer.
- Version command.
- Academic search command.
- Citation-preserving summary command.
- Configurable results per page.
- Page-based result navigation.
- Inclusive publication-year filters.
- Validated and immutable publication and author domain models.
- DOI normalization and validation.
- Citation-count validation.
- Immutable citation, summary-claim, and citation-summary domain models.
- Validation that every summary claim references known publications.
- Deterministic, contiguous citation labels such as `S1` and `S2`.
- Provider-independent synthesizer interface.
- Deterministic extractive synthesis from retrieved abstracts.
- Query-aware selection of verbatim evidence sentences.
- Rejection of synthesis when abstracts or relevant evidence are unavailable.
- Configurable source limits between one and ten publications.
- Summary output with inline labels and a traceable source table.
- OpenAlex keyword-search provider.
- OpenAlex response normalization into internal publication models.
- OpenAlex abstract reconstruction.
- DOI-based publication deduplication.
- Title-and-year deduplication when DOI metadata is unavailable.
- Deterministic publication ranking.
- Citation counts displayed in search results.
- JSON exports with nested author metadata.
- CSV exports with stable columns for spreadsheet and data-processing tools.
- Markdown table exports for reports and documentation.
- BibTeX exports with deterministic, collision-safe citation keys.
- UTF-8 file output that preserves international author names.
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

Limit the number of results per page:

```cmd
scholargraph search "machine learning" --limit 3
```

Filter publications by an inclusive year range:

```cmd
scholargraph search "machine learning" --from-year 2020 --to-year 2024
```

Retrieve a specific results page:

```cmd
scholargraph search "machine learning" --page 2
```

Combine pagination, limits, and publication-year filters:

```cmd
scholargraph search "machine learning" --limit 3 --page 2 --from-year 2020 --to-year 2024
```

Print results as structured JSON:

```cmd
scholargraph search "graph databases" --limit 3 --format json
```

Export results to JSON, CSV, Markdown, or BibTeX files:

```cmd
scholargraph search "graph databases" --limit 10 --format json --output results.json
scholargraph search "graph databases" --limit 10 --format csv --output results.csv
scholargraph search "graph databases" --limit 10 --format markdown --output results.md
scholargraph search "graph databases" --limit 10 --format bibtex --output references.bib
```

The table remains the default output format. The `--output` option requires one of the portable formats selected with `--format`.

Create a deterministic citation-preserving summary from retrieved abstracts:

```cmd
scholargraph summarize "graph databases"
```

Control retrieval, cited sources, pagination, and publication years:

```cmd
scholargraph summarize "graph databases" --limit 10 --max-sources 3
scholargraph summarize "machine learning" --page 2 --from-year 2020 --to-year 2026
```

Each summary claim is copied verbatim from a retrieved abstract and ends with a source label such as `[S1]`. The source table maps every label to its publication title, year, and DOI, URL, or provider identifier.

Basic page-based navigation is limited to the first 10,000 matching OpenAlex results.

The optional `OPENALEX_API_KEY` environment variable can be used to authenticate requests without exposing credentials in command history.

## OpenAlex provider

ScholarGraph retrieves academic metadata from the [OpenAlex API](https://developers.openalex.org/).

The provider can also be used directly from Python:

```python
from scholargraph.providers import OpenAlexProvider

with OpenAlexProvider() as provider:
    publications = provider.search(
        "graph databases",
        limit=5,
        page=1,
        from_year=2020,
        to_year=2026,
    )

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

## Ranking and deduplication

Search results are processed by a provider-independent application service.

Duplicate publications are identified using:

1. A normalized DOI when both publications provide one.
2. A normalized title and publication year when DOI metadata is unavailable.

When duplicates are detected, ScholarGraph retains the publication containing the most complete metadata.

Publications are ranked using the following deterministic criteria:

1. Exact normalized title match.
2. Query phrase contained in the title.
3. Proportion of query words present in the title.
4. Citation count.
5. Publication year.

Ranking and deduplication are currently applied within each retrieved results page. No language model is used for ranking.

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
│       │   ├── publication.py
│       │   └── synthesis.py
│       ├── exporters/
│       │   ├── __init__.py
│       │   └── publication.py
│       ├── providers/
│       │   ├── __init__.py
│       │   └── openalex.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── search.py
│       │   └── synthesis.py
│       ├── __init__.py
│       └── cli.py
├── tests/
│   ├── test_cli.py
│   ├── test_export_cli.py
│   ├── test_exporters.py
│   ├── test_openalex.py
│   ├── test_publication.py
│   ├── test_search_service.py
│   ├── test_summary_cli.py
│   ├── test_synthesis.py
│   └── test_synthesis_service.py
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
- [x] Add search filters and pagination.
- [x] Add result ranking and deduplication.
- [x] Define citation-preserving summary models.
- [x] Add deterministic citation-preserving synthesis.
- [x] Expose citation-preserving summaries through the CLI.
- [ ] Add optional model-assisted synthesis behind the same citation contract.
- [x] Add JSON, CSV, Markdown, and BibTeX exports.
- [ ] Add an API and web interface.

## Design principles

- Citations must always be traceable to retrieved sources.
- The language model must never act as the source of publication metadata.
- Ranking criteria must remain deterministic and explainable.
- External services must remain replaceable.
- Core functionality must be testable without real network requests.
- Domain models must remain independent from provider-specific responses.
- Secrets must never be committed to Git.
