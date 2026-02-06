from __future__ import annotations

from inspect import signature
from pathlib import Path

import pytest
import SimpleITK as sitk

import sitk_cli


def get_shape(input: sitk.Image) -> tuple[int, int]:
    return input.GetWidth(), input.GetHeight()


def make_image(width: int, height: int) -> sitk.Image:
    return sitk.Image(width, height, sitk.sitkInt16)


def register_api(
    fixed: sitk.Image, moving: sitk.Image, init_transform: sitk.Transform
) -> sitk.Transform:
    tx = sitk.CenteredTransformInitializer(fixed, moving)
    return sitk.CompositeTransform([init_transform, tx])


def select_image(input1: sitk.Image, input2: sitk.Image | None) -> sitk.Image:
    return input1 if input2 is None else input2


def test_make_cli_image_arg() -> None:
    cli = sitk_cli.make_cli(get_shape)
    sig = signature(cli)

    assert len(sig.parameters) == 1
    assert issubclass(sig.parameters["input"].annotation, Path)


def test_make_cli_image_return() -> None:
    cli = sitk_cli.make_cli(make_image)
    sig = signature(cli)

    assert len(sig.parameters) == 3
    assert sig.parameters["width"].annotation is int
    assert sig.parameters["height"].annotation is int
    assert issubclass(sig.parameters["output"].annotation, Path)


def test_make_cli_usage(tmp_path: Path) -> None:
    make_image_cli = sitk_cli.make_cli(make_image)
    get_width_cli = sitk_cli.make_cli(get_shape)

    tmp_file = tmp_path / "image.nii.gz"
    make_image_cli(width=32, height=64, output=tmp_file)
    width, height = get_width_cli(input=tmp_file)
    assert width == 32 and height == 64

    # check running without writing output file
    make_image_cli(width=32, height=64, output=None)


def test_make_cli_transform_arg() -> None:
    cli = sitk_cli.make_cli(register_api, output_arg_name="output_transform")
    sig = signature(cli)

    assert len(sig.parameters) == 4
    assert issubclass(sig.parameters["fixed"].annotation, Path)
    assert issubclass(sig.parameters["moving"].annotation, Path)
    assert issubclass(sig.parameters["init_transform"].annotation, Path)
    assert issubclass(sig.parameters["output_transform"].annotation, Path)


def test_optional_argument() -> None:
    cli = sitk_cli.make_cli(select_image)
    sig = signature(cli)

    assert len(sig.parameters) == 3
    assert sig.parameters["input1"].annotation is Path
    assert sig.parameters["input2"].annotation is Path
    assert sig.parameters["output"].annotation, Path


def test_file_not_found_error_for_image(tmp_path: Path) -> None:
    """Test that FileNotFoundError is raised when input image file doesn't exist."""
    get_shape_cli = sitk_cli.make_cli(get_shape)
    nonexistent_file = tmp_path / "does_not_exist.nii.gz"

    with pytest.raises(FileNotFoundError, match="Input image file not found"):
        get_shape_cli(input=nonexistent_file)


def test_file_not_found_error_for_transform(tmp_path: Path) -> None:
    """Test that FileNotFoundError is raised when input transform file doesn't exist."""

    # Create a simple function that takes a transform
    def process_transform(tx: sitk.Transform) -> sitk.Transform:
        return tx

    process_cli = sitk_cli.make_cli(process_transform)
    nonexistent_file = tmp_path / "does_not_exist.tfm"

    with pytest.raises(FileNotFoundError, match="Input transform file not found"):
        process_cli(tx=nonexistent_file, output=tmp_path / "output.tfm")


def test_auto_create_output_directories(tmp_path: Path) -> None:
    """Test that output directories are created automatically when create_dirs=True."""
    make_image_cli = sitk_cli.make_cli(make_image, create_dirs=True)

    # Create output path with nested directories that don't exist
    nested_output = tmp_path / "level1" / "level2" / "level3" / "output.nii.gz"
    assert not nested_output.parent.exists()

    # Should create directories automatically
    make_image_cli(width=64, height=64, output=nested_output)

    assert nested_output.exists()
    assert nested_output.parent.exists()


def test_no_auto_create_directories_when_disabled(tmp_path: Path) -> None:
    """Test that directories are NOT created when create_dirs=False."""
    make_image_cli = sitk_cli.make_cli(make_image, create_dirs=False)

    # Create output path with directory that doesn't exist
    nested_output = tmp_path / "nonexistent" / "output.nii.gz"
    assert not nested_output.parent.exists()

    # Should raise RuntimeError from SimpleITK when trying to write to non-existent directory
    with pytest.raises(RuntimeError, match="failed to write image"):
        make_image_cli(width=64, height=64, output=nested_output)
