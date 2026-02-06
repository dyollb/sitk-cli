"""Demonstrates automatic directory creation for output files.

By default, sitk-cli automatically creates parent directories for output
files. This can be disabled with create_dirs=False.
"""

from __future__ import annotations

import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer()


@register_command(app)  # create_dirs=True by default
def process_with_auto_dirs(width: int = 100, height: int = 100) -> sitk.Image:
    """Process that auto-creates output directories.

    CLI: process-with-auto-dirs OUTPUT --width 100 --height 100

    You can specify nested paths like:
        process-with-auto-dirs results/2024/output.nii --width 200

    The directories 'results/2024/' will be created automatically.
    """
    return sitk.Image(width, height, sitk.sitkUInt8)


@register_command(app, create_dirs=False)
def process_no_auto_dirs(width: int = 100, height: int = 100) -> sitk.Image:
    """Process that requires directories to exist.

    CLI: process-no-auto-dirs OUTPUT --width 100 --height 100

    If you specify a path with directories that don't exist, you'll get an error.
    Useful when you want to ensure output paths are pre-validated.
    """
    return sitk.Image(width, height, sitk.sitkUInt8)


if __name__ == "__main__":
    app()
