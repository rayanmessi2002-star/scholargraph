"""Application services exposed by ScholarGraph."""

from scholargraph.services.search import (
    PublicationProvider,
    SearchService,
    deduplicate_publications,
    rank_publications,
)
from scholargraph.services.synthesis import (
    ExtractiveSynthesizer,
    SummarySynthesizer,
    SynthesisError,
)

__all__ = [
    "ExtractiveSynthesizer",
    "PublicationProvider",
    "SearchService",
    "SummarySynthesizer",
    "SynthesisError",
    "deduplicate_publications",
    "rank_publications",
]
