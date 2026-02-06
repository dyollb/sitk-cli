"""Batch processing utilities for sitk-cli."""

from __future__ import annotations

import types
from collections import defaultdict
from inspect import Parameter, signature
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Union, get_type_hints

import SimpleITK as sitk
import typer
from makefun import wraps

if TYPE_CHECKING:
    from .lib import FuncType

_OUTPUT_DIR_ARG: Final = typer.Argument(..., help="Output directory")


def _get_stem_and_suffix(path: Path) -> tuple[str, str]:
    """Get stem and suffix handling multi-part extensions like .nii.gz.

    Args:
        path: File path to parse

    Returns:
        Tuple of (stem, suffix) where suffix includes all extensions

    Examples:
        brain.nii.gz -> ('brain', '.nii.gz')
        image.nii -> ('image', '.nii')
        data.tar.gz -> ('data', '.tar.gz')
    """
    suffix = "".join(path.suffixes)
    stem = path.name.removesuffix(suffix)
    return stem, suffix


def _get_default_glob(param_type: type) -> str:
    """Get default glob pattern for Image or Transform types."""
    if issubclass(param_type, sitk.Transform):
        return "*.tfm"
    # Default for Image
    return "*.nii.gz"


def create_batch_command(
    func: FuncType,
    output_template: str = "{stem}{suffix}",
    output_stem: str | None = None,
) -> FuncType:
    """Create a batch processing command from a function.

    Converts a function that processes single Image/Transform files into one that
    processes directories of files. Input directories are globbed and matched by stem.

    Args:
        func: Processing function with Image/Transform parameters
        output_template: Template for output filenames. Variables: {stem}, {suffix}, {name}
        output_stem: Which parameter to use for output naming (default: first Image/Transform)

    Returns:
        Batch processing function

    Examples:
        >>> def filter(input: sitk.Image, radius: int = 2) -> sitk.Image:
        ...     return sitk.Median(input, [radius] * input.GetDimension())
        >>> batch_filter = create_batch_command(filter)
        >>> # CLI: batch_filter input_dir/ output_dir/ --radius 3

        >>> def register(fixed: sitk.Image, moving: sitk.Image) -> sitk.Transform:
        ...     # registration code
        ...     return transform
        >>> batch_register = create_batch_command(register, output_stem="moving")
        >>> # CLI: batch_register fixed.nii movings_dir/ outputs_dir/
        >>> # Uses fixed.nii for all, globs movings_dir/*.nii.gz
    """
    func_sig = signature(func)

    # Get type hints (handles "from __future__ import annotations")
    try:
        type_hints = get_type_hints(func)
    except Exception:
        # Fallback if get_type_hints fails
        type_hints = {}

    # Find Image/Transform parameters and track optional ones
    image_transform_params: dict[str, type] = {}
    optional_params: set[str] = set()

    for param_name, param in func_sig.parameters.items():
        annotation = type_hints.get(param_name)
        if annotation is None:
            continue

        # Check if parameter has a default value (is optional)
        param_is_optional = param.default is not param.empty

        # Handle Union types (e.g., Image | None)
        # Python 3.10+: types.UnionType (from X | Y syntax)
        # Python 3.9-: typing.Union (from Union[X, Y] syntax)
        origin = getattr(annotation, "__origin__", None)
        is_union = origin is Union or isinstance(annotation, types.UnionType)

        if is_union:
            # Extract non-None types from Union
            args = getattr(annotation, "__args__", ())
            non_none_types = [t for t in args if t is not type(None)]
            if len(non_none_types) == 1:
                annotation = non_none_types[0]
                param_is_optional = True  # Union with None means optional

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

    # Determine which parameter drives output naming
    if output_stem is None:
        # Use first positional Image/Transform parameter
        for param_name in image_transform_params:
            output_stem = param_name
            break

    if not image_transform_params:
        msg = "Function must have at least one Image or Transform parameter"
        raise ValueError(msg)

    if output_stem not in image_transform_params:
        msg = f"output_stem '{output_stem}' not found in Image/Transform parameters"
        raise ValueError(msg)

    # Build new signature for batch wrapper
    # Separate parameters by kind to maintain proper ordering
    positional_params: list[Parameter] = []
    keyword_only_params: list[Parameter] = []

    # Convert Image/Transform parameters to Path arguments
    for param_name, param in func_sig.parameters.items():
        if param_name in image_transform_params:
            # Image/Transform → Path argument with help text
            param_type = image_transform_params[param_name]
            glob_pattern = _get_default_glob(param_type)

            # Build help text
            if param_name in optional_params:
                help_text = f"Directory (glob: {glob_pattern}) or file. Optional, matched by stem if directory."
                default = typer.Argument(None, help=help_text)
            else:
                help_text = f"Directory (glob: {glob_pattern}) or file."
                default = typer.Argument(..., help=help_text)

            positional_params.append(
                Parameter(
                    param_name,
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Path,
                    default=default,
                )
            )
        elif param.kind == Parameter.KEYWORD_ONLY:
            # Keep keyword-only parameters as keyword-only
            keyword_only_params.append(param)
        else:
            # Keep other positional/keyword parameters
            positional_params.append(param)

    # Add output_dir parameter (positional/keyword)
    positional_params.append(
        Parameter(
            "output_dir",
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Path,
            default=_OUTPUT_DIR_ARG,
        )
    )

    # Combine parameters in correct order: positional/keyword, then keyword-only
    new_params = positional_params + keyword_only_params

    new_sig = func_sig.replace(parameters=new_params, return_annotation=None)

    @wraps(func, new_sig=new_sig)  # type: ignore[misc,untyped-decorator]
    def batch_wrapper(*args: Any, **kwargs: Any) -> None:
        """Process multiple files in batch."""
        # Extract output_dir from kwargs
        output_dir: Path = kwargs.pop("output_dir")

        # Build arg_map from both args and kwargs
        param_names = list(func_sig.parameters.keys())
        arg_map: dict[str, Path] = {}

        # First, handle positional args
        for i, arg in enumerate(args):
            if i < len(param_names):
                arg_map[param_names[i]] = arg

        # Then, handle Image/Transform parameters from kwargs
        for param_name in image_transform_params:
            if param_name in kwargs:
                arg_map[param_name] = kwargs.pop(param_name)

        # Remaining kwargs are the non-Image/Transform parameters (radius, etc.)

        # Collect files for each Image/Transform parameter
        # Separate single files from directory-based file lists
        single_files: dict[str, Path] = {}  # Params with single files (reused)
        dir_files: dict[str, list[Path]] = {}  # Params with directory globs

        for param_name, param_type in image_transform_params.items():
            path = arg_map.get(param_name)
            if path is None:
                continue

            # Handle optional parameters: typer.Argument(None) becomes ArgumentInfo object
            # when not provided, treat as None
            if isinstance(path, typer.models.ArgumentInfo):
                continue

            if path.is_file():
                # Single file - will be reused for all iterations
                single_files[param_name] = path
            elif path.is_dir():
                # Directory - glob for files
                glob_pattern = _get_default_glob(param_type)
                files = sorted(path.glob(glob_pattern))
                if not files:
                    print(f"Warning: No files found matching {path}/{glob_pattern}")
                    return
                dir_files[param_name] = files
            else:
                msg = f"Path does not exist: {path}"
                raise FileNotFoundError(msg)

        # Match files by stem across directory-based params
        if dir_files:
            stem_to_files: dict[str, dict[str, Path]] = defaultdict(dict)

            for param_name, files in dir_files.items():
                for file_path in files:
                    stem, _ = _get_stem_and_suffix(file_path)
                    stem_to_files[stem][param_name] = file_path

            # Filter to complete matches
            # Required params must have files for all stems
            # Optional params can be missing for some stems
            required_dir_params = {p for p in dir_files if p not in optional_params}

            complete_matches = {
                stem: files
                for stem, files in stem_to_files.items()
                if all(p in files for p in required_dir_params)
            }

            if not complete_matches:
                print("Error: No matching files found across directory inputs")
                print(f"Directory parameters: {list(dir_files.keys())}")
                return
        else:
            # No directory inputs - only single files
            if not single_files:
                print("Error: No input files provided")
                return
            # Process once with the single files
            complete_matches = {"single": {}}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Process each matched set
        total = len(complete_matches)
        for idx, (stem, matched_files) in enumerate(complete_matches.items(), 1):
            # Combine single files with matched directory files
            all_files = {**single_files, **matched_files}

            # Get template variables from output_stem file
            output_file_ref = all_files[output_stem]
            _, suffix = _get_stem_and_suffix(output_file_ref)

            # Format output filename
            output_name = output_template.format(
                stem=stem,
                suffix=suffix,
                name=output_file_ref.name,
            )
            output_path = output_dir / output_name

            print(f"[{idx}/{total}] Processing {stem}...")

            # Build function arguments
            func_args: dict[str, Any] = {}
            for param_name, file_path in all_files.items():
                param_type = image_transform_params[param_name]
                if issubclass(param_type, sitk.Image):
                    func_args[param_name] = sitk.ReadImage(str(file_path))
                elif issubclass(param_type, sitk.Transform):
                    func_args[param_name] = sitk.ReadTransform(str(file_path))

            # Add other kwargs (like radius, threshold, etc.)
            func_args.update(kwargs)

            # Execute function
            result = func(**func_args)

            # Save result
            if result is not None:
                if isinstance(result, sitk.Image):
                    sitk.WriteImage(result, str(output_path))
                elif isinstance(result, sitk.Transform):
                    sitk.WriteTransform(result, str(output_path))
                print(f"  → Saved to {output_path.name}")

        print(f"\nCompleted {total} files")

    return batch_wrapper
