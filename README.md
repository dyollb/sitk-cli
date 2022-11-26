# Wrap SimpleITK functions as command lines

[![Build Actions Status](https://github.com/dyollb/segmantic/workflows/CI/badge.svg)](https://github.com/dyollb/sitk-cli/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/sitk-cli.svg)](https://badge.fury.io/py/sitk-cli)
<img src="https://img.shields.io/pypi/dm/sitk-cli.svg?label=pypi%20downloads&logo=python&logoColor=green"/>

## Overview

Create [Typer](https://github.com/tiangolo/typer) command line interface from functions that use [SimpleITK](https://github.com/SimpleITK/SimpleITK) images (and transforms) as arguments or return type. 

```Python
import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer()


@register_command(app)
def fill_holes_slice_by_slice(mask: sitk.Image) -> sitk.Image:
    mask = mask != 0
    output = sitk.Image(mask.GetSize(), mask.GetPixelID())
    output.CopyInformation(mask)
    for k in range(mask.GetSize()[2]):
        output[:, :, k] = sitk.BinaryFillhole(mask[:, :, k], fullyConnected=False)
    return output


if __name__ == "__main__":
    app()
```

To work, sitk-cli inspects the type annotations of the function and creates a wrapper function that loads images from file and passes these to the original function. Returned images (transforms) are written to a file by the wrapper function..

## Installation

```sh
pip install sitk-cli
```

## Demo

![Command lind demo](https://github.com/dyollb/sitk-cli/raw/main/docs/demo.gif)
