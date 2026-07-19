"""Tests for the academic publication domain model."""

import pytest
from pydantic import ValidationError

from scholargraph.domain import Publication


def test_publication_normalizes_metadata() -> None:
    """Publication metadata should be validated and normalized."""
    publication = Publication.model_validate(
        {
            "source": "openalex",
            "source_id": "W123456",
            "title": "  A Scientific Publication  ",
            "authors": [
                {
                    "name": "Ada Lovelace",
                    "orcid": "0000-0000-0000-0001",
                }
            ],
            "abstract": "An example abstract.",
            "publication_year": 2026,
            "journal": "Journal of Examples",
            "doi": "https://doi.org/10.1000/EXAMPLE",
            "url": "https://example.org/publication",
        }
    )

    assert publication.title == "A Scientific Publication"
    assert publication.authors[0].name == "Ada Lovelace"
    assert publication.doi == "10.1000/example"
    assert publication.publication_year == 2026


def test_publication_rejects_blank_title() -> None:
    """A publication must contain a non-empty title."""
    with pytest.raises(ValidationError):
        Publication.model_validate(
            {
                "source": "openalex",
                "source_id": "W123456",
                "title": "   ",
            }
        )


def test_publication_rejects_invalid_doi() -> None:
    """A malformed DOI should be rejected."""
    with pytest.raises(ValidationError, match="DOI must use"):
        Publication.model_validate(
            {
                "source": "openalex",
                "source_id": "W123456",
                "title": "A Scientific Publication",
                "doi": "invalid-doi",
            }
        )
