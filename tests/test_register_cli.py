import SimpleITK as sitk
import typer
from typer.testing import CliRunner

from sitk_cli import register_command

app = typer.Typer()


@register_command(app, func_name="centered-transform-initializer")
def example_function(
    fixed: sitk.Image, moving: sitk.Image, init_transform: sitk.Transform
) -> sitk.Transform:
    """Test function"""
    tx = sitk.CenteredTransformInitializer(fixed, moving)
    return sitk.CompositeTransform([init_transform, tx])


def test_register_command():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "centered-transform-initializer" in result.stdout
    assert "Test function" in result.stdout
