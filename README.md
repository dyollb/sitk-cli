# Wrap SimpleITK functions as command lines

[![Build Actions Status](https://github.com/dyollb/segmantic/workflows/CI/badge.svg)](https://github.com/dyollb/sitk-cli/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/sitk-cli.svg)](https://badge.fury.io/py/sitk-cli)
<img src="https://img.shields.io/pypi/dm/sitk-cli.svg?label=pypi%20downloads&logo=python&logoColor=green"/>

## Overview

Create [Typer](https://github.com/tiangolo/typer) command line interfaces from functions that use [SimpleITK](https://github.com/SimpleITK/SimpleITK) images and transforms as arguments or return types.

**Key features:**

- 🔄 Automatic file I/O handling for SimpleITK images and transforms
- 🚀 Built on Typer for modern CLI experiences
- 📁 Auto-create output directories with optional overwrite protection
- 📝 Optional verbose logging with Rich integration
- � Batch processing for entire directories with automatic file matching
- �🐍 Python 3.11+ with modern syntax

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

## Advanced Features

### Positional vs Named Arguments

Use Python's native `*,` syntax to control whether CLI arguments are positional or named:

```python
@register_command(app)
def process(input: sitk.Image, *, mask: sitk.Image) -> sitk.Image:
    """Mix positional and keyword-only arguments.

    CLI: process INPUT OUTPUT --mask MASK
    """
    return input * mask
```

Behavior:

- **Required** Image/Transform parameters → **positional** by default
- Parameters **after `*,`** → **keyword-only** (named options)
- **Optional** parameters (with defaults) → **named options**
- Output → **positional** if any input is positional, otherwise **named**

### Verbose Logging

```python
from sitk_cli import logger, register_command

@register_command(app, verbose=True)
def process_with_logging(input: sitk.Image) -> sitk.Image:
    logger.info("Starting processing...")
    result = sitk.Median(input, [2] * input.GetDimension())
    logger.debug(f"Result size: {result.GetSize()}")
    return result
```

```sh
python script.py process-with-logging input.nii output.nii -v   # INFO level
python script.py process-with-logging input.nii output.nii -vv  # DEBUG level
```

### Overwrite Protection

```python
@register_command(app, overwrite=False)
def protected_process(input: sitk.Image) -> sitk.Image:
    """Prevent accidental overwrites."""
    return sitk.Median(input, [2] * input.GetDimension())
```

```sh
python script.py protected-process input.nii output.nii
python script.py protected-process input.nii output.nii          # Error: file exists
python script.py protected-process input.nii output.nii --force  # OK, overwrites
```

Modes: `overwrite=True` (default), `overwrite=False` (requires `--force`), `overwrite="prompt"` (asks user)

### Batch Processing

Process entire directories of images/transforms with automatic file matching:

```python
from sitk_cli import register_command
import typer

app = typer.Typer()

@register_command(app, batch=True)
def denoise(input: sitk.Image, radius: int = 2) -> sitk.Image:
    """Apply median filter to reduce noise."""
    return sitk.Median(input, [radius] * input.GetDimension())

@register_command(app, batch=True)
def smooth(input: sitk.Image, sigma: float = 1.0) -> sitk.Image:
    """Apply Gaussian smoothing."""
    return sitk.SmoothingRecursiveGaussian(input, sigma)
```

```sh
# Process directory
python script.py denoise input/ outputs/ --radius 3

# Mix directory and single file (e.g., registration with fixed reference)
python script.py register fixed.nii movings/ outputs/
```

**Features:**

- 🔍 Auto-detects files vs directories (globs `*.nii.gz` or `*.tfm`)
- 🔗 Matches files across directories by stem (e.g., `brain_001.nii.gz` ↔ `brain_001_mask.nii.gz`)
- 📝 Customizable output naming with `output_template='processed_{stem}{suffix}'`
- ✅ Supports optional parameters (e.g., optional mask)

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
