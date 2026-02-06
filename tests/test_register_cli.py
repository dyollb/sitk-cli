from typer.testing import CliRunner

from .example_function import app


def test_register_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "centered-transform-initializer" in result.stdout
    assert "Test function" in result.stdout
