from __future__ import annotations

import logging
from collections.abc import Callable
from inspect import Parameter, isclass, signature
from pathlib import Path
from typing import Any, Literal, TypeAlias

import SimpleITK as sitk
import typer
from makefun import wraps

from .utils import is_typer_default, parse_annotation

# Type aliases
SitkImageOrTransform: TypeAlias = type[sitk.Image] | type[sitk.Transform]
FuncType: TypeAlias = Callable[..., Any]
DecoratorType: TypeAlias = Callable[[FuncType], FuncType]


def make_cli(
    func: FuncType,
    output_arg_name: str = "output",
    create_dirs: bool = True,
    verbose: bool = False,
    overwrite: bool | Literal["prompt"] = True,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
) -> FuncType:
    """Make command line interface from function with sitk.Image args.

    Transforms a function that uses SimpleITK Image/Transform objects into a CLI
    that accepts file paths. Automatically handles loading from and saving to files.

    Behavior:
        - Required Image/Transform parameters → positional arguments
        - Keyword-only Image/Transform parameters (after *,) → named options
        - Optional Image/Transform parameters (with defaults) → named options
        - Output → positional if ANY input is positional, otherwise named

    Args:
        func: Function to wrap with CLI functionality
        output_arg_name: Name for the output file parameter (default: "output")
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
        >>> def process(input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process INPUT OUTPUT

        >>> def process(*, input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process --input INPUT --output OUTPUT

        >>> def process(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
        ...     return input * mask
        # CLI: process INPUT OUTPUT --mask MASK
    """
    image_args: list[str] = []
    transform_args: list[str] = []
    has_positional_input = (
        False  # Track if we see any positional Image/Transform inputs
    )
    has_any_image_transform_input = (
        False  # Track if we see any Image/Transform inputs at all
    )

    def _translate_param(p: Parameter) -> Parameter:
        """Translate function parameters for CLI compatibility.

        Converts SimpleITK Image/Transform parameters to Path parameters,
        tracks which parameters need file I/O, and sets appropriate defaults.
        Uses Typer convention: Argument() for positional, Option() for named.
        Respects Python's keyword-only parameters (after *,).
        """
        nonlocal has_positional_input, has_any_image_transform_input
        annotation = parse_annotation(p.annotation, globals, locals)
        default = p.default
        is_keyword_only = p.kind == Parameter.KEYWORD_ONLY

        if isclass(annotation) and issubclass(annotation, (sitk.Image, sitk.Transform)):
            has_any_image_transform_input = True
            if issubclass(annotation, sitk.Image):
                image_args.append(p.name)
            else:
                transform_args.append(p.name)
            annotation = Path

            # Determine if this should be positional or named
            if is_keyword_only:
                # Keyword-only parameter (after *, in signature) is always named
                default = typer.Option(None) if p.default is None else typer.Option(...)
            elif p.default is Parameter.empty:
                # Positional: required Image/Transform without default
                default = typer.Argument(...)
                has_positional_input = True  # Mark that we've seen a positional input
            elif p.default is None:
                # Named: optional Image/Transform (has default)
                default = typer.Option(None)
            else:
                # Named: Image/Transform with non-None default
                default = typer.Option(...)
        elif p.default == Parameter.empty:
            # Non-Image/Transform required parameters stay as named options
            default = typer.Option(...)
        return Parameter(
            p.name,
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=annotation,
            default=default,
        )

    func_sig = signature(func)

    params: list[Parameter] = []
    for p in func_sig.parameters.values():
        params.append(_translate_param(p))

    return_type = parse_annotation(func_sig.return_annotation, globals, locals)
    if (
        return_type
        and isclass(return_type)
        and issubclass(return_type, (sitk.Image, sitk.Transform))
    ):
        # Output is positional if:
        # 1. There's at least one positional Image/Transform input, OR
        # 2. There are no Image/Transform inputs at all (e.g., generator functions)
        # Output is named only when ALL Image/Transform inputs are keyword-only
        output_default = (
            typer.Argument(...)
            if (has_positional_input or not has_any_image_transform_input)
            else None
        )
        params.append(
            Parameter(
                output_arg_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=output_default,
                annotation=Path,
            ),
        )
        return_type = None

    # Add verbose parameter if requested
    if verbose:
        params.append(
            Parameter(
                "_verbose",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
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
        params.append(
            Parameter(
                "_force",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
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

    @wraps(func, new_sig=new_sig)  # type: ignore[misc,untyped-decorator]
    def func_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Configure logging based on verbosity level
        if verbose and "_verbose" in kwargs:
            verbose_level = kwargs.pop("_verbose")
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
            if k == "_force":
                # Extract boolean value from typer.Option if needed
                force = bool(v.default if is_typer_default(v) else v)
                continue
            if k in image_args and isinstance(v, Path):
                if not v.exists():
                    msg = f"Input image file not found: {v}"
                    raise FileNotFoundError(msg)
                v = sitk.ReadImage(str(v))
            if k in transform_args and isinstance(v, Path):
                if not v.exists():
                    msg = f"Input transform file not found: {v}"
                    raise FileNotFoundError(msg)
                v = sitk.ReadTransform(str(v))
            kwargs_inner[k] = v

        ret = func(*args, **kwargs_inner)
        if output_file and ret:
            # Check for overwrite protection
            if overwrite is not True and not force and output_file.exists():
                if overwrite == "prompt":
                    # Interactive prompt
                    response = input(
                        f"Output file '{output_file}' exists. Overwrite? [y/N]: "
                    )
                    if response.lower() not in ("y", "yes"):
                        print("Operation cancelled.")
                        return None
                else:  # overwrite is False
                    msg = (
                        f"Output file '{output_file}' already exists. "
                        "Use --force to overwrite."
                    )
                    raise FileExistsError(msg)

            if create_dirs:
                output_file.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(ret, sitk.Image):
                return sitk.WriteImage(ret, str(output_file))
            return sitk.WriteTransform(ret, str(output_file))
        return ret

    return func_wrapper


def register_command(
    app: typer.Typer,
    func_name: str | None = None,
    output_arg_name: str = "output",
    create_dirs: bool = True,
    verbose: bool = False,
    overwrite: bool | Literal["prompt"] = True,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
) -> DecoratorType:
    """Register a function as a Typer command.

    Decorator that wraps a function with make_cli and registers it with a Typer app.

    Args:
        app: Typer application instance to register the command with
        func_name: Custom name for the command (default: use function name)
        output_arg_name: Name for the output file parameter (default: "output")
        create_dirs: Auto-create parent directories for output files (default: True)
        verbose: Add --verbose/-v flag for logging control (default: False)
        overwrite: Control output file overwrite behavior (default: True)
            - True: Always overwrite existing files
            - False: Error if output file exists (adds --force flag to override)
            - "prompt": Ask user interactively (adds --force flag to skip prompt)
        globals: Global namespace for evaluating string annotations
        locals: Local namespace for evaluating string annotations

    Returns:
        Decorator function that registers and returns the original function

    Examples:
        >>> @register_command(app)
        ... def process(input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process INPUT OUTPUT

        >>> @register_command(app)
        ... def process(*, input: sitk.Image) -> sitk.Image:
        ...     return input
        # CLI: process --input INPUT --output OUTPUT

        >>> @register_command(app)
        ... def process(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
        ...     return input * mask
        # CLI: process INPUT OUTPUT --mask MASK
    """

    def decorator(func: FuncType) -> FuncType:
        func_cli = make_cli(
            func,
            output_arg_name=output_arg_name,
            create_dirs=create_dirs,
            verbose=verbose,
            overwrite=overwrite,
            globals=globals,
            locals=locals,
        )

        @app.command()
        @wraps(func_cli, func_name=func_name)  # type: ignore[misc,untyped-decorator,arg-type]
        def foo(*args: Any, **kwargs: Any) -> Any:
            return func_cli(*args, **kwargs)

        return func

    return decorator
