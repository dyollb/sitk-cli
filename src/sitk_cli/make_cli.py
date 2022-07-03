from inspect import Parameter, isclass, signature
from pathlib import Path

import SimpleITK as sitk
import typer
from makefun import wraps


def make_cli(func):
    """Make command line interface from function with sitk.Image args"""
    image_args = []

    def _translate_param(p: Parameter):
        annotation, default = p.annotation, p.default
        if issubclass(p.annotation, sitk.Image):
            image_args.append(p.name)
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
    last_image_argument_idx = 0
    for idx, p in enumerate(func_sig.parameters.values()):
        if issubclass(p.annotation, sitk.Image):
            last_image_argument_idx = idx + 1
        params.append(_translate_param(p))

    return_type = func_sig.return_annotation
    if return_type and isclass(return_type) and issubclass(return_type, sitk.Image):
        params.insert(
            last_image_argument_idx,
            Parameter(
                "output",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
                annotation=Path,
            ),
        )
        return_type = None

    new_sig = func_sig.replace(parameters=params, return_annotation=return_type)

    @wraps(func, new_sig=new_sig)
    def func_wrapper(*args, **kwargs):
        output_file: Path = None
        kwargs_inner = {}
        for k, v in kwargs.items():
            if k == "output":
                output_file = v
                continue
            if k in image_args and issubclass(type(v), Path):
                v = sitk.ReadImage(f"{v}")
            kwargs_inner[k] = v

        ret = func(*args, **kwargs_inner)
        if output_file and ret:
            return sitk.WriteImage(ret, f"{output_file}")
        print(ret)
        return ret

    return func_wrapper


def register_command(func, *, app: typer.Typer, func_name: str = None):
    """Register function as command"""
    func_cli = make_cli(func)

    @app.command()
    @wraps(func_cli, func_name=func_name)
    def foo(*args, **kwargs):
        return func_cli(*args, **kwargs)
