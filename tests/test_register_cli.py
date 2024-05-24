from typer.testing import CliRunner


def test_register_command():
    from .example_function import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "centered-transform-initializer" in result.stdout
    assert "Test function" in result.stdout
