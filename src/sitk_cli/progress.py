"""Progress feedback utilities for long-running SimpleITK operations."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING

import SimpleITK as sitk

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any

_logger = logging.getLogger("sitk_cli")

try:
    from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

    _rich_available: bool = True
except ImportError:
    _rich_available = False


def _should_show_progress() -> bool:
    return _logger.getEffectiveLevel() < logging.WARNING


class _NoOpProgressBar:
    def update(self, n: int = 1) -> None:
        pass


class _RichProgressBarProxy:
    def __init__(self, progress: Any, task_id: Any) -> None:
        self._progress = progress
        self._task_id = task_id

    def update(self, n: int = 1) -> None:
        self._progress.update(self._task_id, advance=n)


@contextmanager
def progress_tracker(
    sitk_obj: Any, desc: str = "Processing"
) -> Generator[None, None, None]:
    """Context manager that hooks into SimpleITK's observer pattern to show a progress bar.

    Attaches StartEvent, ProgressEvent, and EndEvent observers to ``sitk_obj``
    and renders a Rich progress bar. Only active when verbose mode is on and
    Rich is installed; otherwise a no-op.
    """
    if not _should_show_progress() or not _rich_available:
        yield
        return

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task(desc, total=1.0)

        def on_start() -> None:
            progress.reset(task)

        def on_progress() -> None:
            progress.update(task, completed=sitk_obj.GetProgress())

        def on_end() -> None:
            progress.update(task, completed=1.0)

        sitk_obj.AddCommand(sitk.sitkStartEvent, on_start)
        sitk_obj.AddCommand(sitk.sitkProgressEvent, on_progress)
        sitk_obj.AddCommand(sitk.sitkEndEvent, on_end)

        try:
            yield
        finally:
            sitk_obj.RemoveAllCommands()


@contextmanager
def progress_bar(
    total: int, desc: str = "Processing"
) -> Generator[_NoOpProgressBar | _RichProgressBarProxy, None, None]:
    """Context manager that provides a manually-updated progress bar.

    Yields an object with an ``update(n)`` method. When verbose mode is
    inactive or Rich is not installed, yields a silent no-op object instead.
    """
    if not _should_show_progress() or not _rich_available:
        yield _NoOpProgressBar()
        return

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task(desc, total=total)
        yield _RichProgressBarProxy(progress, task)
