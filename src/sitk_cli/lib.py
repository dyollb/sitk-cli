from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, isclass, signature
from pathlib import Path
from typing import Any, TypeAlias, get_args, get_origin

import SimpleITK as sitk
import typer
from makefun import wraps

# Type aliases
SitkImageOrTransform: TypeAlias = type[sitk.Image] | type[sitk.Transform]
FuncType: TypeAlias = Callable[..., Any]
DecoratorType: TypeAlias = Callable[[FuncType], FuncType]


def make_cli(
    func: FuncType,
    output_arg_name: str = "output",
    create_dirs: bool = True,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
) -> FuncType:
    """Make command line interface from function with sitk.Image args.

    Transforms a function that uses SimpleITK Image/Transform objects into a CLI
    that accepts file paths. Automatically handles loading from and saving to files.

    Args:
        func: Function to wrap with CLI functionality
        output_arg_name: Name for the output file parameter (default: "output")
        create_dirs: Auto-create parent directories for output files (default: True)
        globals: Global namespace for evaluating string annotations
        locals: Local namespace for evaluating string annotations

    Returns:
        Wrapped function that accepts Path arguments and handles file I/O

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If annotation parsing fails
    """
    image_args: list[str] = []
    transform_args: list[str] = []

    def _parse_annotation(annotation: Any) -> Any:
        """Parse type annotation, handling Optional/Union and string annotations.

        String annotations need evaluation to convert to actual types. This is
        necessary when annotations reference types not yet defined at parse time.
        """
        if isinstance(annotation, str):
            try:
                annotation = eval(annotation, globals, locals)
            except Exception as e:
                msg = f"Failed to parse type annotation '{annotation}': {e}"
                raise ValueError(msg) from e

        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is not None:
            for a in args:
                if a is not type(None):
                    return a
        return annotation

    def _translate_param(p: Parameter) -> Parameter:
        """Translate function parameters for CLI compatibility.

        Converts SimpleITK Image/Transform parameters to Path parameters,
        tracks which parameters need file I/O, and sets appropriate defaults.
        """
        annotation = _parse_annotation(p.annotation)
        default = p.default

        if isclass(annotation) and issubclass(annotation, (sitk.Image, sitk.Transform)):
            if issubclass(annotation, sitk.Image):
                image_args.append(p.name)
            else:
                transform_args.append(p.name)
            annotation = Path
            default = typer.Option(None) if p.default is None else typer.Option(...)
        elif p.default == Parameter.empty:
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

    return_type = _parse_annotation(func_sig.return_annotation)
    if (
        return_type
        and isclass(return_type)
        and issubclass(return_type, (sitk.Image, sitk.Transform))
    ):
        params.append(
            Parameter(
                output_arg_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
                annotation=Path,
            ),
        )
        return_type = None

    new_sig = func_sig.replace(parameters=params, return_annotation=return_type)

    @wraps(func, new_sig=new_sig)  # type: ignore[misc,untyped-decorator]
    def func_wrapper(*args: Any, **kwargs: Any) -> Any:
        output_file: Path | None = None
        kwargs_inner: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k == output_arg_name:
                output_file = v
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
        globals: Global namespace for evaluating string annotations
        locals: Local namespace for evaluating string annotations

    Returns:
        Decorator function that registers and returns the original function
    """

    def decorator(func: FuncType) -> FuncType:
        func_cli = make_cli(
            func,
            output_arg_name=output_arg_name,
            create_dirs=create_dirs,
            globals=globals,
            locals=locals,
        )

        @app.command()
        @wraps(func_cli, func_name=func_name)  # type: ignore[misc,untyped-decorator,arg-type]
        def foo(*args: Any, **kwargs: Any) -> Any:
            return func_cli(*args, **kwargs)

        return func

    return decorator
