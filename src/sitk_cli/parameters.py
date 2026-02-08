"""Parameter translation and CLI signature building."""

from __future__ import annotations

from inspect import Parameter, Signature, signature
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import SimpleITK as sitk
import typer

from .constants import FORCE_PARAM_NAME, VERBOSE_PARAM_NAME
from .introspection import (
    find_image_transform_params,
    parse_annotation,
    resolve_type_hints,
)

if TYPE_CHECKING:
    from inspect import _ParameterKind

    from .lib import FuncType, SitkImageOrTransform

    ParameterKindType = _ParameterKind


class OutputParamConfig(NamedTuple):
    """Configuration for output parameter."""

    default: typer.models.ArgumentInfo | None
    kind: ParameterKindType


class TranslatedParam(NamedTuple):
    """Result of translating Image/Transform parameter to Path."""

    parameter: Parameter
    is_positional: bool


class CLISignatureInfo(NamedTuple):
    """Information about the CLI signature being built."""

    signature: Signature
    positional_params: list[Parameter]
    keyword_only_params: list[Parameter]
    output_param: Parameter | None
    image_args: list[str]
    transform_args: list[str]
    image_transform_params: dict[str, type]
    optional_params: set[str]
    has_positional_input: bool
    has_any_positional_or_keyword: bool


def determine_output_param_config(
    has_positional_input: bool,
    has_any_image_transform_input: bool,
    has_any_positional_or_keyword: bool,
) -> OutputParamConfig:
    """Determine output parameter default (Argument/Option) and kind."""
    # Output is positional if:
    # 1. There's at least one positional Image/Transform input, OR
    # 2. There are no Image/Transform inputs at all (e.g., generator functions)
    # Output is named only when ALL Image/Transform inputs are keyword-only
    output_default = (
        typer.Argument(...)
        if (has_positional_input or not has_any_image_transform_input)
        else None
    )
    # Output kind should match - keyword-only if all params are keyword-only
    output_kind = (
        Parameter.KEYWORD_ONLY
        if not has_any_positional_or_keyword
        else Parameter.POSITIONAL_OR_KEYWORD
    )
    return OutputParamConfig(output_default, output_kind)


def translate_image_transform_param(
    param: Parameter,
    param_type: SitkImageOrTransform,
    is_optional: bool,
) -> TranslatedParam:
    """Translate Image/Transform parameter to Path parameter.

    Args:
        param: Original parameter
        param_type: SimpleITK Image or Transform type
        is_optional: Whether parameter is optional (has default or Union with None)
    """
    is_keyword_only = param.kind == Parameter.KEYWORD_ONLY
    is_positional = False
    default: typer.models.OptionInfo | typer.models.ArgumentInfo
    kind: ParameterKindType

    # Determine default value and kind based on parameter kind and optionality
    if is_keyword_only:
        # Keyword-only parameter (after *, in signature) is always named
        default = typer.Option(None) if is_optional else typer.Option(...)
        kind = Parameter.KEYWORD_ONLY
    elif param.default is Parameter.empty and not is_optional:
        # Required positional Image/Transform without default
        default = typer.Argument(...)
        is_positional = True
        kind = Parameter.POSITIONAL_OR_KEYWORD
    elif is_optional:
        # Named: optional Image/Transform
        default = typer.Option(None)
        kind = Parameter.POSITIONAL_OR_KEYWORD
    else:
        # Named: Image/Transform with non-None default
        default = typer.Option(...)
        kind = Parameter.POSITIONAL_OR_KEYWORD

    new_param = Parameter(
        param.name,
        kind,
        annotation=Path,
        default=default,
    )
    return TranslatedParam(new_param, is_positional)


def build_cli_signature(
    func: FuncType,
    output_arg_name: str,
    verbose: bool,
    overwrite: bool | str,
) -> CLISignatureInfo:
    """Build CLI signature from function signature.

    Translates Image/Transform parameters to Path, adds output parameter if needed.
    """
    func_sig = signature(func)
    type_hints = resolve_type_hints(func)

    # Find Image/Transform parameters
    image_transform_params, optional_params = find_image_transform_params(
        func_sig, type_hints
    )

    # Track which parameters need file I/O
    image_args: list[str] = []
    transform_args: list[str] = []
    has_positional_input = False
    has_any_image_transform_input = bool(image_transform_params)
    has_any_positional_or_keyword = False

    # Build parameter lists
    positional_params: list[Parameter] = []
    keyword_only_params: list[Parameter] = []

    for param in func_sig.parameters.values():
        if param.name in image_transform_params:
            # Image/Transform parameter - translate to Path
            param_type = image_transform_params[param.name]
            is_optional = param.name in optional_params

            # Track for file I/O
            if issubclass(param_type, sitk.Image):
                image_args.append(param.name)
            else:
                transform_args.append(param.name)

            # Translate parameter
            translated = translate_image_transform_param(param, param_type, is_optional)
            if translated.parameter.kind == Parameter.KEYWORD_ONLY:
                keyword_only_params.append(translated.parameter)
            else:
                positional_params.append(translated.parameter)
                has_any_positional_or_keyword = True
            if translated.is_positional:
                has_positional_input = True
        elif param.default == Parameter.empty:
            # Non-Image/Transform required parameters stay as named options
            # Get resolved annotation from type_hints if available, otherwise use raw
            annotation = type_hints.get(param.name, param.annotation)
            annotation = parse_annotation(annotation)
            new_param = Parameter(
                param.name,
                param.kind,
                annotation=annotation,
                default=typer.Option(...),
            )
            if new_param.kind == Parameter.KEYWORD_ONLY:
                keyword_only_params.append(new_param)
            else:
                positional_params.append(new_param)
                has_any_positional_or_keyword = True
        else:
            # Keep other parameters as-is
            # Get resolved annotation from type_hints if available, otherwise use raw
            annotation = type_hints.get(param.name, param.annotation)
            annotation = parse_annotation(annotation)
            new_param = Parameter(
                param.name,
                param.kind,
                annotation=annotation,
                default=param.default,
            )
            if new_param.kind == Parameter.KEYWORD_ONLY:
                keyword_only_params.append(new_param)
            else:
                positional_params.append(new_param)
                has_any_positional_or_keyword = True

    # Determine output parameter
    # Get resolved return annotation from type_hints
    return_annotation = type_hints.get("return", func_sig.return_annotation)
    return_type = parse_annotation(return_annotation)
    output_param: Parameter | None = None
    if (
        return_type
        and isinstance(return_type, type)
        and issubclass(return_type, (sitk.Image, sitk.Transform))
    ):
        config = determine_output_param_config(
            has_positional_input,
            has_any_image_transform_input,
            has_any_positional_or_keyword,
        )
        output_param = Parameter(
            output_arg_name,
            kind=config.kind,
            default=config.default,
            annotation=Path,
        )
        return_type = None  # Clear return type since we have output file

    # Build final parameter list
    params: list[Parameter] = positional_params.copy()
    if output_param and output_param.kind != Parameter.KEYWORD_ONLY:
        params.append(output_param)
    params.extend(keyword_only_params)
    if output_param and output_param.kind == Parameter.KEYWORD_ONLY:
        params.append(output_param)

    # Add verbose parameter if requested
    if verbose:
        verbose_kind = (
            Parameter.KEYWORD_ONLY
            if not has_any_positional_or_keyword
            else Parameter.POSITIONAL_OR_KEYWORD
        )
        params.append(
            Parameter(
                VERBOSE_PARAM_NAME,
                kind=verbose_kind,
                default=typer.Option(
                    0,
                    "--verbose",
                    "-v",
                    count=True,
                    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
                ),
                annotation=int,
            )
        )

    # Add force flag if overwrite protection is enabled
    if overwrite is not True:
        force_kind = (
            Parameter.KEYWORD_ONLY
            if not has_any_positional_or_keyword
            else Parameter.POSITIONAL_OR_KEYWORD
        )
        params.append(
            Parameter(
                FORCE_PARAM_NAME,
                kind=force_kind,
                default=typer.Option(
                    False,
                    "--force",
                    "-f",
                    help="Force overwrite of existing output files",
                ),
                annotation=bool,
            )
        )

    new_sig = func_sig.replace(parameters=params, return_annotation=return_type)

    return CLISignatureInfo(
        signature=new_sig,
        positional_params=positional_params,
        keyword_only_params=keyword_only_params,
        output_param=output_param,
        image_args=image_args,
        transform_args=transform_args,
        image_transform_params=image_transform_params,
        optional_params=optional_params,
        has_positional_input=has_positional_input,
        has_any_positional_or_keyword=has_any_positional_or_keyword,
    )
