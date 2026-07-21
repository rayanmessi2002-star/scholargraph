"""Domain models for citation-preserving academic summaries."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scholargraph.domain.publication import Publication

CitationLabel = Annotated[str, Field(pattern=r"^S[1-9]\d*$")]


class Citation(BaseModel):
    """A traceable publication assigned to a summary citation label."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    label: CitationLabel
    publication: Publication

    @classmethod
    def from_publication(
        cls,
        publication: Publication,
        *,
        position: int,
    ) -> Citation:
        """Create a citation with a deterministic one-based label."""
        if position < 1:
            raise ValueError("Citation position must be greater than zero")

        return cls(
            label=f"S{position}",
            publication=publication,
        )


class SummaryClaim(BaseModel):
    """A single summary statement supported by one or more citations."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    text: str = Field(min_length=1)
    citations: tuple[CitationLabel, ...] = Field(min_length=1)

    @field_validator("citations")
    @classmethod
    def require_unique_citations(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Prevent a claim from repeating the same source label."""
        if len(value) != len(set(value)):
            raise ValueError("Claim citation labels must be unique")

        return value


class CitationSummary(BaseModel):
    """A structured summary whose claims map to retrieved publications."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    query: str = Field(min_length=1)
    claims: tuple[SummaryClaim, ...] = Field(min_length=1)
    citations: tuple[Citation, ...] = Field(min_length=1)
    generator: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_citation_graph(self) -> Self:
        """Ensure citation labels are complete, deterministic, and referenced."""
        labels = tuple(citation.label for citation in self.citations)

        if len(labels) != len(set(labels)):
            raise ValueError("Summary citation labels must be unique")

        expected_labels = tuple(f"S{position}" for position in range(1, len(self.citations) + 1))
        if labels != expected_labels:
            raise ValueError("Summary citation labels must be ordered from S1")

        referenced_labels = {label for claim in self.claims for label in claim.citations}
        available_labels = set(labels)
        unknown_labels = referenced_labels - available_labels

        if unknown_labels:
            unknown = ", ".join(sorted(unknown_labels))
            raise ValueError(f"Claims reference unknown citations: {unknown}")

        unused_labels = available_labels - referenced_labels
        if unused_labels:
            unused = ", ".join(sorted(unused_labels))
            raise ValueError(f"Summary contains unused citations: {unused}")

        return self
