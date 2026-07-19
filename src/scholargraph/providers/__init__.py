"""External academic data providers."""

from scholargraph.providers.openalex import (
    OPENALEX_BASE_URL,
    OpenAlexProvider,
    OpenAlexProviderError,
)

__all__ = [
    "OPENALEX_BASE_URL",
    "OpenAlexProvider",
    "OpenAlexProviderError",
]
