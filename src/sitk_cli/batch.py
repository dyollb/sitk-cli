"""Batch processing wrapper for sitk-cli."""

from __future__ import annotations

from collections import defaultdict
from inspect import Parameter, signature
from pathlib import Path
from typing import TYPE_CHECKING, Any

import SimpleITK as sitk
import typer
from makefun import wraps

from .constants import (
    DEFAULT_IMAGE_GLOB,
    DEFAULT_TRANSFORM_GLOB,
    FORCE_PARAM_NAME,
    VERBOSE_PARAM_NAME,
)
from .introspection import is_typer_default

if TYPE_CHECKING:
    from .lib import FuncType


def get_stem_and_suffix(path: Path) -> tuple[str, str]:
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


def get_default_glob(param_type: type) -> str:
    """Get default glob pattern for Image or Transform types.

    Args:
        param_type: SimpleITK Image or Transform type

    Returns:
        Glob pattern string
    """
    if issubclass(param_type, sitk.Transform):
        return DEFAULT_TRANSFORM_GLOB
    # Default for Image
    return DEFAULT_IMAGE_GLOB


def create_batch_wrapper(
    func: FuncType,
    func_wrapper: FuncType,
    positional_params: list[Parameter],
    keyword_only_params: list[Parameter],
    output_param: Parameter | None,
    image_transform_params: dict[str, type],
    optional_params: set[str],
    output_arg_name: str,
    output_template: str,
    output_stem: str | None,
    all_params: list[Parameter],
) -> FuncType:
    """Create batch processing wrapper around single-file CLI.

    Args:
        func: Original function
        func_wrapper: Single-file CLI wrapper
        positional_params: Positional/keyword parameters
        keyword_only_params: Keyword-only parameters
        output_param: Output parameter if function returns Image/Transform
        image_transform_params: Map of Image/Transform parameter names to types
        optional_params: Set of optional parameter names
        output_arg_name: Name of output parameter
        output_template: Template for output filenames
        output_stem: Parameter to use for output naming
        all_params: All CLI parameters (may include _verbose and _force)

    Returns:
        Batch processing wrapper function
    """
    func_sig = signature(func)

    # Determine output stem parameter
    if output_stem is None and image_transform_params:
        output_stem = next(iter(image_transform_params.keys()))

    # Check if output is needed
    has_output = output_param is not None

    # Build batch signature
    batch_params: list[Parameter] = []
    for param in positional_params:
        batch_params.append(param)

    # Add output_dir if function returns Image/Transform
    if has_output:
        batch_params.append(
            Parameter(
                "output_dir",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Path,
                default=typer.Argument(..., help="Output directory"),
            )
        )

    # Add keyword-only params
    batch_params.extend(keyword_only_params)

    # Add output_template option if has output
    if has_output:
        batch_params.append(
            Parameter(
                "output_template",
                Parameter.KEYWORD_ONLY,
                annotation=str,
                default=typer.Option(
                    output_template,
                    help=f"Output filename template. Variables: {{stem}}, {{suffix}}, {{name}}. Default: {output_template}",
                ),
            )
        )

    # Add verbose and force parameters if they exist
    for param in all_params:
        if param.name in (VERBOSE_PARAM_NAME, FORCE_PARAM_NAME):
            batch_params.append(param)

    batch_sig = func_sig.replace(parameters=batch_params, return_annotation=None)

    @wraps(func, new_sig=batch_sig)  # type: ignore[misc,untyped-decorator]
    def batch_wrapper(*args: Any, **kwargs: Any) -> None:
        """Batch process multiple files."""
        # Extract batch-specific parameters
        out_dir: Path | None = None
        template: str = output_template
        if has_output:
            out_dir = kwargs.pop("output_dir")
            tmpl_arg = kwargs.pop("output_template")
            if not is_typer_default(tmpl_arg):
                template = tmpl_arg

        # Build argument map from args
        param_names = list(func_sig.parameters)
        arg_map: dict[str, Path] = {}
        for i, arg in enumerate(args):
            if i < len(param_names):
                arg_map[param_names[i]] = arg

        # Add from kwargs
        for pname in image_transform_params:
            if pname in kwargs:
                val = kwargs.pop(pname)
                if not is_typer_default(val):
                    arg_map[pname] = val

        # Separate single files from directory globs
        single_files: dict[str, Path] = {}
        dir_files: dict[str, list[Path]] = {}

        for pname, ptype in image_transform_params.items():
            if pname not in arg_map:
                continue
            path = arg_map[pname]

            if path.is_file():
                single_files[pname] = path
            elif path.is_dir():
                glob_pattern = get_default_glob(ptype)
                files = sorted(path.glob(glob_pattern))
                if not files:
                    print(f"Warning: No files found matching {path}/{glob_pattern}")
                    return
                dir_files[pname] = files
            else:
                msg = f"Path does not exist: {path}"
                raise FileNotFoundError(msg)

        # Match files by stem
        if dir_files:
            stem_to_files: dict[str, dict[str, Path]] = defaultdict(dict)
            for pname, files in dir_files.items():
                for fpath in files:
                    stem, _ = get_stem_and_suffix(fpath)
                    stem_to_files[stem][pname] = fpath

            # Filter complete matches
            required_dir_params = {p for p in dir_files if p not in optional_params}
            complete_matches = {
                stem: files
                for stem, files in stem_to_files.items()
                if all(p in files for p in required_dir_params)
            }

            if not complete_matches:
                print("Error: No matching files found")
                return
        else:
            complete_matches = {"single": {}}

        # Create output dir if needed
        if has_output and out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

        # Process each match
        total = len(complete_matches)
        for idx, (stem, matched) in enumerate(complete_matches.items(), 1):
            all_files = {**single_files, **matched}

            # Prepare output path
            out_path: Path | None = None
            if has_output and out_dir:
                assert output_stem is not None  # nosec
                ref_file = all_files[output_stem]
                _, suffix = get_stem_and_suffix(ref_file)
                out_name = template.format(stem=stem, suffix=suffix, name=ref_file.name)
                out_path = out_dir / out_name

            print(f"[{idx}/{total}] Processing {stem}...")

            # Call single-file wrapper with individual file paths
            call_kwargs = {**kwargs}  # Other params (radius, etc.)
            call_kwargs.update(all_files)  # Image/Transform params as Paths
            if out_path:
                call_kwargs[output_arg_name] = out_path

            func_wrapper(**call_kwargs)

            if out_path:
                print(f"  → Saved to {out_path.name}")

        print(f"\nCompleted {total} files")

    return batch_wrapper
