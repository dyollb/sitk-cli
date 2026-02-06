"""Example demonstrating automatic directory creation feature."""

from __future__ import annotations

import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer()


@register_command(app)  # create_dirs=True by default
def create_test_image(width: int = 100, height: int = 100) -> sitk.Image:
    """Create a test image with specified dimensions."""
    return sitk.Image(width, height, sitk.sitkUInt8)


@register_command(app, create_dirs=False)
def create_without_dirs(width: int = 100, height: int = 100) -> sitk.Image:
    """Create a test image but don't auto-create output directories."""
    return sitk.Image(width, height, sitk.sitkUInt8)


if __name__ == "__main__":
    app()
