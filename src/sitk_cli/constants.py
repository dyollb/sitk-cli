"""Constants and default values for sitk-cli."""

from __future__ import annotations

from typing import Final

# Parameter names for internal CLI flags
VERBOSE_PARAM_NAME: Final = "_verbose"
FORCE_PARAM_NAME: Final = "_force"

# Default values for make_cli/register_command
DEFAULT_OUTPUT_ARG_NAME: Final = "output"
DEFAULT_OUTPUT_TEMPLATE: Final = "{stem}{suffix}"

# Default glob patterns for file discovery
DEFAULT_IMAGE_GLOB: Final = "*.nii.gz"
DEFAULT_TRANSFORM_GLOB: Final = "*.tfm"
