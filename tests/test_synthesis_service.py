"""Tests for deterministic citation-preserving synthesis."""

import pytest

from scholargraph.domain import Publication
from scholargraph.services import ExtractiveSynthesizer, SynthesisError


def _publication(
    source_id: str,
    *,
    title: str,
    abstract: str | None,
) -> Publication:
    """Create a normalized publication for synthesis tests."""
    return Publication(
        source="openalex",
        source_id=source_id,
        title=title,
        abstract=abstract,
    )


def test_synthesizer_selects_query_relevant_sentences() -> None:
    """Claims should be copied from the most relevant abstract sentences."""
    publication = _publication(
        "W1",
        title="Graph Databases",
        abstract=(
            "Relational systems organize data into tables. "
            "Graph databases represent entities and relationships. "
            "Indexes can improve performance."
        ),
    )

    summary = ExtractiveSynthesizer().synthesize(
        "graph relationships",
        [publication],
    )

    assert summary.claims[0].text == ("Graph databases represent entities and relationships.")
    assert summary.claims[0].text in (publication.abstract or "")
    assert summary.claims[0].citations == ("S1",)
    assert summary.citations[0].publication is publication
    assert summary.generator == "extractive-v1"


def test_synthesizer_preserves_ranked_source_order() -> None:
    """Citation positions should follow the supplied publication ranking."""
    publications = [
        _publication(
            "W2",
            title="First Ranked Work",
            abstract="Graph storage uses nodes and edges.",
        ),
        _publication(
            "W1",
            title="Second Ranked Work",
            abstract="Graph queries traverse relationships.",
        ),
    ]

    summary = ExtractiveSynthesizer().synthesize("graph", publications)

    assert tuple(citation.publication.source_id for citation in summary.citations) == (
        "W2",
        "W1",
    )
    assert tuple(citation.label for citation in summary.citations) == ("S1", "S2")


def test_synthesizer_skips_publications_without_abstracts() -> None:
    """Only publications containing evidence should receive citations."""
    publications = [
        _publication("W1", title="Missing Abstract", abstract=None),
        _publication(
            "W2",
            title="Usable Abstract",
            abstract="Graph systems connect related records.",
        ),
    ]

    summary = ExtractiveSynthesizer().synthesize("graph", publications)

    assert len(summary.citations) == 1
    assert summary.citations[0].publication.source_id == "W2"
    assert summary.citations[0].label == "S1"


def test_synthesizer_aggregates_identical_evidence() -> None:
    """The same extracted sentence should become one multiply cited claim."""
    sentence = "Graph databases represent connected data."
    publications = [
        _publication("W1", title="Work One", abstract=sentence),
        _publication("W2", title="Work Two", abstract=sentence),
    ]

    summary = ExtractiveSynthesizer().synthesize("graph data", publications)

    assert len(summary.claims) == 1
    assert summary.claims[0].text == sentence
    assert summary.claims[0].citations == ("S1", "S2")
    assert len(summary.citations) == 2


def test_synthesizer_limits_number_of_sources() -> None:
    """The configured source cap should limit summary size."""
    publications = [
        _publication(
            f"W{position}",
            title=f"Work {position}",
            abstract=f"Graph evidence from work {position}.",
        )
        for position in range(1, 5)
    ]

    summary = ExtractiveSynthesizer().synthesize(
        "graph",
        publications,
        max_sources=2,
    )

    assert len(summary.citations) == 2
    assert tuple(citation.label for citation in summary.citations) == ("S1", "S2")


def test_synthesizer_strips_query_whitespace() -> None:
    """The validated summary should contain the normalized user query."""
    publication = _publication(
        "W1",
        title="Graph Work",
        abstract="Graph databases model relationships.",
    )

    summary = ExtractiveSynthesizer().synthesize(
        "  graph databases  ",
        [publication],
    )

    assert summary.query == "graph databases"


@pytest.mark.parametrize("query", ["", "   ", "\t"])
def test_synthesizer_rejects_blank_query(query: str) -> None:
    """Synthesis requires a meaningful search query."""
    with pytest.raises(ValueError, match="must not be blank"):
        ExtractiveSynthesizer().synthesize(query, [])


@pytest.mark.parametrize("max_sources", [0, 11])
def test_synthesizer_rejects_invalid_source_limit(max_sources: int) -> None:
    """Source limits should stay within a safe supported range."""
    publication = _publication(
        "W1",
        title="Graph Work",
        abstract="Graph databases model relationships.",
    )

    with pytest.raises(ValueError, match="between 1 and 10"):
        ExtractiveSynthesizer().synthesize(
            "graph",
            [publication],
            max_sources=max_sources,
        )


def test_synthesizer_requires_publications() -> None:
    """A summary cannot be created without retrieved sources."""
    with pytest.raises(SynthesisError, match="At least one publication"):
        ExtractiveSynthesizer().synthesize("graph", [])


def test_synthesizer_requires_abstracts() -> None:
    """Publication metadata alone is insufficient evidence for claims."""
    publication = _publication(
        "W1",
        title="Graph Work",
        abstract=None,
    )

    with pytest.raises(SynthesisError, match="No publication abstracts"):
        ExtractiveSynthesizer().synthesize("graph", [publication])


def test_synthesizer_requires_query_evidence() -> None:
    """Unrelated abstract text must not become a summary claim."""
    publication = _publication(
        "W1",
        title="Unrelated Work",
        abstract="Marine ecosystems contain diverse organisms.",
    )

    with pytest.raises(SynthesisError, match="No abstract evidence matches"):
        ExtractiveSynthesizer().synthesize("graph databases", [publication])
