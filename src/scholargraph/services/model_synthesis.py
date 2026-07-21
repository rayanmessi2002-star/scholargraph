"""Citation-safe model-assisted synthesis."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from scholargraph.domain import (
    Citation,
    CitationSummary,
    Publication,
    SummaryClaim,
)
from scholargraph.services.synthesis import SynthesisError


class ModelSource(BaseModel):
    """Publication evidence supplied to a language model."""

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
    )

    label: str = Field(pattern=r"^S[1-9]\d*$")
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)


class ModelSynthesisResult(BaseModel):
    """Structured claims proposed by a language model."""

    model_config = ConfigDict(frozen=True)

    claims: tuple[SummaryClaim, ...] = Field(min_length=1)


class ModelSynthesisClient(Protocol):
    """Interface implemented by language-model clients."""

    def generate(
        self,
        *,
        query: str,
        sources: Sequence[ModelSource],
    ) -> ModelSynthesisResult:
        """Generate structured claims from supplied evidence."""
        ...


class ModelAssistedSynthesizer:
    """Build a validated citation summary from model-generated claims."""

    generator_name = "model-assisted-v1"

    def __init__(self, client: ModelSynthesisClient) -> None:
        self._client = client

    def synthesize(
        self,
        query: str,
        publications: Sequence[Publication],
        *,
        max_sources: int = 3,
    ) -> CitationSummary:
        """Generate claims while preserving retrieved source integrity."""
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Summary query must not be blank")

        if not 1 <= max_sources <= 10:
            raise ValueError("Maximum sources must be between 1 and 10")

        if not publications:
            raise SynthesisError("At least one publication is required for synthesis")

        eligible_publications = [
            publication
            for publication in publications
            if publication.abstract and publication.abstract.strip()
        ][:max_sources]

        if not eligible_publications:
            raise SynthesisError("No publication abstracts available for synthesis")

        model_sources = tuple(
            ModelSource(
                label=f"S{position}",
                title=publication.title,
                abstract=publication.abstract or "",
            )
            for position, publication in enumerate(
                eligible_publications,
                start=1,
            )
        )

        try:
            result = self._client.generate(
                query=normalized_query,
                sources=model_sources,
            )
        except Exception as error:
            raise SynthesisError("Language model synthesis failed") from error

        publication_by_label = {
            source.label: publication
            for source, publication in zip(
                model_sources,
                eligible_publications,
                strict=True,
            )
        }

        referenced_labels = {label for claim in result.claims for label in claim.citations}

        unknown_labels = referenced_labels - publication_by_label.keys()

        if unknown_labels:
            unknown = ", ".join(sorted(unknown_labels))
            raise SynthesisError(f"Model output references unknown citations: {unknown}")

        used_labels = tuple(
            source.label for source in model_sources if source.label in referenced_labels
        )

        label_mapping = {
            old_label: f"S{position}"
            for position, old_label in enumerate(
                used_labels,
                start=1,
            )
        }

        claims = tuple(
            SummaryClaim(
                text=claim.text,
                citations=tuple(label_mapping[label] for label in claim.citations),
            )
            for claim in result.claims
        )

        citations = tuple(
            Citation.from_publication(
                publication_by_label[old_label],
                position=position,
            )
            for position, old_label in enumerate(
                used_labels,
                start=1,
            )
        )

        return CitationSummary(
            query=normalized_query,
            claims=claims,
            citations=citations,
            generator=self.generator_name,
        )
