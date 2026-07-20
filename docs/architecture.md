# ScholarGraph Architecture

## Purpose

ScholarGraph separates academic data retrieval, normalization, deduplication, ranking, synthesis, and export into independent components.

This modular design allows external APIs, ranking strategies, exporters, or language-model providers to be replaced without rewriting the complete application.

## Components

| Component | Responsibility | Status |
|---|---|---|
| CLI | Receive commands, validate options, and display results | Implemented |
| Search service | Coordinate retrieval, deduplication, and ranking | Implemented |
| Provider interface | Define the academic-provider contract | Implemented |
| OpenAlex provider | Retrieve and normalize OpenAlex publications | Implemented |
| Domain models | Represent publications and authors consistently | Implemented |
| Deduplicator | Remove repeated publications safely | Implemented |
| Ranker | Order results using transparent criteria | Implemented |
| Synthesizer | Produce source-grounded summaries | Planned |
| Exporter | Serialize results as JSON, CSV, Markdown, or BibTeX | Implemented |
| API and web interface | Expose ScholarGraph beyond the CLI | Planned |

## Current data flow

1. The user submits a search query through the CLI.
2. The CLI validates option combinations.
3. The OpenAlex provider retrieves publication metadata.
4. Provider-specific responses are converted into domain models.
5. The search service removes duplicate publications.
6. The search service ranks the remaining publications.
7. The CLI displays the processed results in a table or delegates to an exporter.
8. An exporter prints portable output or writes a UTF-8 file.

Future phases will optionally synthesize the processed results before display or export.

## Search service

The `SearchService` depends on a provider interface rather than directly on OpenAlex.

This allows future providers to be introduced without changing the ranking and deduplication algorithms.

### Deduplication

Publications are considered duplicates when:

1. Both provide the same normalized DOI.
2. At least one DOI is unavailable and the normalized title and publication year match.

When duplicates are detected, the publication with the most complete metadata is retained.

Metadata completeness considers:

- DOI availability.
- Abstract availability.
- Journal availability.
- URL availability.
- Publication-year availability.
- Author availability.
- Citation count.
- Abstract length.
- Number of authors.

### Ranking

Ranking is deterministic and uses these criteria in order:

1. Exact normalized title match.
2. Query phrase contained in the title.
3. Query-token overlap.
4. Citation count.
5. Publication year.

Python's stable sorting preserves provider order when all ranking criteria are equal.

Ranking currently applies only to publications returned on the selected page.

## Export system

Exporters depend only on normalized publication domain models. They do not perform searches, network requests, ranking, or deduplication.

The CLI supports five output modes:

1. A Rich terminal table for interactive use.
2. JSON with structured author metadata.
3. CSV with stable columns for data-processing tools.
4. Markdown tables for reports and documentation.
5. BibTeX entries with deterministic, collision-safe citation keys.

Portable formats can be printed to standard output or written as UTF-8 files. File output preserves international author names and keeps serialization independent from the terminal presentation layer.

## Dependency rules

- The CLI handles user interaction but does not perform HTTP requests.
- The search service coordinates application logic.
- Domain models do not depend on external APIs.
- Provider implementations depend on domain models.
- The search service depends on a provider protocol rather than OpenAlex.
- Exporters depend on domain models rather than provider responses.
- The CLI selects output destinations, while exporters own serialization.
- Network calls are replaced with test doubles during automated testing.
- API keys and credentials are loaded from environment variables.
- Ranking must remain transparent and independently testable.
- Future language-model components must not create publication metadata.

## Development phases

- [x] Project foundation and CLI.
- [x] Publication model.
- [x] Academic provider integration.
- [x] Filtering and pagination.
- [x] Ranking and deduplication.
- [ ] Citation-preserving synthesis.
- [x] Export system.
- [ ] REST API and web interface.