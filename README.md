# Wrap SimpleITK functions as command lines

[![Build Actions Status](https://github.com/dyollb/segmantic/workflows/CI/badge.svg)](https://github.com/dyollb/sitk-cli/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/sitk-cli.svg)](https://badge.fury.io/py/sitk-cli)
<img src="https://img.shields.io/pypi/dm/sitk-cli.svg?label=pypi%20downloads&logo=python&logoColor=green"/>

## Overview

Create [Typer](https://github.com/tiangolo/typer) command line interfaces from functions that use [SimpleITK](https://github.com/SimpleITK/SimpleITK) images and transforms as arguments or return types.

**Key features:**

- 🔄 Automatic file I/O handling for SimpleITK images and transforms
- 🎯 Type-safe with full type annotation support
- 🚀 Built on Typer for modern CLI experiences
- 🐍 Python 3.11+ with modern syntax

## Installation

```sh
pip install sitk-cli
```

**Optional dependencies:**

```sh
# For enhanced logging output with colors and formatting
pip install sitk-cli[rich]
```

**Requirements:** Python 3.11 or higher

## Quick Start

```python
from __future__ import annotations

import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer()


@register_command(app)
def fill_holes_slice_by_slice(mask: sitk.Image) -> sitk.Image:
    """Fill holes in a binary mask slice by slice."""
    mask = mask != 0
    output = sitk.Image(mask.GetSize(), mask.GetPixelID())
    output.CopyInformation(mask)
    for k in range(mask.GetSize()[2]):
        output[:, :, k] = sitk.BinaryFillhole(mask[:, :, k], fullyConnected=False)
    return output


if __name__ == "__main__":
    app()
```

**How it works:** sitk-cli inspects the type annotations and creates a wrapper that:

1. Converts CLI file path arguments to SimpleITK images/transforms
1. Calls your function with the loaded objects
1. Saves returned images/transforms to the specified output file

## Usage Examples

### Optional Arguments

```python
@register_command(app)
def median_filter(input: sitk.Image, radius: int = 2) -> sitk.Image:
    """Apply median filtering to an image."""
    return sitk.Median(input, [radius] * input.GetDimension())
```

```sh
python script.py median-filter --input image.nii.gz --radius 3 --output filtered.nii.gz
```

### Multiple Inputs with Type Unions

```python
@register_command(app)
def add_images(
    input1: sitk.Image,
    input2: sitk.Image | None = None
) -> sitk.Image:
    """Add two images together, or return first if second is not provided."""
    if input2 is None:
        return input1
    return input1 + input2
```

### Transform Registration

```python
@register_command(app)
def register_images(
    fixed: sitk.Image,
    moving: sitk.Image,
    init_transform: sitk.Transform | None = None
) -> sitk.Transform:
    """Register two images and return the computed transform."""
    if init_transform is None:
        init_transform = sitk.CenteredTransformInitializer(fixed, moving)
    # ... registration code ...
    return final_transform
```

## Demo

![Command line demo](https://github.com/dyollb/sitk-cli/raw/main/docs/demo.gif)

## Development

### Setup

```sh
git clone https://github.com/dyollb/sitk-cli.git
cd sitk-cli
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e '.[dev,rich]'
```

### Running Tests

```sh
pytest tests/ -v --cov
```

### Code Quality

```sh
ruff check .
ruff format .
mypy src/sitk_cli
```

### Pre-commit Hooks

```sh
pre-commit install
pre-commit run --all-files
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
