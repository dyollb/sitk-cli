import SimpleITK as sitk
import typer

from sitk_cli import register_command


def median_filter(input: sitk.Image, radius: int) -> sitk.Image:
    return sitk.Median(input, [radius] * input.GetDimension())


def bias_correct(
    input: sitk.Image,
    mask: sitk.Image = None,
    shrink_factor: int = 4,
    num_fitting_levels: int = 4,
    num_iterations: int = 50,
) -> sitk.Image:
    """Perform N4 bias correction on MRI

    Note:
    - if no mask is provided it will be generated using Otsu-thresholding
    """
    if not isinstance(mask, sitk.Image):
        mask = sitk.OtsuThreshold(input, 0, 1, 200)

    input = sitk.Cast(input, sitk.sitkFloat32)
    image = sitk.Shrink(
        sitk.Cast(input, sitk.sitkFloat32), [shrink_factor] * input.GetDimension()
    )
    mask = sitk.Shrink(mask, [shrink_factor] * input.GetDimension())

    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrector.SetMaximumNumberOfIterations([num_iterations] * num_fitting_levels)

    corrector.Execute(image, mask)
    log_bias_field = corrector.GetLogBiasFieldAsImage(input)
    corrected_image_full_resolution = input / sitk.Exp(log_bias_field)
    return corrected_image_full_resolution


if __name__ == "__main__":
    app = typer.Typer()

    register_command(median_filter, app)
    register_command(bias_correct, app)

    app()
