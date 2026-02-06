"""Comprehensive guide to argument patterns using Python's *, syntax.

This example demonstrates all the ways to control whether CLI arguments
are positional or named using native Python keyword-only parameter syntax.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

from sitk_cli import register_command

if TYPE_CHECKING:
    import SimpleITK as sitk

app = typer.Typer()


# Pattern 1: All positional (default for required Image/Transform parameters)
@register_command(app)
def all_positional(input: sitk.Image, mask: sitk.Image) -> sitk.Image:
    """All required inputs are positional by default.

    CLI: all-positional INPUT MASK OUTPUT
    """
    return input * mask


# Pattern 2: Mixed positional and named using *, (Pythonic!)
@register_command(app)
def mixed_args(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
    """Use *, to make specific parameters keyword-only.

    CLI: mixed-args INPUT OUTPUT --mask MASK

    The *, separator makes everything after it keyword-only,
    so 'mask' becomes a named option while 'input' stays positional.
    This is the recommended Python pattern!
    """
    return input * mask


# Pattern 3: All keyword-only
@register_command(app)
def all_named(*, input: sitk.Image, mask: sitk.Image) -> sitk.Image:
    """Use *, at start to make ALL parameters keyword-only.

    CLI: all-named --input INPUT --mask MASK --output OUTPUT

    Note: Output is also named because there are no positional inputs.
    """
    return input * mask


# Pattern 4: Optional parameters are always named
@register_command(app)
def optional_params(input: sitk.Image, mask: sitk.Image | None = None) -> sitk.Image:
    """Optional Image parameters (with defaults) are always named.

    CLI: optional-params INPUT OUTPUT [--mask MASK]

    Even without *,, optional parameters become named options.
    """
    if mask is not None:
        return input * mask
    return input


# Pattern 5: Complex mixing for maximum clarity
@register_command(app)
def segment_regions(
    input: sitk.Image,
    reference: sitk.Image,
    *,
    brain_mask: sitk.Image | None = None,
    threshold: float = 0.5,
) -> sitk.Image:
    """Recommended pattern: positional for required, keyword-only for optional.

    CLI: segment-regions INPUT REFERENCE OUTPUT \\
         [--brain-mask MASK] [--threshold 0.7]

    Benefits:
    - Required inputs (input, reference): positional → concise
    - Optional/configuration (brain_mask, threshold): keyword-only → explicit
    - This is the most Pythonic and readable CLI pattern!
    """
    result = input + reference
    if brain_mask is not None:
        result = result * brain_mask
    return result > threshold


if __name__ == "__main__":
    app()
