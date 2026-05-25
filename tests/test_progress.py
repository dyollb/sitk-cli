"""Tests for progress feedback utilities."""

from __future__ import annotations

import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
import SimpleITK as sitk

import sitk_cli
from sitk_cli.progress import (
    _NoOpProgressBar,
    _RichProgressBarProxy,
    _should_show_progress,
)


@pytest.fixture(autouse=True)
def reset_logger() -> Generator[None, None, None]:
    yield
    logging.getLogger("sitk_cli").setLevel(logging.WARNING)


# --- _should_show_progress ---


def test_should_show_progress_false_at_warning_level() -> None:
    assert not _should_show_progress()


def test_should_show_progress_true_at_info_level() -> None:
    sitk_cli.logger.setLevel(logging.INFO)
    assert _should_show_progress()


def test_should_show_progress_true_at_debug_level() -> None:
    sitk_cli.logger.setLevel(logging.DEBUG)
    assert _should_show_progress()


# --- _NoOpProgressBar ---


def test_noop_progress_bar_update_is_silent() -> None:
    noop = _NoOpProgressBar()
    noop.update()
    noop.update(5)


# --- progress_bar (no-op paths) ---


def test_progress_bar_noop_when_not_verbose() -> None:
    with sitk_cli.progress_bar(total=10, desc="test") as pbar:
        assert isinstance(pbar, _NoOpProgressBar)
        pbar.update(3)


def test_progress_bar_noop_when_rich_unavailable() -> None:
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)
    with (
        patch.object(pm, "_rich_available", False),
        sitk_cli.progress_bar(total=10, desc="test") as pbar,
    ):
        assert isinstance(pbar, _NoOpProgressBar)


# --- progress_bar (Rich path) ---


def test_progress_bar_yields_proxy_when_verbose_and_rich() -> None:
    pytest.importorskip("rich")
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)

    mock_progress_instance = MagicMock()
    mock_progress_class = MagicMock()
    mock_progress_class.return_value.__enter__ = MagicMock(
        return_value=mock_progress_instance
    )
    mock_progress_class.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(pm, "Progress", mock_progress_class),
        sitk_cli.progress_bar(total=5, desc="test") as pbar,
    ):
        assert isinstance(pbar, _RichProgressBarProxy)
        pbar.update(2)

    mock_progress_instance.add_task.assert_called_once_with("test", total=5)
    mock_progress_instance.update.assert_called_once()


# --- progress_tracker (no-op paths) ---


def test_progress_tracker_noop_when_not_verbose() -> None:
    mock_sitk = MagicMock()
    with sitk_cli.progress_tracker(mock_sitk, desc="test"):
        pass
    mock_sitk.AddCommand.assert_not_called()
    mock_sitk.RemoveAllCommands.assert_not_called()


def test_progress_tracker_noop_when_rich_unavailable() -> None:
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)
    mock_sitk = MagicMock()
    with (
        patch.object(pm, "_rich_available", False),
        sitk_cli.progress_tracker(mock_sitk, desc="test"),
    ):
        pass
    mock_sitk.AddCommand.assert_not_called()


# --- progress_tracker (Rich path) ---


def test_progress_tracker_registers_three_commands_when_verbose() -> None:
    pytest.importorskip("rich")
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)

    mock_sitk = MagicMock()
    mock_progress_instance = MagicMock()
    mock_progress_class = MagicMock()
    mock_progress_class.return_value.__enter__ = MagicMock(
        return_value=mock_progress_instance
    )
    mock_progress_class.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(pm, "Progress", mock_progress_class),
        sitk_cli.progress_tracker(mock_sitk, desc="test"),
    ):
        pass

    assert mock_sitk.AddCommand.call_count == 3
    mock_sitk.RemoveAllCommands.assert_called_once()


def test_progress_tracker_removes_commands_on_exception() -> None:
    pytest.importorskip("rich")
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)

    mock_sitk = MagicMock()
    mock_progress_instance = MagicMock()
    mock_progress_class = MagicMock()
    mock_progress_class.return_value.__enter__ = MagicMock(
        return_value=mock_progress_instance
    )
    mock_progress_class.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(pm, "Progress", mock_progress_class),
        pytest.raises(RuntimeError),
        sitk_cli.progress_tracker(mock_sitk, desc="test"),
    ):
        raise RuntimeError("test error")

    mock_sitk.RemoveAllCommands.assert_called_once()


def test_progress_tracker_callbacks_update_progress() -> None:
    """Verify observer callbacks call the correct Rich progress methods."""
    pytest.importorskip("rich")
    import sitk_cli.progress as pm

    sitk_cli.logger.setLevel(logging.INFO)

    mock_sitk = MagicMock()
    mock_sitk.GetProgress.return_value = 0.5

    mock_progress_instance = MagicMock()
    task_id = mock_progress_instance.add_task.return_value
    mock_progress_class = MagicMock()
    mock_progress_class.return_value.__enter__ = MagicMock(
        return_value=mock_progress_instance
    )
    mock_progress_class.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch.object(pm, "Progress", mock_progress_class),
        sitk_cli.progress_tracker(mock_sitk, desc="test"),
    ):
        # Extract the registered callbacks
        calls = mock_sitk.AddCommand.call_args_list
        assert len(calls) == 3

        on_start = calls[0][0][1]
        on_progress = calls[1][0][1]
        on_end = calls[2][0][1]

        # Verify event types
        assert calls[0][0][0] == sitk.sitkStartEvent
        assert calls[1][0][0] == sitk.sitkProgressEvent
        assert calls[2][0][0] == sitk.sitkEndEvent

        # Invoke callbacks and verify they call Rich correctly
        on_start()
        mock_progress_instance.reset.assert_called_once_with(task_id)

        on_progress()
        mock_progress_instance.update.assert_called_with(task_id, completed=0.5)

        on_end()
        mock_progress_instance.update.assert_called_with(task_id, completed=1.0)
