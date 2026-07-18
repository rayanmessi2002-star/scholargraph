"""Tests for the ScholarGraph command-line interface."""

from typer.testing import CliRunner

from scholargraph.cli import app

runner = CliRunner()


def test_version_command() -> None:
    """The version command should display the installed version."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "ScholarGraph 0.1.0" in result.stdout
