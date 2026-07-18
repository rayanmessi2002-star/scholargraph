# ScholarGraph Architecture

## Purpose

ScholarGraph separates academic data retrieval, normalization, ranking, synthesis, and export into independent components.

This modular design allows external APIs or language-model providers to be replaced without rewriting the complete application.

## Planned components

| Component | Responsibility |
|---|---|
| CLI | Receive commands and display results |
| Search service | Coordinate the complete search workflow |
| Provider | Retrieve publications from an external academic API |
| Domain models | Represent publications consistently |
| Ranker | Order results according to relevance |
| Synthesizer | Produce source-grounded summaries |
| Exporter | Save results as Markdown, JSON, or BibTeX |

## Planned data flow

1. The user submits a search query.
2. The provider retrieves publications.
3. Results are converted into internal domain models.
4. Duplicate publications are removed.
5. Results are filtered and ranked.
6. An optional synthesis is generated from the retrieved sources.
7. Results are displayed or exported.

## Dependency rules

- The CLI coordinates user interaction but does not perform HTTP requests directly.
- Domain models do not depend on external APIs.
- Provider implementations are accessed through interfaces.
- Network calls are replaced with test doubles during automated testing.
- API keys and credentials are loaded from environment variables.

## Development phases

1. Project foundation and CLI.
2. Publication model.
3. Academic provider integration.
4. Filtering, pagination, and ranking.
5. Citation-preserving synthesis.
6. Export system.
7. REST API and web interface.