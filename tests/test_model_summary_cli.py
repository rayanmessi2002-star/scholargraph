"""Tests for optional model-assisted synthesis through the CLI."""

from __future__ import annotations

from types import TracebackType

import pytest
from typer.testing import CliRunner

from scholargraph.cli import app
from scholargraph.domain import Publication, SummaryClaim
from scholargraph.services.model_synthesis import ModelSynthesisResult

runner = CliRunner()


class FakeOpenAlexProvider:
    """Return deterministic publication evidence without network access."""

    called = False

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def __enter__(self) -> FakeOpenAlexProvider:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        page: int = 1,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Publication]:
        type(self).called = True

        return [
            Publication(
                source="openalex",
                source_id="W1",
                title="Graph Databases",
                abstract=("Graph databases represent connected information."),
                doi="10.1000/graph",
            )
        ]


class FakeOpenAITransport:
    """Return model output without importing the SDK or calling the API."""

    api_key: str | None = None
    model: str | None = None

    @classmethod
    def from_api_key(
        cls,
        *,
        api_key: str,
    ) -> FakeOpenAITransport:
        """Create the simulated transport."""
        cls.api_key = api_key
        return cls()

    def parse(
        self,
        *,
        model: str,
        instructions: str,
        input_text: str,
    ) -> ModelSynthesisResult:
        """Return deterministic structured model output."""
        type(self).model = model

        return ModelSynthesisResult(
            claims=(
                SummaryClaim(
                    text=("Graph databases represent connected information."),
                    citations=("S1",),
                ),
            )
        )


@pytest.fixture
def fake_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace external providers with deterministic test doubles."""
    FakeOpenAlexProvider.called = False
    FakeOpenAITransport.api_key = None
    FakeOpenAITransport.model = None

    monkeypatch.setattr(
        "scholargraph.cli.OpenAlexProvider",
        FakeOpenAlexProvider,
    )
    monkeypatch.setattr(
        "scholargraph.cli.OpenAIResponsesTransport",
        FakeOpenAITransport,
    )


def test_model_generator_uses_configured_openai_client(
    fake_dependencies: None,
) -> None:
    """The model option should produce a citation-safe summary."""
    result = runner.invoke(
        app,
        [
            "summarize",
            "graph databases",
            "--generator",
            "model",
        ],
        env={
            "OPENAI_API_KEY": "test-openai-key",
            "OPENAI_MODEL": "test-model",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Graph databases represent connected information." in result.output
    assert "[S1]" in result.output
    assert "Generator: model-assisted-v1" in result.output
    assert FakeOpenAITransport.api_key == "test-openai-key"
    assert FakeOpenAITransport.model == "test-model"
    assert FakeOpenAlexProvider.called is True


def test_model_generator_requires_api_key_before_search(
    fake_dependencies: None,
) -> None:
    """A missing credential should fail before academic retrieval."""
    result = runner.invoke(
        app,
        [
            "summarize",
            "graph databases",
            "--generator",
            "model",
        ],
        env={"OPENAI_API_KEY": ""},
    )

    assert result.exit_code == 1
    assert "OPENAI_API_KEY is required" in result.output
    assert FakeOpenAlexProvider.called is False


def test_extractive_generator_remains_the_default(
    fake_dependencies: None,
) -> None:
    """Free deterministic synthesis should remain backward compatible."""
    result = runner.invoke(
        app,
        [
            "summarize",
            "graph databases",
        ],
        env={"OPENAI_API_KEY": ""},
    )

    assert result.exit_code == 0, result.output
    assert "Generator: extractive-v1" in result.output
    assert FakeOpenAITransport.api_key is None
