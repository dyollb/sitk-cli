from inspect import signature
from pathlib import Path
from typing import Tuple

import SimpleITK as sitk

import sitk_cli


def get_shape(input: sitk.Image) -> Tuple[int, int]:
    return input.GetWidth(), input.GetHeight()


def make_image(width: int, height: int) -> sitk.Image:
    return sitk.Image(width, height, sitk.sitkInt16)


def test_make_cli_image_arg():
    cli = sitk_cli.make_cli(get_shape)
    sig = signature(cli)

    assert len(sig.parameters) == 1
    assert issubclass(sig.parameters["input"].annotation, Path)


def test_make_cli_image_return():
    cli = sitk_cli.make_cli(make_image)
    sig = signature(cli)

    assert len(sig.parameters) == 3
    assert sig.parameters["width"].annotation is int
    assert sig.parameters["height"].annotation is int
    assert issubclass(sig.parameters["output"].annotation, Path)


def test_make_cli_usage(tmp_path: Path):
    make_image_cli = sitk_cli.make_cli(make_image)
    get_width_cli = sitk_cli.make_cli(get_shape)

    tmp_file = tmp_path / "image.nii.gz"
    make_image_cli(width=32, height=64, output=tmp_file)
    width, height = get_width_cli(input=tmp_file)
    assert width == 32 and height == 64

    # check running without writing output file
    make_image_cli(width=32, height=64, output=None)
