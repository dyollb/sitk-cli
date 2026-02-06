"""Demonstrate keyword-only parameters using Python's *, syntax."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer

from sitk_cli import register_command

if TYPE_CHECKING:
    import SimpleITK as sitk

app = typer.Typer()


# All positional (default new behavior)
@register_command(app)
def process_all_positional(input: sitk.Image, mask: sitk.Image) -> sitk.Image:
    """Process with all positional args.

    Usage: process-all-positional INPUT MASK OUTPUT
    """
    return input * mask


# Mixed: some positional, some keyword-only using *,
@register_command(app)
def process_mixed(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
    """Process with mixed args (Pythonic way!).

    Usage: process-mixed INPUT OUTPUT --mask MASK

    The *, in the signature makes 'mask' keyword-only, so it becomes
    a named option on the CLI, while 'input' remains positional.
    """
    return input * mask


# All keyword-only
@register_command(app)
def process_all_named(*, input: sitk.Image, mask: sitk.Image) -> sitk.Image:
    """Process with all named options.

    Usage: process-all-named OUTPUT --input INPUT --mask MASK

    The *, at the start makes ALL parameters keyword-only.
    """
    return input * mask


# Complex example: multiple regions with positional/keyword-only mix
@register_command(app)
def segment_regions(
    input: sitk.Image,
    reference: sitk.Image,
    *,
    brain_mask: sitk.Image | None = None,
    threshold: float = 0.5,
) -> sitk.Image:
    """Segment regions with flexible arguments.

    Usage: segment-regions INPUT REFERENCE OUTPUT \\
           [--brain-mask MASK] [--threshold 0.7]

    - input, reference, output: positional (required, concise)
    - brain_mask, threshold: keyword-only (optional, explicit)

    This is the most Pythonic and readable way to define CLIs!
    """
    result = input + reference
    if brain_mask is not None:
        result = result * brain_mask
    return result > threshold


if __name__ == "__main__":
    app()
