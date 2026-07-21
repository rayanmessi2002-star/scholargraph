"""Tests for citation-safe model-assisted synthesis."""

from collections.abc import Sequence

import pytest

from scholargraph.domain import Publication, SummaryClaim
from scholargraph.services import SynthesisError
from scholargraph.services.model_synthesis import (
    ModelAssistedSynthesizer,
    ModelSource,
    ModelSynthesisResult,
)


class FakeModelClient:
    """Return deterministic model output without making network requests."""

    def __init__(self, result: ModelSynthesisResult) -> None:
        self.result = result
        self.calls: list[tuple[str, tuple[ModelSource, ...]]] = []

    def generate(
        self,
        *,
        query: str,
        sources: Sequence[ModelSource],
    ) -> ModelSynthesisResult:
        """Record the request and return the configured result."""
        self.calls.append((query, tuple(sources)))
        return self.result


class FailingModelClient:
    """Simulate an unavailable external model provider."""

    def generate(
        self,
        *,
        query: str,
        sources: Sequence[ModelSource],
    ) -> ModelSynthesisResult:
        """Raise the same kind of failure an external client could produce."""
        raise RuntimeError("provider unavailable")


def _publication(
    source_id: str,
    *,
    title: str,
    abstract: str | None,
) -> Publication:
    """Create a normalized publication for model synthesis tests."""
    return Publication(
        source="openalex",
        source_id=source_id,
        title=title,
        abstract=abstract,
    )


def test_model_synthesizer_builds_citation_summary() -> None:
    """Model claims should be attached only to supplied publications."""
    publications = [
        _publication(
            "W1",
            title="Graph Storage",
            abstract="Graph databases store connected entities as nodes and edges.",
        ),
        _publication(
            "W2",
            title="Graph Queries",
            abstract="Graph queries efficiently traverse relationships.",
        ),
    ]
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Graph databases represent connected information.",
                    citations=("S1",),
                ),
                SummaryClaim(
                    text="They also support queries over relationships.",
                    citations=("S1", "S2"),
                ),
            )
        )
    )

    summary = ModelAssistedSynthesizer(client=client).synthesize(
        "graph databases",
        publications,
    )

    assert summary.query == "graph databases"
    assert summary.claims == client.result.claims
    assert tuple(citation.label for citation in summary.citations) == ("S1", "S2")
    assert tuple(citation.publication.source_id for citation in summary.citations) == ("W1", "W2")
    assert summary.generator == "model-assisted-v1"

    assert len(client.calls) == 1
    called_query, called_sources = client.calls[0]
    assert called_query == "graph databases"
    assert tuple(source.label for source in called_sources) == ("S1", "S2")
    assert called_sources[0].title == "Graph Storage"
    assert called_sources[0].abstract == publications[0].abstract


def test_model_synthesizer_sends_only_eligible_ranked_sources() -> None:
    """Missing abstracts should be skipped and the source limit respected."""
    publications = [
        _publication(
            "W0",
            title="Missing Abstract",
            abstract=None,
        ),
        _publication(
            "W1",
            title="First Evidence",
            abstract="Graph databases model connected data.",
        ),
        _publication(
            "W2",
            title="Second Evidence",
            abstract="Graph systems support relationship queries.",
        ),
        _publication(
            "W3",
            title="Excluded Evidence",
            abstract="Graph indexes can improve retrieval.",
        ),
    ]
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Graph systems model and query relationships.",
                    citations=("S1", "S2"),
                ),
            )
        )
    )

    summary = ModelAssistedSynthesizer(client=client).synthesize(
        "graph databases",
        publications,
        max_sources=2,
    )

    _, called_sources = client.calls[0]

    assert tuple(source.label for source in called_sources) == ("S1", "S2")
    assert tuple(source.title for source in called_sources) == (
        "First Evidence",
        "Second Evidence",
    )
    assert tuple(citation.publication.source_id for citation in summary.citations) == ("W1", "W2")


def test_model_synthesizer_renumbers_used_sources_contiguously() -> None:
    """Unused sources should be removed without leaving citation gaps."""
    publications = [
        _publication(
            "W1",
            title="First Work",
            abstract="Graph storage uses nodes.",
        ),
        _publication(
            "W2",
            title="Second Work",
            abstract="Graph queries use paths.",
        ),
        _publication(
            "W3",
            title="Third Work",
            abstract="Graph databases represent relationships.",
        ),
    ]
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Graph databases represent relationships.",
                    citations=("S3",),
                ),
            )
        )
    )

    summary = ModelAssistedSynthesizer(client=client).synthesize(
        "graph databases",
        publications,
    )

    assert summary.claims[0].citations == ("S1",)
    assert len(summary.citations) == 1
    assert summary.citations[0].label == "S1"
    assert summary.citations[0].publication.source_id == "W3"


def test_model_synthesizer_rejects_unknown_citations() -> None:
    """A model must not invent citation labels."""
    publication = _publication(
        "W1",
        title="Graph Work",
        abstract="Graph databases model relationships.",
    )
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Graph databases model relationships.",
                    citations=("S2",),
                ),
            )
        )
    )

    with pytest.raises(
        SynthesisError,
        match="unknown citations",
    ):
        ModelAssistedSynthesizer(client=client).synthesize(
            "graph databases",
            [publication],
        )


def test_model_synthesizer_wraps_client_failures() -> None:
    """External client errors should become application-level errors."""
    publication = _publication(
        "W1",
        title="Graph Work",
        abstract="Graph databases model relationships.",
    )

    with pytest.raises(
        SynthesisError,
        match="Language model synthesis failed",
    ):
        ModelAssistedSynthesizer(client=FailingModelClient()).synthesize(
            "graph databases",
            [publication],
        )


@pytest.mark.parametrize("query", ["", "   ", "\t"])
def test_model_synthesizer_rejects_blank_query(query: str) -> None:
    """Model synthesis requires a meaningful query."""
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Unused claim.",
                    citations=("S1",),
                ),
            )
        )
    )

    with pytest.raises(ValueError, match="must not be blank"):
        ModelAssistedSynthesizer(client=client).synthesize(query, [])


@pytest.mark.parametrize("max_sources", [0, 11])
def test_model_synthesizer_rejects_invalid_source_limit(
    max_sources: int,
) -> None:
    """Model source limits should remain within the supported range."""
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Unused claim.",
                    citations=("S1",),
                ),
            )
        )
    )

    with pytest.raises(ValueError, match="between 1 and 10"):
        ModelAssistedSynthesizer(client=client).synthesize(
            "graph",
            [],
            max_sources=max_sources,
        )


def test_model_synthesizer_requires_publications() -> None:
    """The model must never generate a summary without retrieved sources."""
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Unused claim.",
                    citations=("S1",),
                ),
            )
        )
    )

    with pytest.raises(SynthesisError, match="At least one publication"):
        ModelAssistedSynthesizer(client=client).synthesize(
            "graph databases",
            [],
        )


def test_model_synthesizer_requires_abstracts() -> None:
    """Publication metadata alone is insufficient model evidence."""
    publication = _publication(
        "W1",
        title="Missing Abstract",
        abstract=None,
    )
    client = FakeModelClient(
        ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text="Unused claim.",
                    citations=("S1",),
                ),
            )
        )
    )

    with pytest.raises(SynthesisError, match="No publication abstracts"):
        ModelAssistedSynthesizer(client=client).synthesize(
            "graph databases",
            [publication],
        )
