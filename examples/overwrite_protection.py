"""Demonstrates overwrite protection modes for output files.

This example shows how to control output file overwrite behavior using the
`overwrite` parameter in make_cli() and register_command().

Three modes are available:
- True: Always overwrite without asking
- False: Raise error if file exists (adds --force/-f flag to override)
- "prompt": Ask user interactively (adds --force/-f flag to skip prompt)
"""

import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer(help="Overwrite protection examples")


# Mode 1: Always overwrite (default, backward compatible)
# Will silently overwrite existing files
@register_command(app, overwrite=True)
def always_overwrite(size: int = 100) -> sitk.Image:
    """Create image (always overwrites)."""
    return sitk.Image(size, size, sitk.sitkUInt8)


# Mode 2: Never overwrite without --force
# Raises FileExistsError if output exists unless --force flag is used
@register_command(app, overwrite=False)
def protected(size: int = 100) -> sitk.Image:
    """Create image (protected, use --force to overwrite)."""
    return sitk.Image(size, size, sitk.sitkUInt8)


# Mode 3: Prompt user interactively
# Asks "Output file exists. Overwrite? [y/N]:" if file exists
# Can be bypassed with --force flag for non-interactive scripts
@register_command(app, overwrite="prompt")
def prompt_mode(size: int = 100) -> sitk.Image:
    """Create image (prompts if exists, use --force to skip)."""
    return sitk.Image(size, size, sitk.sitkUInt8)


if __name__ == "__main__":
    app()


# Usage examples:
#
# 1. Always overwrite mode (default):
#    python overwrite_protection.py always-overwrite output.nii
#    python overwrite_protection.py always-overwrite output.nii  # Overwrites silently
#
# 2. Protected mode (error on conflict):
#    python overwrite_protection.py protected output.nii
#    python overwrite_protection.py protected output.nii  # ERROR: file exists
#    python overwrite_protection.py protected output.nii --force  # OK, overwrites
#    python overwrite_protection.py protected output.nii -f  # Short form also works
#
# 3. Prompt mode (interactive):
#    python overwrite_protection.py prompt-mode output.nii
#    python overwrite_protection.py prompt-mode output.nii  # Asks: Overwrite? [y/N]:
#    python overwrite_protection.py prompt-mode output.nii --force  # Skip prompt
