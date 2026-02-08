from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeAlias

import SimpleITK as sitk
import typer  # noqa: TC002 (needed at runtime for @app.command())
from makefun import wraps

from .batch import create_batch_wrapper
from .constants import DEFAULT_OUTPUT_ARG_NAME, FORCE_PARAM_NAME, VERBOSE_PARAM_NAME
from .introspection import is_typer_default
from .parameters import build_cli_signature

# Type aliases
SitkImageOrTransform: TypeAlias = type[sitk.Image] | type[sitk.Transform]
FuncType: TypeAlias = Callable[..., Any]
DecoratorType: TypeAlias = Callable[[FuncType], FuncType]


def _load_sitk_file(
    file_path: Path, param_type: SitkImageOrTransform
) -> sitk.Image | sitk.Transform:
    """Load SimpleITK Image or Transform from file.

    Raises FileNotFoundError if file doesn't exist.
    """
    if not file_path.exists():
        type_name = "image" if param_type is sitk.Image else "transform"
        msg = f"Input {type_name} file not found: {file_path}"
        raise FileNotFoundError(msg)

    if param_type is sitk.Image:
        return sitk.ReadImage(str(file_path))
    return sitk.ReadTransform(str(file_path))


def _save_sitk_file(
    obj: sitk.Image | sitk.Transform,
    output_file: Path,
    *,
    overwrite: bool | Literal["prompt"],
    force: bool,
    create_dirs: bool,
) -> None:
    """Save SimpleITK Image or Transform to file.

    Raises FileExistsError if file exists and overwrite protection enabled.
    """
    # Check for overwrite protection
    if overwrite is not True and not force and output_file.exists():
        if overwrite == "prompt":
            # Interactive prompt
            response = input(f"Output file '{output_file}' exists. Overwrite? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                print("Operation cancelled.")
                return
        else:  # overwrite is False
            msg = (
                f"Output file '{output_file}' already exists. Use --force to overwrite."
            )
            raise FileExistsError(msg)

    if create_dirs:
        output_file.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(obj, sitk.Image):
        sitk.WriteImage(obj, str(output_file))
    else:
        sitk.WriteTransform(obj, str(output_file))


def create_command(
    func: FuncType,
    batch: bool = False,
    output_arg_name: str = DEFAULT_OUTPUT_ARG_NAME,
    output_template: str = "{stem}{suffix}",
    output_stem: str | None = None,
    create_dirs: bool = True,
    verbose: bool = False,
    overwrite: bool | Literal["prompt"] = True,
) -> FuncType:
    """Create command line interface from function with sitk.Image args.

    Transforms a function that uses SimpleITK Image/Transform objects into a CLI
    that accepts file paths. Automatically handles loading from and saving to files.

    Single-file behavior:
        - Required Image/Transform parameters → positional arguments
        - Keyword-only Image/Transform parameters (after *,) → named options
        - Optional Image/Transform parameters (with defaults) → named options
        - Output → positional if ANY input is positional, otherwise named

    Batch mode behavior (batch=True):
        - Image/Transform parameters accept directories or files
        - Directories are globbed and matched by filename stem
        - Single files are reused across all matches
        - Adds output_dir and output_template parameters

    Args:
        func: Function to wrap with CLI functionality
        batch: Enable batch processing mode (default: False)
        output_arg_name: Name for output file parameter in single-file mode (default: "output")
        output_template: Template for output filenames in batch mode (default: "{stem}{suffix}")
            Variables: {stem}, {suffix}, {name}
        output_stem: Which parameter drives output naming in batch mode (default: first Image/Transform param)
        create_dirs: Auto-create parent directories for output files (default: True)
        verbose: Add --verbose/-v flag for logging control (default: False)
        overwrite: Control output file overwrite behavior (default: True)
            - True: Always overwrite existing files
            - False: Error if output file exists (adds --force flag to override)
            - "prompt": Ask user interactively (adds --force flag to skip prompt)
        globals: Global namespace for evaluating string annotations
        locals: Local namespace for evaluating string annotations

    Returns:
        Wrapped function that accepts Path arguments and handles file I/O

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If annotation parsing fails

    Examples:
        Single-file mode:
        >>> def process(input: sitk.Image) -> sitk.Image:
        ...     return input
        >>> cli = create_command(process)
        # CLI: process INPUT OUTPUT

        Batch mode:
        >>> cli_batch = create_command(process, batch=True)
        # CLI: process INPUT_DIR/ OUTPUT_DIR/

        >>> def process(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
        ...     return input * mask
        >>> cli = create_command(process)
        # CLI: process INPUT OUTPUT --mask MASK
    """
    # Build CLI signature using parameters module
    sig_info = build_cli_signature(
        func=func,
        output_arg_name=output_arg_name,
        verbose=verbose,
        overwrite=overwrite,
    )

    # Extract info from signature
    image_transform_params = sig_info.image_transform_params
    optional_params = sig_info.optional_params
    image_args = sig_info.image_args
    transform_args = sig_info.transform_args

    # Create single-file wrapper
    @wraps(func, new_sig=sig_info.signature)  # type: ignore[misc,untyped-decorator]
    def func_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Configure logging based on verbosity level
        if verbose and VERBOSE_PARAM_NAME in kwargs:
            verbose_level = kwargs.pop(VERBOSE_PARAM_NAME)
            logger = logging.getLogger("sitk_cli")
            if verbose_level == 1:
                logger.setLevel(logging.INFO)
            elif verbose_level >= 2:
                logger.setLevel(logging.DEBUG)

        output_file: Path | None = None
        force: bool = False
        kwargs_inner: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k == output_arg_name:
                output_file = v
                continue
            if k == FORCE_PARAM_NAME:
                force = bool(v.default if is_typer_default(v) else v)
                continue
            if k in image_args and isinstance(v, Path):
                v = _load_sitk_file(v, sitk.Image)
            elif k in transform_args and isinstance(v, Path):
                v = _load_sitk_file(v, sitk.Transform)
            kwargs_inner[k] = v

        ret = func(*args, **kwargs_inner)
        if output_file and ret:
            _save_sitk_file(
                ret,
                output_file,
                overwrite=overwrite,
                force=force,
                create_dirs=create_dirs,
            )
        return ret

    # If batch mode, wrap with batch processing logic
    if batch:
        return create_batch_wrapper(
            func=func,
            func_wrapper=func_wrapper,
            positional_params=sig_info.positional_params,
            keyword_only_params=sig_info.keyword_only_params,
            output_param=sig_info.output_param,
            image_transform_params=image_transform_params,
            optional_params=optional_params,
            output_arg_name=output_arg_name,
            output_template=output_template,
            output_stem=output_stem,
            all_params=list(sig_info.signature.parameters.values()),
        )

    return func_wrapper


def make_cli(
    func: FuncType,
    batch: bool = False,
    output_arg_name: str = DEFAULT_OUTPUT_ARG_NAME,
    output_template: str = "{stem}{suffix}",
    output_stem: str | None = None,
    create_dirs: bool = True,
    verbose: bool = False,
    overwrite: bool | Literal["prompt"] = True,
) -> FuncType:
    """Deprecated: Use create_command instead.

    This function is deprecated and will be removed in a future version.
    Please use create_command() instead.
    """
    warnings.warn(
        "make_cli() is deprecated, use create_command() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_command(
        func=func,
        batch=batch,
        output_arg_name=output_arg_name,
        output_template=output_template,
        output_stem=output_stem,
        create_dirs=create_dirs,
        verbose=verbose,
        overwrite=overwrite,
    )


def register_command(
    app: typer.Typer,
    func_name: str | None = None,
    batch: bool = False,
    output_arg_name: str = DEFAULT_OUTPUT_ARG_NAME,
    output_template: str = "{stem}{suffix}",
    output_stem: str | None = None,
    create_dirs: bool = True,
    verbose: bool = False,
    overwrite: bool | Literal["prompt"] = True,
) -> DecoratorType:
    """Register a function as a Typer command.

    Decorator that wraps a function with create_command and registers it with a Typer app.

    Args:
        app: Typer application instance to register the command with
        func_name: Custom name for the command (default: use function name)
        batch: Enable batch processing mode (default: False)
        output_arg_name: Name for output file parameter in single-file mode (default: "output")
        output_template: Template for output filenames in batch mode (default: "{stem}{suffix}")
        output_stem: Which parameter drives output naming in batch mode (default: first Image/Transform param)
        create_dirs: Auto-create parent directories for output files (default: True)
        verbose: Add --verbose/-v flag for logging control (default: False)
        overwrite: Control output file overwrite behavior (default: True)
            - True: Always overwrite existing files
            - False: Error if output file exists (adds --force flag to override)
            - "prompt": Ask user interactively (adds --force flag to skip prompt)

    Returns:
        Decorator function that registers and returns the original function

    Examples:
        Single-file mode:
        >>> @register_command(app)
        ... def process(input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process INPUT OUTPUT

        Batch mode:
        >>> @register_command(app, batch=True)
        ... def process(input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process INPUT_DIR/ OUTPUT_DIR/

        >>> @register_command(app)
        ... def process(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
        ...     return input * mask
        # CLI: process INPUT OUTPUT --mask MASK
    """

    def decorator(func: FuncType) -> FuncType:
        func_cli = create_command(
            func,
            batch=batch,
            output_arg_name=output_arg_name,
            output_template=output_template,
            output_stem=output_stem,
            create_dirs=create_dirs,
            verbose=verbose,
            overwrite=overwrite,
        )

        @app.command()
        @wraps(func_cli, func_name=func_name)  # type: ignore[misc,untyped-decorator,arg-type]
        def foo(*args: Any, **kwargs: Any) -> Any:
            return func_cli(*args, **kwargs)

        return func

    return decorator
