import sys
from inspect import Parameter, isclass, signature
from pathlib import Path
from typing import Optional, Union, get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType as UnionType
else:
    from typing import Union as UnionType

import SimpleITK as sitk
import typer
from makefun import wraps


def make_cli(func, output_arg_name="output", globals=None, locals=None):
    """Make command line interface from function with sitk.Image args"""
    image_args = []
    transform_args = []

    def _parse_annotation(annotation):
        """handle Optional[A], Union[A, None] and A | None, and string annotations"""
        if isinstance(annotation, str):
            if sys.version_info < (3, 10):
                if "|" in annotation:
                    types = ",".join(t.strip() for t in annotation.split("|"))
                    annotation = f"Union[{types}]"
            annotation = eval(annotation, globals, locals)

        origin = get_origin(annotation)
        args = get_args(annotation)
        if any(origin is t for t in (Union, UnionType)):
            for a in args:
                if not isinstance(a, type(None)):
                    return a
        return annotation

    def _translate_param(p: Parameter):
        """translate signature parameters"""
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

    params = []
    for idx, p in enumerate(func_sig.parameters.values()):
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

    @wraps(func, new_sig=new_sig)
    def func_wrapper(*args, **kwargs):
        output_file: Optional[Path] = None
        kwargs_inner = {}
        for k, v in kwargs.items():
            if k == output_arg_name:
                output_file = v
                continue
            if k in image_args and issubclass(type(v), Path):
                v = sitk.ReadImage(f"{v}")
            if k in transform_args and issubclass(type(v), Path):
                v = sitk.ReadTransform(f"{v}")
            kwargs_inner[k] = v

        ret = func(*args, **kwargs_inner)
        if output_file and ret:
            if isinstance(ret, sitk.Image):
                return sitk.WriteImage(ret, f"{output_file}")
            else:
                return sitk.WriteTransform(ret, f"{output_file}")
        return ret

    return func_wrapper


def register_command(
    app: typer.Typer,
    func_name: Optional[str] = None,
    output_arg_name: str = "output",
    globals=None,
    locals=None,
):
    """Register function as command"""

    def decorator(func):
        func_cli = make_cli(
            func, output_arg_name=output_arg_name, globals=globals, locals=locals
        )

        @app.command()
        @wraps(func_cli, func_name=func_name)
        def foo(*args, **kwargs):
            return func_cli(*args, **kwargs)

        return func

    return decorator
