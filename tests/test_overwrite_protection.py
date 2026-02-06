"""Tests for overwrite protection feature."""

from __future__ import annotations

from pathlib import Path

import pytest
import SimpleITK as sitk

from sitk_cli import make_cli


def create_dummy_image() -> sitk.Image:
    """Create a dummy SimpleITK Image for testing."""
    return sitk.Image(10, 10, sitk.sitkUInt8)


def test_overwrite_true_always_overwrites(tmp_path: Path) -> None:
    """Test that overwrite=True always overwrites existing files."""

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=True)

    output_path = tmp_path / "output.nii"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()
    mtime1 = output_path.stat().st_mtime

    # Overwrite without --force (should work)
    cli_func(output=output_path)
    assert output_path.exists()
    # File should have been modified
    mtime2 = output_path.stat().st_mtime
    assert mtime2 >= mtime1


def test_overwrite_false_raises_error(tmp_path: Path) -> None:
    """Test that overwrite=False raises error if file exists."""

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=False)

    output_path = tmp_path / "output.nii"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()

    # Try to overwrite without --force (should fail)
    with pytest.raises(FileExistsError, match="already exists"):
        cli_func(output=output_path)


def test_overwrite_false_with_force_flag(tmp_path: Path) -> None:
    """Test that --force flag overrides overwrite=False."""

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=False)

    output_path = tmp_path / "output.nii"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()

    # Overwrite with _force=True (should work)
    cli_func(output=output_path, _force=True)
    assert output_path.exists()


def test_overwrite_false_force_short_flag(tmp_path: Path) -> None:
    """Test that force parameter works directly."""

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=False)

    output_path = tmp_path / "output.nii"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()

    # Overwrite with _force=True (should work)
    cli_func(output=output_path, _force=True)
    assert output_path.exists()


def test_overwrite_prompt_mode_with_force(tmp_path: Path) -> None:
    """Test that prompt mode with force skips prompting."""

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite="prompt")

    output_path = tmp_path / "output.nii"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()

    # Overwrite with _force=True (should skip prompt)
    cli_func(output=output_path, _force=True)
    assert output_path.exists()


def test_overwrite_protection_with_transform(tmp_path: Path) -> None:
    """Test that overwrite protection works with Transform outputs."""

    def create_transform() -> sitk.Transform:
        return sitk.AffineTransform(2)

    cli_func = make_cli(create_transform, overwrite=False)

    output_path = tmp_path / "transform.tfm"

    # Create initial file
    cli_func(output=output_path)
    assert output_path.exists()

    # Try to overwrite (should fail)
    with pytest.raises(FileExistsError):
        cli_func(output=output_path)


def test_no_force_flag_when_overwrite_true() -> None:
    """Test that no --force flag is added when overwrite=True."""
    from inspect import signature

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=True)
    sig = signature(cli_func)

    # Check that _force parameter is not present
    assert "_force" not in sig.parameters


def test_force_flag_present_when_overwrite_false() -> None:
    """Test that --force flag appears when overwrite=False."""
    from inspect import signature

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite=False)
    sig = signature(cli_func)

    # Check _force parameter is present
    assert "_force" in sig.parameters


def test_force_flag_present_when_overwrite_prompt() -> None:
    """Test that --force flag appears when overwrite='prompt'."""
    from inspect import signature

    def create_image() -> sitk.Image:
        return create_dummy_image()

    cli_func = make_cli(create_image, overwrite="prompt")
    sig = signature(cli_func)

    # Check _force parameter is present
    assert "_force" in sig.parameters
