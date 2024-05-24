from __future__ import annotations

from enum import Enum

import SimpleITK as sitk
import typer

from sitk_cli import register_command


class Mode(str, Enum):
    moments = "moments"
    geometry = "geometry"


app = typer.Typer()


@register_command(
    app, func_name="centered-transform-initializer", locals=locals(), globals=globals()
)
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
