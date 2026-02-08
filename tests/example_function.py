from __future__ import annotations

from enum import StrEnum

import SimpleITK as sitk
import typer

from sitk_cli import register_command


class Mode(StrEnum):
    moments = "moments"
    geometry = "geometry"


app = typer.Typer()


@register_command(app, func_name="centered-transform-initializer")
def example_function(
    fixed: sitk.Image,
    moving: sitk.Image,
    mode: Mode = Mode.moments.value,  # type: ignore
) -> sitk.Transform:
    """Test function"""

    operation_mode = (
        sitk.CenteredTransformInitializerFilter.MOMENTS
        if mode == Mode.moments.value
        else sitk.CenteredTransformInitializerFilter.GEOMETRY
    )
    tx: sitk.Transform = sitk.CenteredTransformInitializer(
        fixed, moving, sitk.Euler3DTransform(), operation_mode
    )
    return tx
