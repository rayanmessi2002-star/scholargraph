# ScholarGraph

ScholarGraph is a command-line academic search engine designed to retrieve, organize, and eventually summarize scientific literature with verifiable citations.

> **Project status:** Early development — version 0.1.0 currently provides the project foundation and a tested command-line interface.

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
- Automated tests with pytest.
- Static type checking with mypy.
- Linting and formatting with Ruff.

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

## Usage

Display the installed version:

```cmd
scholargraph version
```

Display the available commands:

```cmd
scholargraph --help
```

## Quality checks

Run the automated tests:

```cmd
pytest
```

Check the code:

```cmd
ruff check .
ruff format --check .
mypy src tests
```

Apply automatic formatting:

```cmd
ruff format .
```

## Project structure

```text
Scholargraph/
├── docs/
│   └── architecture.md
├── src/
│   └── scholargraph/
│       ├── __init__.py
│       └── cli.py
├── tests/
│   └── test_cli.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Roadmap

- [x] Create the Python project foundation.
- [x] Add a tested command-line interface.
- [ ] Define the publication data model.
- [ ] Integrate the first academic data provider.
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
- Secrets must never be committed to Git.