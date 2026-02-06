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
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
) -> FuncType:
    """Make command line interface from function with sitk.Image args."""
    image_args: list[str] = []
    transform_args: list[str] = []

    def _parse_annotation(annotation: Any) -> Any:
        """Handle Optional[A], Union[A, None] and A | None, and string annotations."""
        if isinstance(annotation, str):
            annotation = eval(annotation, globals, locals)

        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is not None:
            for a in args:
                if a is not type(None):
                    return a
        return annotation

    def _translate_param(p: Parameter) -> Parameter:
        """Translate signature parameters."""
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
                v = sitk.ReadImage(str(v))
            if k in transform_args and isinstance(v, Path):
                v = sitk.ReadTransform(str(v))
            kwargs_inner[k] = v

        ret = func(*args, **kwargs_inner)
        if output_file and ret:
            if isinstance(ret, sitk.Image):
                return sitk.WriteImage(ret, str(output_file))
            return sitk.WriteTransform(ret, str(output_file))
        return ret

    return func_wrapper


def register_command(
    app: typer.Typer,
    func_name: str | None = None,
    output_arg_name: str = "output",
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
) -> DecoratorType:
    """Register function as command."""

    def decorator(func: FuncType) -> FuncType:
        func_cli = make_cli(
            func, output_arg_name=output_arg_name, globals=globals, locals=locals
        )

        @app.command()
        @wraps(func_cli, func_name=func_name)  # type: ignore[misc,untyped-decorator,arg-type]
        def foo(*args: Any, **kwargs: Any) -> Any:
            return func_cli(*args, **kwargs)

        return func

    return decorator
