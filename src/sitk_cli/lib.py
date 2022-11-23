from inspect import Parameter, isclass, signature
from pathlib import Path
from typing import Optional

import SimpleITK as sitk
import typer
from makefun import wraps


def make_cli(func, output_arg_name="output"):
    """Make command line interface from function with sitk.Image args"""
    image_args = []
    transform_args = []

    def _translate_param(p: Parameter):
        annotation, default = p.annotation, p.default
        if isclass(p.annotation) and issubclass(
            p.annotation, (sitk.Image, sitk.Transform)
        ):
            if issubclass(p.annotation, sitk.Image):
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

    return_type = func_sig.return_annotation
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
    app: typer.Typer, func_name: Optional[str] = None, output_arg_name: str = "output"
):
    """Register function as command"""

    def decorator(func):
        func_cli = make_cli(func, output_arg_name=output_arg_name)

        @app.command()
        @wraps(func_cli, func_name=func_name)
        def foo(*args, **kwargs):
            return func_cli(*args, **kwargs)

        return func

    return decorator
