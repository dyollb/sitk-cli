import logging
import sys
from typing import Final

from .batch import create_batch_command
from .lib import make_cli, register_command

# Try to use Rich if available, otherwise fall back to standard logging
try:
    from rich.logging import RichHandler

    _handler: logging.Handler = RichHandler(
        show_path=False,
        show_time=False,
        markup=True,
    )
except ImportError:
    _handler = logging.StreamHandler(sys.stderr)
    _formatter = logging.Formatter("%(levelname)s: %(message)s")
    _handler.setFormatter(_formatter)

# Create package-level logger
logger = logging.getLogger("sitk_cli")
logger.setLevel(logging.WARNING)  # Default: quiet
logger.addHandler(_handler)
logger.propagate = False  # Don't propagate to root logger

__version__: Final = "0.8.0"
__all__ = (
    "__version__",
    "create_batch_command",
    "logger",
    "make_cli",
    "register_command",
)
