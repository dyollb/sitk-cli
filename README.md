# Wrap SimpleITK functions as command lines

Create simple command line interface from functions that use SimpleITK images as arguments or return type.

Example:

```Python
import SimpleITK as sitk
import typer

def fill_holes_slice_by_slice(mask: sitk.Image) -> sitk.Image:
    mask = mask != 0
    output = sitk.Image(mask.GetSize(), mask.GetPixelID())
    output.CopyInformation(mask)
    for k in range(mask.GetSize()[2]):
        output[:, :, k] = sitk.BinaryFillhole(mask[:, :, k], fullyConnected=False)
    return output


if __name__ == "__main__":
    app = typer.Typer()

    register_command(fill_holes_slice_by_slice, app)

    app()
```
