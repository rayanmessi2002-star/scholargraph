"""OpenAlex API provider."""

from __future__ import annotations

from types import TracebackType

import httpx
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from scholargraph import __version__
from scholargraph.domain import Author, Publication

OPENALEX_BASE_URL = "https://api.openalex.org"

_OPENALEX_FIELDS = (
    "id,title,authorships,abstract_inverted_index,publication_year,primary_location,doi"
)


class OpenAlexProviderError(RuntimeError):
    """Raised when an OpenAlex request or response cannot be processed."""


class _OpenAlexAuthor(BaseModel):
    """Author information returned by OpenAlex."""

    display_name: str | None = None
    orcid: str | None = None


class _OpenAlexAuthorship(BaseModel):
    """Authorship information returned by OpenAlex."""

    author: _OpenAlexAuthor


class _OpenAlexSource(BaseModel):
    """Publication source returned by OpenAlex."""

    display_name: str | None = None


class _OpenAlexLocation(BaseModel):
    """Primary publication location returned by OpenAlex."""

    landing_page_url: HttpUrl | None = None
    source: _OpenAlexSource | None = None


class _OpenAlexWork(BaseModel):
    """Relevant fields from an OpenAlex work."""

    id: str
    title: str | None = None
    authorships: list[_OpenAlexAuthorship] = Field(default_factory=list)
    abstract_inverted_index: dict[str, list[int]] | None = None
    publication_year: int | None = None
    primary_location: _OpenAlexLocation | None = None
    doi: str | None = None


class _OpenAlexResponse(BaseModel):
    """Relevant fields from an OpenAlex search response."""

    results: list[_OpenAlexWork] = Field(default_factory=list)


class OpenAlexProvider:
    """Retrieve and normalize academic publications from OpenAlex."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=OPENALEX_BASE_URL,
            timeout=timeout,
            headers={"User-Agent": f"ScholarGraph/{__version__}"},
        )

    def __enter__(self) -> OpenAlexProvider:
        """Enter the provider context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close provider-owned resources when leaving the context."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client when it was created by this provider."""
        if self._owns_client:
            self._client.close()

    def search(self, query: str, *, limit: int = 10) -> list[Publication]:
        """Search OpenAlex and return normalized publications."""
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Search query must not be blank")

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        params: dict[str, str | int] = {
            "search": normalized_query,
            "per_page": limit,
            "select": _OPENALEX_FIELDS,
        }

        if self._api_key:
            params["api_key"] = self._api_key

        try:
            response = self._client.get("/works", params=params)
            response.raise_for_status()
            payload = _OpenAlexResponse.model_validate(response.json())

            publications = [
                self._to_publication(work)
                for work in payload.results
                if work.title and work.title.strip()
            ]
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise OpenAlexProviderError("OpenAlex search failed") from error

        return publications

    @staticmethod
    def _to_publication(work: _OpenAlexWork) -> Publication:
        """Convert an OpenAlex work into a ScholarGraph publication."""
        authors = tuple(
            Author(name=authorship.author.display_name, orcid=authorship.author.orcid)
            for authorship in work.authorships
            if authorship.author.display_name
        )

        abstract = OpenAlexProvider._reconstruct_abstract(work.abstract_inverted_index)

        journal = None
        url = None

        if work.primary_location:
            url = work.primary_location.landing_page_url

            if work.primary_location.source:
                journal = work.primary_location.source.display_name

        return Publication(
            source="openalex",
            source_id=work.id.rsplit("/", maxsplit=1)[-1],
            title=work.title or "",
            authors=authors,
            abstract=abstract,
            publication_year=work.publication_year,
            journal=journal,
            doi=work.doi,
            url=url,
        )

    @staticmethod
    def _reconstruct_abstract(
        inverted_index: dict[str, list[int]] | None,
    ) -> str | None:
        """Reconstruct plain text from an OpenAlex inverted abstract index."""
        if not inverted_index:
            return None

        positioned_words = [
            (position, word) for word, positions in inverted_index.items() for position in positions
        ]

        positioned_words.sort(key=lambda item: item[0])

        return " ".join(word for _, word in positioned_words)
