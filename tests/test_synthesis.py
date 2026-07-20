"""Tests for citation-preserving summary domain models."""

import pytest
from pydantic import ValidationError

from scholargraph.domain import (
    Citation,
    CitationSummary,
    Publication,
    SummaryClaim,
)


@pytest.fixture
def publications() -> tuple[Publication, Publication]:
    """Return two traceable publications for summary tests."""
    return (
        Publication(
            source="openalex",
            source_id="W1",
            title="Graph Databases",
            publication_year=2024,
            doi="10.1000/graph",
        ),
        Publication(
            source="openalex",
            source_id="W2",
            title="Graph Query Languages",
            publication_year=2025,
            doi="10.1000/query",
        ),
    )


def test_citation_retains_publication_provenance(
    publications: tuple[Publication, Publication],
) -> None:
    """A citation should retain the complete normalized publication."""
    citation = Citation.from_publication(publications[0], position=1)

    assert citation.label == "S1"
    assert citation.publication.source == "openalex"
    assert citation.publication.source_id == "W1"
    assert citation.publication.doi == "10.1000/graph"


def test_citation_rejects_non_positive_position(
    publications: tuple[Publication, Publication],
) -> None:
    """Citation labels should always use positive one-based positions."""
    with pytest.raises(ValueError, match="greater than zero"):
        Citation.from_publication(publications[0], position=0)


def test_citation_rejects_invalid_label(
    publications: tuple[Publication, Publication],
) -> None:
    """Citation labels should use the stable S<number> format."""
    with pytest.raises(ValidationError):
        Citation(label="source-1", publication=publications[0])


def test_claim_requires_at_least_one_citation() -> None:
    """Every summary claim must reference supporting evidence."""
    with pytest.raises(ValidationError):
        SummaryClaim(
            text="Graph databases use graph structures.",
            citations=(),
        )


def test_claim_rejects_duplicate_citations() -> None:
    """A claim should not repeat a citation label."""
    with pytest.raises(ValidationError, match="must be unique"):
        SummaryClaim(
            text="Graph databases use graph structures.",
            citations=("S1", "S1"),
        )


def test_summary_accepts_complete_citation_graph(
    publications: tuple[Publication, Publication],
) -> None:
    """Every claim should map cleanly to retrieved publications."""
    summary = CitationSummary(
        query="graph databases",
        claims=(
            SummaryClaim(
                text="Graph databases model connected data.",
                citations=("S1",),
            ),
            SummaryClaim(
                text="Specialized query languages traverse relationships.",
                citations=("S1", "S2"),
            ),
        ),
        citations=(
            Citation.from_publication(publications[0], position=1),
            Citation.from_publication(publications[1], position=2),
        ),
        generator="test-synthesizer",
    )

    assert summary.query == "graph databases"
    assert summary.generator == "test-synthesizer"
    assert summary.claims[1].citations == ("S1", "S2")


def test_summary_rejects_duplicate_labels(
    publications: tuple[Publication, Publication],
) -> None:
    """Different sources cannot share the same citation label."""
    with pytest.raises(ValidationError, match="labels must be unique"):
        CitationSummary(
            query="graph databases",
            claims=(
                SummaryClaim(
                    text="A supported claim.",
                    citations=("S1",),
                ),
            ),
            citations=(
                Citation(label="S1", publication=publications[0]),
                Citation(label="S1", publication=publications[1]),
            ),
        )


def test_summary_rejects_unordered_labels(
    publications: tuple[Publication, Publication],
) -> None:
    """Labels should remain contiguous and deterministic."""
    with pytest.raises(ValidationError, match="ordered from S1"):
        CitationSummary(
            query="graph databases",
            claims=(
                SummaryClaim(
                    text="A supported claim.",
                    citations=("S2",),
                ),
            ),
            citations=(
                Citation(
                    label="S2",
                    publication=publications[0],
                ),
            ),
        )


def test_summary_rejects_unknown_claim_citation(
    publications: tuple[Publication, Publication],
) -> None:
    """Claims cannot cite publications absent from the source list."""
    with pytest.raises(ValidationError, match="unknown citations: S2"):
        CitationSummary(
            query="graph databases",
            claims=(
                SummaryClaim(
                    text="An unsupported claim.",
                    citations=("S2",),
                ),
            ),
            citations=(
                Citation.from_publication(
                    publications[0],
                    position=1,
                ),
            ),
        )


def test_summary_rejects_unused_citation(
    publications: tuple[Publication, Publication],
) -> None:
    """The source list should contain only citations used by claims."""
    with pytest.raises(ValidationError, match="unused citations: S2"):
        CitationSummary(
            query="graph databases",
            claims=(
                SummaryClaim(
                    text="A supported claim.",
                    citations=("S1",),
                ),
            ),
            citations=(
                Citation.from_publication(publications[0], position=1),
                Citation.from_publication(publications[1], position=2),
            ),
        )


def test_summary_models_are_immutable(
    publications: tuple[Publication, Publication],
) -> None:
    """Validated synthesis output should not be mutated after creation."""
    claim = SummaryClaim(
        text="A supported claim.",
        citations=("S1",),
    )

    with pytest.raises(ValidationError):
        claim.text = "Changed claim."
