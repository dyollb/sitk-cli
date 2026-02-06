"""Demonstrates verbose mode with logging.

Shows how to use the --verbose/-v flag to control logging output.
Use -v for INFO level, -vv for DEBUG level.
"""

from __future__ import annotations

import SimpleITK as sitk
import typer

from sitk_cli import logger, register_command

app = typer.Typer()


@register_command(app, verbose=True)
def process_with_logging(iterations: int = 10) -> sitk.Image:
    """Process image with detailed logging.

    CLI Examples:
        # No logging output
        process-with-logging input.nii output.nii

        # INFO level logging (-v)
        process-with-logging input.nii output.nii -v

        # DEBUG level logging (-vv)
        process-with-logging input.nii output.nii -vv
    """
    logger.info(f"Starting processing with {iterations} iterations")

    result = sitk.Image([100, 100], sitk.sitkFloat32)
    for i in range(iterations):
        logger.debug(f"Iteration {i + 1}/{iterations}")
        result = sitk.Median(result, [2] * result.GetDimension())

        if (i + 1) % 5 == 0:
            logger.info(f"Progress: {i + 1}/{iterations} iterations complete")

    logger.info("Processing complete")
    logger.debug(f"Output image size: {result.GetSize()}")

    return result


@register_command(app, verbose=True)
def segment_with_feedback(
    input: sitk.Image,
    *,
    threshold: float = 0.5,
    fill_holes: bool = True,
) -> sitk.Image:
    """Segment image with progress feedback.

    CLI Examples:
        # With verbose output
        segment-with-feedback input.nii output.nii --threshold 0.7 -v
    """
    logger.info(f"Segmenting with threshold={threshold}")

    logger.debug("Converting to float...")
    float_image = sitk.Cast(input, sitk.sitkFloat32)

    logger.debug("Applying threshold...")
    binary = float_image > threshold

    if fill_holes:
        logger.info("Filling holes in segmentation")
        size = binary.GetSize()
        if len(size) == 3:
            logger.debug("Processing 3D volume slice-by-slice")
            for k in range(size[2]):
                logger.debug(f"  Slice {k + 1}/{size[2]}")
                binary[:, :, k] = sitk.BinaryFillhole(binary[:, :, k])
        else:
            logger.debug("Processing 2D image")
            binary = sitk.BinaryFillhole(binary)

    logger.info("Segmentation complete")
    return binary


if __name__ == "__main__":
    app()
