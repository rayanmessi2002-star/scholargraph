"""Deterministic synthesis from retrieved publication abstracts."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Protocol

from scholargraph.domain import Citation, CitationSummary, Publication, SummaryClaim

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class SynthesisError(RuntimeError):
    """Raised when a verifiable summary cannot be produced."""


class SummarySynthesizer(Protocol):
    """Interface implemented by citation-preserving synthesizers."""

    def synthesize(
        self,
        query: str,
        publications: Sequence[Publication],
        *,
        max_sources: int = 3,
    ) -> CitationSummary:
        """Create a summary from normalized publication evidence."""
        ...


class ExtractiveSynthesizer:
    """Build a summary using only sentences copied from source abstracts."""

    generator_name = "extractive-v1"

    def synthesize(
        self,
        query: str,
        publications: Sequence[Publication],
        *,
        max_sources: int = 3,
    ) -> CitationSummary:
        """Select relevant abstract sentences and attach traceable citations."""
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Summary query must not be blank")

        if not 1 <= max_sources <= 10:
            raise ValueError("Maximum sources must be between 1 and 10")

        if not publications:
            raise SynthesisError("At least one publication is required for synthesis")

        publications_with_abstracts = [
            publication
            for publication in publications
            if publication.abstract and publication.abstract.strip()
        ]

        if not publications_with_abstracts:
            raise SynthesisError("No publication abstracts available for synthesis")

        citations: list[Citation] = []
        claim_texts: list[str] = []
        claim_citations: list[list[str]] = []
        claim_positions: dict[str, int] = {}

        for publication in publications_with_abstracts:
            sentence = _select_relevant_sentence(
                publication.abstract or "",
                query=normalized_query,
            )

            if sentence is None:
                continue

            citation = Citation.from_publication(
                publication,
                position=len(citations) + 1,
            )
            citations.append(citation)

            normalized_sentence = _normalize_text(sentence)
            existing_position = claim_positions.get(normalized_sentence)

            if existing_position is None:
                claim_positions[normalized_sentence] = len(claim_texts)
                claim_texts.append(sentence)
                claim_citations.append([citation.label])
            else:
                claim_citations[existing_position].append(citation.label)

            if len(citations) == max_sources:
                break

        if not citations:
            raise SynthesisError("No abstract evidence matches the summary query")

        claims = tuple(
            SummaryClaim(
                text=text,
                citations=tuple(labels),
            )
            for text, labels in zip(
                claim_texts,
                claim_citations,
                strict=True,
            )
        )

        return CitationSummary(
            query=normalized_query,
            claims=claims,
            citations=tuple(citations),
            generator=self.generator_name,
        )


def _select_relevant_sentence(
    abstract: str,
    *,
    query: str,
) -> str | None:
    """Return the highest-scoring sentence containing query evidence."""
    normalized_query = _normalize_text(query)
    query_tokens = set(normalized_query.split())
    best_sentence: str | None = None
    best_score: tuple[int, float, int] | None = None

    for sentence in _split_sentences(abstract):
        normalized_sentence = _normalize_text(sentence)
        sentence_tokens = set(normalized_sentence.split())
        overlap = len(query_tokens & sentence_tokens)

        if overlap == 0:
            continue

        score = (
            int(normalized_query in normalized_sentence),
            overlap / len(query_tokens),
            overlap,
        )

        if best_score is None or score > best_score:
            best_sentence = sentence
            best_score = score

    return best_sentence


def _split_sentences(abstract: str) -> list[str]:
    """Split an abstract while preserving each sentence verbatim."""
    return [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(abstract.strip())
        if sentence.strip()
    ]


def _normalize_text(value: str) -> str:
    """Normalize text for deterministic evidence matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    alphanumeric = "".join(character if character.isalnum() else " " for character in normalized)
    return " ".join(alphanumeric.split())
