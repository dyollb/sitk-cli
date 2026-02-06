"""Tests for verbose mode functionality."""

from __future__ import annotations

import logging
from inspect import signature

import SimpleITK as sitk

import sitk_cli


def process_image(input: sitk.Image) -> sitk.Image:
    """Process an image."""
    logger = logging.getLogger("sitk_cli")
    logger.info("Processing image")
    logger.debug("Debug information")
    return input


def test_verbose_mode_adds_parameter() -> None:
    """Test that verbose=True adds _verbose parameter."""
    cli = sitk_cli.make_cli(process_image, verbose=True)
    sig = signature(cli)

    # Should have input, output, and _verbose parameters
    assert len(sig.parameters) == 3
    assert "input" in sig.parameters
    assert "output" in sig.parameters
    assert "_verbose" in sig.parameters

    # _verbose should be an integer with default 0
    verbose_param = sig.parameters["_verbose"]
    assert verbose_param.annotation is int


def test_verbose_mode_disabled_by_default() -> None:
    """Test that verbose mode is disabled by default."""
    cli = sitk_cli.make_cli(process_image, verbose=False)
    sig = signature(cli)

    # Should NOT have _verbose parameter
    assert len(sig.parameters) == 2
    assert "input" in sig.parameters
    assert "output" in sig.parameters
    assert "_verbose" not in sig.parameters


def test_logger_exported() -> None:
    """Test that logger is exported from sitk_cli."""
    assert hasattr(sitk_cli, "logger")
    assert isinstance(sitk_cli.logger, logging.Logger)
    assert sitk_cli.logger.name == "sitk_cli"
