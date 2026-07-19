"""Domain models for academic publications."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Author(BaseModel):
    """An author associated with an academic publication."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(min_length=1)
    orcid: str | None = None


class Publication(BaseModel):
    """A normalized academic publication retrieved from an external provider."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    source: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authors: tuple[Author, ...] = ()
    abstract: str | None = None
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    journal: str | None = None
    doi: str | None = None
    url: HttpUrl | None = None

    @field_validator("doi", mode="before")
    @classmethod
    def normalize_doi(cls, value: object) -> str | None:
        """Normalize DOI values into their canonical identifier form."""
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("DOI must be a string")

        normalized = value.strip().lower()

        if not normalized:
            return None

        prefixes = ("https://doi.org/", "http://doi.org/", "doi:")
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized.removeprefix(prefix)
                break

        if not normalized.startswith("10.") or "/" not in normalized:
            raise ValueError("DOI must use the form '10.xxxx/identifier'")

        return normalized
