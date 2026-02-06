"""Example demonstrating positional vs named arguments."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

from sitk_cli import register_command

if TYPE_CHECKING:
    import SimpleITK as sitk

app = typer.Typer()


# Default: required inputs are positional
@register_command(app)
def process_positional(input: sitk.Image, threshold: float = 0.5) -> sitk.Image:
    """Process image with positional input argument.

    Usage: process-positional INPUT OUTPUT --threshold 0.7
    """
    return input > threshold


# Use *, to make all inputs keyword-only (named)
@register_command(app)
def process_named(*, input: sitk.Image, threshold: float = 0.5) -> sitk.Image:
    """Process image with all named arguments.

    Usage: process-named --input INPUT --output OUTPUT --threshold 0.7
    (All parameters after *, are keyword-only, so output is also named)
    """
    return input > threshold


# Force specific parameters to be named using Python's keyword-only syntax
@register_command(app)
def process_mixed(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
    """Process image with mixed positional/named arguments.

    Usage: process-mixed INPUT OUTPUT --mask MASK
    (input is positional, mask is keyword-only after *,)
    """
    return input * mask


# Multiple positional inputs (default)
@register_command(app)
def add_images(input1: sitk.Image, input2: sitk.Image) -> sitk.Image:
    """Add two images together.

    Usage: add-images INPUT1 INPUT2 OUTPUT
    """
    return input1 + input2


# Optional inputs remain named
@register_command(app)
def optional_second(input1: sitk.Image, input2: sitk.Image | None = None) -> sitk.Image:
    """Add two images or return first if second is missing.

    Usage: optional-second INPUT1 OUTPUT [--input2 INPUT2]
    (input1 is required so it's positional, output is positional because input1 is,
     input2 is named because it's optional)
    """
    if input2 is None:
        return input1
    return input1 + input2


if __name__ == "__main__":
    app()
