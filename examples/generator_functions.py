"""Demonstrates functions that generate images without input images.

When a function has no Image/Transform inputs but returns an Image/Transform,
the output parameter is positional by default (unless you use *, syntax).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

from sitk_cli import register_command

if TYPE_CHECKING:
    import SimpleITK as sitk

app = typer.Typer()


@register_command(app)
def create_blank() -> sitk.Image:
    """Create a blank 100x100 image.

    CLI: create-blank OUTPUT

    Output is positional because there are no Image/Transform inputs.
    """
    import SimpleITK as sitk_

    return sitk_.Image([100, 100], sitk_.sitkUInt8)


@register_command(app)
def create_checkerboard(
    size: int = 100,
    square_size: int = 10,
) -> sitk.Image:
    """Create a checkerboard pattern.

    CLI: create-checkerboard OUTPUT --size 200 --square-size 20

    Output is positional, size/square_size are named options with defaults.
    """
    import SimpleITK as sitk_

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
    """Create a horizontal gradient image.

    CLI: create-gradient --output OUTPUT --width 200 --height 150

    Using *, makes all parameters keyword-only, so output is also named.
    """
    import SimpleITK as sitk_

    image = sitk_.Image([width, height], sitk_.sitkUInt8)
    for y in range(height):
        for x in range(width):
            image.SetPixel([x, y], int(255 * x / width))
    return image


if __name__ == "__main__":
    app()
