from __future__ import annotations

from inspect import Parameter, signature
from pathlib import Path
from typing import Any

import SimpleITK as sitk
from typer.models import OptionInfo

import sitk_cli


def select_image(*, input1: sitk.Image, input2: sitk.Image | None = None) -> sitk.Image:
    return input1 if input2 is None else input2


def pass_image(name: str, *, input: sitk.Image | None = None) -> sitk.Image | None:
    return input


def get_option_default(p: Parameter) -> Any:
    input_default: OptionInfo = p.default
    assert isinstance(input_default, OptionInfo)
    return input_default.default


def test_optional_argument() -> None:
    """Test optional arguments with keyword-only inputs."""
    cli = sitk_cli.create_command(select_image)
    sig = signature(cli)

    assert len(sig.parameters) == 3
    assert sig.parameters["input1"].annotation is Path
    assert sig.parameters["input2"].annotation is Path
    assert sig.parameters["output"].annotation, Path

    # All inputs are keyword-only, so output is also named (None means optional)
    assert get_option_default(sig.parameters["input1"]) is not None
    assert get_option_default(sig.parameters["input2"]) is None
    assert sig.parameters["output"].default is None


def _test_optional_return_type() -> None:
    """Test optional return type with keyword-only inputs."""
    cli = sitk_cli.create_command(pass_image)
    sig = signature(cli)

    assert len(sig.parameters) == 3
    assert sig.parameters["name"].annotation is str
    assert sig.parameters["input"].annotation is Path
    assert sig.parameters["output"].annotation, Path

    # name stays as is, input is keyword-only so it's named
    assert get_option_default(sig.parameters["name"]) is not None
    assert get_option_default(sig.parameters["input"]) is None
    assert sig.parameters["output"].default is None
