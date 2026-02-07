"""Type introspection utilities for sitk-cli."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

import SimpleITK as sitk
import typer

if TYPE_CHECKING:
    from inspect import Signature


def resolve_type_hints(func: Any) -> dict[str, Any]:
    """Resolve type hints, handling 'from __future__ import annotations'.

    Args:
        func: Function to get type hints from

    Returns:
        Dictionary of parameter names to resolved type annotations

    Raises:
        TypeError: If object is not a class, module, or function
    """
    return get_type_hints(func)


def parse_annotation(
    annotation: Any,
    globals_dict: dict[str, Any] | None = None,
    locals_dict: dict[str, Any] | None = None,
) -> Any:
    """Parse type annotation, handling string annotations and Optional/Union types.

    Args:
        annotation: Type annotation to parse
        globals_dict: Global namespace for evaluating string annotations
        locals_dict: Local namespace for evaluating string annotations

    Returns:
        Resolved type annotation (non-None type extracted from Union)

    Raises:
        ValueError: If string annotation evaluation fails
    """
    if isinstance(annotation, str):
        try:
            annotation = eval(annotation, globals_dict, locals_dict)
        except Exception as e:
            msg = f"Failed to parse type annotation '{annotation}': {e}"
            raise ValueError(msg) from e

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is not None:
        for arg in args:
            if arg is not type(None):
                return arg
    return annotation


def resolve_optional_type(annotation: Any, has_default: bool) -> tuple[Any, bool]:
    """Resolve Optional/Union types to extract the base type and optionality.

    Args:
        annotation: Type annotation to resolve
        has_default: Whether the parameter has a default value

    Returns:
        Tuple of (resolved_type, is_optional)
    """
    param_is_optional = has_default

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is not None:
        # Union type - extract non-None types
        non_none_types = [t for t in args if t is not type(None)]
        if len(non_none_types) == 1:
            return non_none_types[0], True

    return annotation, param_is_optional


def find_image_transform_params(
    func_sig: Signature, type_hints: dict[str, Any]
) -> tuple[dict[str, type], set[str]]:
    """Find Image and Transform parameters in function signature.

    Args:
        func_sig: Function signature to inspect
        type_hints: Resolved type hints for the function

    Returns:
        Tuple of (image_transform_params, optional_params) where:
        - image_transform_params: dict mapping param name to Image/Transform type
        - optional_params: set of param names that are optional
    """
    image_transform_params: dict[str, type] = {}
    optional_params: set[str] = set()

    for param_name, param in func_sig.parameters.items():
        annotation = type_hints.get(param_name)
        if annotation is None:
            continue

        # Resolve optional types
        annotation, param_is_optional = resolve_optional_type(
            annotation, param.default is not param.empty
        )

        # Check if annotation is Image or Transform class
        if annotation is sitk.Image or annotation is sitk.Transform:
            image_transform_params[param_name] = annotation
            if param_is_optional:
                optional_params.add(param_name)
        elif isinstance(annotation, type):
            try:
                if issubclass(annotation, (sitk.Image, sitk.Transform)):
                    image_transform_params[param_name] = annotation
                    if param_is_optional:
                        optional_params.add(param_name)
            except TypeError:
                # Handle cases where issubclass fails
                pass

    return image_transform_params, optional_params


def is_typer_default(value: Any) -> bool:
    """Check if value is a typer default (not user-provided).

    Args:
        value: Value to check

    Returns:
        True if value is a typer OptionInfo or ArgumentInfo object
    """
    return isinstance(value, (typer.models.OptionInfo, typer.models.ArgumentInfo))
