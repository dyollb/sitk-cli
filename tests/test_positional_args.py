from __future__ import annotations

from inspect import signature

import SimpleITK as sitk
import typer

import sitk_cli


def process_image(input: sitk.Image, threshold: float = 0.5) -> sitk.Image:
    """Process an image with threshold."""
    return input > threshold


def two_inputs(input1: sitk.Image, input2: sitk.Image) -> sitk.Image:
    """Process two images."""
    return input1 + input2


def two_inputs_keyword_only(input1: sitk.Image, *, input2: sitk.Image) -> sitk.Image:
    """Process two images where input2 is keyword-only."""
    return input1 + input2


def optional_input(input1: sitk.Image, input2: sitk.Image | None = None) -> sitk.Image:
    """Process with optional second input."""
    return input1 if input2 is None else input1 + input2


def test_default_behavior_positional() -> None:
    """Test that required Image inputs become positional by default."""
    cli = sitk_cli.make_cli(process_image)
    sig = signature(cli)

    # Input should be ArgumentInfo (positional), not OptionInfo
    assert sig.parameters["input"].default.__class__.__name__ == "ArgumentInfo"
    # Threshold has default value, keeps its default (not converted to Option)
    assert sig.parameters["threshold"].default == 0.5
    # Output should be ArgumentInfo (positional) because input is positional
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_all_keyword_only_makes_output_named() -> None:
    """Test that output is named when all inputs are keyword-only."""

    def all_keyword_only(*, input: sitk.Image, threshold: float = 0.5) -> sitk.Image:
        return input > threshold

    cli = sitk_cli.make_cli(all_keyword_only)
    sig = signature(cli)

    # Input is keyword-only (after *,)
    assert sig.parameters["input"].default.__class__.__name__ == "OptionInfo"
    # Threshold has default value
    assert sig.parameters["threshold"].default == 0.5
    # Output should be named (None) because NO inputs are positional
    assert sig.parameters["output"].default is None


def test_multiple_positional_inputs() -> None:
    """Test that multiple required inputs are all positional."""
    cli = sitk_cli.make_cli(two_inputs)
    sig = signature(cli)

    # Both inputs should be positional
    assert sig.parameters["input1"].default.__class__.__name__ == "ArgumentInfo"
    assert sig.parameters["input2"].default.__class__.__name__ == "ArgumentInfo"
    # Output should be positional because inputs are positional
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_optional_input_remains_named() -> None:
    """Test that optional Image inputs remain named."""
    cli = sitk_cli.make_cli(optional_input)
    sig = signature(cli)

    # First input is required, should be positional
    assert sig.parameters["input1"].default.__class__.__name__ == "ArgumentInfo"
    # Second input is optional (has default None), should remain named
    assert sig.parameters["input2"].default.__class__.__name__ == "OptionInfo"
    # Output should be positional because input1 is positional
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_keyword_only_parameter() -> None:
    """Test that keyword-only parameters (after *,) are always named."""
    cli = sitk_cli.make_cli(two_inputs_keyword_only)
    sig = signature(cli)

    # input1 is positional (before *,)
    assert sig.parameters["input1"].default.__class__.__name__ == "ArgumentInfo"
    # input2 is keyword-only (after *,), so it's named
    assert sig.parameters["input2"].default.__class__.__name__ == "OptionInfo"
    # output is positional because input1 is positional
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_all_keyword_only_parameters() -> None:
    """Test that when all inputs are keyword-only, output is also named."""

    def all_keyword_only(*, input1: sitk.Image, input2: sitk.Image) -> sitk.Image:
        return input1 + input2

    cli = sitk_cli.make_cli(all_keyword_only)
    sig = signature(cli)

    # Both inputs are keyword-only (after *,)
    assert sig.parameters["input1"].default.__class__.__name__ == "OptionInfo"
    assert sig.parameters["input2"].default.__class__.__name__ == "OptionInfo"
    # Output should be named because NO inputs are positional
    assert sig.parameters["output"].default is None


def test_no_inputs_makes_output_positional() -> None:
    """Test that output is positional when there are no input arguments."""

    def create_image() -> sitk.Image:
        """Create an image from scratch."""
        return sitk.Image()

    cli = sitk_cli.make_cli(create_image)
    sig = signature(cli)

    # Only parameter should be output, and it should be positional
    assert len(sig.parameters) == 1
    assert "output" in sig.parameters
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_no_inputs_with_regular_params() -> None:
    """Test output is positional when there are no Image inputs but other params."""

    def create_image(width: int = 100, height: int = 100) -> sitk.Image:
        """Create an image with specified dimensions."""
        return sitk.Image([width, height], sitk.sitkUInt8)

    cli = sitk_cli.make_cli(create_image)
    sig = signature(cli)

    # Should have width, height, and output parameters
    assert len(sig.parameters) == 3
    assert sig.parameters["width"].default == 100
    assert sig.parameters["height"].default == 100
    # Output should be positional because there are no Image/Transform inputs
    assert sig.parameters["output"].default.__class__.__name__ == "ArgumentInfo"


def test_register_command_default() -> None:
    """Test that register_command uses default behavior."""
    app = typer.Typer()

    @sitk_cli.register_command(app)
    def test_func(input: sitk.Image) -> sitk.Image:
        return input

    # Verify the command was registered
    assert len(app.registered_commands) == 1


def test_register_command_keyword_only() -> None:
    """Test that register_command respects keyword-only parameters."""
    app = typer.Typer()

    @sitk_cli.register_command(app)
    def test_func(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
        return input * mask

    # Verify the command was registered
    assert len(app.registered_commands) == 1
