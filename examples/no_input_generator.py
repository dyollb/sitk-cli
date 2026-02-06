"""Example demonstrating output-only functions (image generators)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

from sitk_cli import register_command

if TYPE_CHECKING:
    import SimpleITK as sitk

app = typer.Typer()


@register_command(app)
def create_test_image() -> sitk.Image:
    """Create a simple test image.

    Usage: create-test-image OUTPUT
    (Output is positional because there are no input Image/Transform parameters)
    """
    import SimpleITK as sitk_

    # Create a 100x100 image filled with zeros
    image = sitk_.Image([100, 100], sitk_.sitkUInt8)
    return image


@register_command(app)
def create_checkerboard(
    size: int = 100,
    square_size: int = 10,
) -> sitk.Image:
    """Create a checkerboard pattern image.

    Usage: create-checkerboard OUTPUT --size 200 --square-size 20
    (Output is positional, size and square_size are named options with defaults)
    """
    import SimpleITK as sitk_

    # Create checkerboard pattern
    image = sitk_.Image([size, size], sitk_.sitkUInt8)
    for y in range(size):
        for x in range(size):
            if (x // square_size + y // square_size) % 2 == 0:
                image.SetPixel([x, y], 255)
    return image


@register_command(app)
def create_gradient(
    *,
    width: int = 100,
    height: int = 100,
) -> sitk.Image:
    """Create a horizontal gradient image with all keyword-only parameters.

    Usage: create-gradient --output OUTPUT --width 200 --height 150
    (Output is named because all non-Image/Transform parameters are keyword-only)
    """
    import SimpleITK as sitk_

    # Create horizontal gradient
    image = sitk_.Image([width, height], sitk_.sitkUInt8)
    for y in range(height):
        for x in range(width):
            image.SetPixel([x, y], int(255 * x / width))
    return image


if __name__ == "__main__":
    app()
