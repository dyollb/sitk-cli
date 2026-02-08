"""Example: Batch processing with sitk-cli.

This example demonstrates how to use create_command(batch=True) and
register_command(batch=True) to process multiple files in directories.

Features demonstrated:
- Single input directory → multiple outputs
- Multiple input directories matched by stem
- Mixed file and directory inputs
- Custom output naming templates
- BIDS-compatible naming preservation
"""

import SimpleITK as sitk
import typer

from sitk_cli import register_command

app = typer.Typer(pretty_exceptions_enable=False)

#
# Example 1: Process a directory of images with a filter
#


@register_command(app, func_name="median", batch=True)
def median_filter(input: sitk.Image, radius: int = 2) -> sitk.Image:
    """Apply median filter to reduce noise."""
    return sitk.Median(input, [radius] * input.GetDimension())


# CLI Usage:
# python examples/batch_processing.py median input_dir/ output_dir/ --radius 3
# Processes: input_dir/brain_001.nii.gz → output_dir/brain_001.nii.gz
#            input_dir/brain_002.nii.gz → output_dir/brain_002.nii.gz
#            ...

#
# Example 2: Simple smoothing - single directory to outputs
#


@register_command(app, func_name="smooth", batch=True)
def smooth(input: sitk.Image, sigma: float = 1.0) -> sitk.Image:
    """Apply Gaussian smoothing."""
    return sitk.SmoothingRecursiveGaussian(input, sigma)


# CLI Usage: Works seamlessly with BIDS naming
# python examples/batch_processing.py smooth bids_dir/ smoothed/ --sigma 2.0
# Preserves naming:
#   sub-01_ses-01_T1w.nii.gz → sub-01_ses-01_T1w.nii.gz
#   sub-01_ses-02_T1w.nii.gz → sub-01_ses-02_T1w.nii.gz

#
# Example 3: Custom output naming template
#


@register_command(
    app,
    func_name="threshold",
    batch=True,
    output_template="thresholded_{stem}{suffix}",
)
def threshold(input: sitk.Image, value: int = 128) -> sitk.Image:
    """Apply binary threshold."""
    return sitk.BinaryThreshold(input, lowerThreshold=value)


# CLI Usage:
# python examples/batch_processing.py threshold scans/ outputs/ --value 100
# Processes: scans/patient01.nii.gz → outputs/thresholded_patient01.nii.gz
#            scans/patient02.nii.gz → outputs/thresholded_patient02.nii.gz

#
# Example 4: Multiple directories matched by stem
#


@register_command(app, func_name="resample", batch=True)
def apply_transform(image: sitk.Image, transform: sitk.Transform) -> sitk.Image:
    """Apply transform to image."""
    return sitk.Resample(image, transform)


# CLI Usage:
# python examples/batch_processing.py resample images/ transforms/ outputs/
# Matches by stem:
#   images/brain_001.nii.gz + transforms/brain_001.tfm → outputs/brain_001.nii.gz
#   images/brain_002.nii.gz + transforms/brain_002.tfm → outputs/brain_002.nii.gz

#
# Example 5: Multiple fixed images to single moving (with optional mask)
#


# Register multiple subjects to a single template
# Outputs are transforms named after the fixed images
@register_command(
    app,
    func_name="register-multi",
    batch=True,
    output_template="{stem}.tfm",
    output_stem="fixed",
)
def register_fixed_to_moving(
    fixed: sitk.Image,
    moving: sitk.Image,
    fixed_mask: sitk.Image | None = None,
) -> sitk.Transform:
    """Register a single fixed image to a single moving image.

    Args:
        fixed: Fixed image to register
        moving: Moving/template image (target)
        fixed_mask: Optional mask for fixed image
    """
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMeanSquares()
    registration.SetOptimizerAsRegularStepGradientDescent(1.0, 0.001, 50)

    # Use mask if provided
    if fixed_mask is not None:
        registration.SetMetricFixedMask(fixed_mask)

    initial_transform = sitk.CenteredTransformInitializer(
        fixed,
        moving,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    registration.SetInitialTransform(initial_transform)

    return registration.Execute(fixed, moving)


# CLI Usage (without mask):
# python examples/batch_processing.py register-multi \
#     subjects/ template.nii.gz transforms/
# Registers each subject to template:
#   subjects/sub-01.nii.gz + template.nii.gz → transforms/sub-01.tfm
#   subjects/sub-02.nii.gz + template.nii.gz → transforms/sub-02.tfm
#
# CLI Usage (with masks matching subjects):
# python examples/batch_processing.py register-multi \
#     subjects/ template.nii.gz transforms/ --fixed-mask masks/
# Matches masks by stem:
#   subjects/sub-01.nii.gz + masks/sub-01.nii.gz + template.nii.gz → transforms/sub-01.tfm
#   subjects/sub-02.nii.gz + masks/sub-02.nii.gz + template.nii.gz → transforms/sub-02.tfm

#
# Example 6: Mixed file and directory (atlas registration)
#


# Use single atlas file for all moving images
# Specify output_stem="moving" to name outputs after moving images
@register_command(app, func_name="register-atlas", batch=True, output_stem="moving")
def register_to_atlas(
    moving: sitk.Image,
    fixed: sitk.Image,
    *,  # Keyword-only marker
    iterations: int = 100,
) -> sitk.Image:
    """Register moving image to fixed atlas."""
    # Simplified example - real registration would be more complex
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMeanSquares()
    registration.SetOptimizerAsRegularStepGradientDescent(
        learningRate=1.0,
        minStep=0.001,
        numberOfIterations=iterations,
    )
    registration.SetInterpolator(sitk.sitkLinear)

    initial_transform = sitk.CenteredTransformInitializer(
        fixed,
        moving,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    registration.SetInitialTransform(initial_transform)

    # Execute registration
    final_transform = registration.Execute(fixed, moving)

    # Apply transform
    return sitk.Resample(
        moving, fixed, final_transform, sitk.sitkLinear, 0.0, moving.GetPixelID()
    )


# CLI Usage:
# python examples/batch_processing.py register-atlas \
#     subjects/ atlas.nii.gz outputs/ --iterations 200
# Processes each file in subjects/ with the same atlas.nii.gz:
#   subjects/sub-01.nii.gz + atlas.nii.gz → outputs/sub-01.nii.gz
#   subjects/sub-02.nii.gz + atlas.nii.gz → outputs/sub-02.nii.gz

#
# Example 7: Generate transforms (different output type)
#


# Output .tfm files instead of images
@register_command(
    app,
    func_name="motion",
    batch=True,
    output_template="{stem}.tfm",
    output_stem="moving",
)
def estimate_motion(fixed: sitk.Image, moving: sitk.Image) -> sitk.Transform:
    """Estimate motion between two images."""
    # Simplified rigid registration
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMeanSquares()
    registration.SetOptimizerAsRegularStepGradientDescent(1.0, 0.001, 100)

    initial_transform = sitk.Euler3DTransform()
    registration.SetInitialTransform(initial_transform)

    return registration.Execute(fixed, moving)


# CLI Usage:
# python examples/batch_processing.py motion \
#     reference.nii.gz timepoints/ transforms/
# Estimates motion for each timepoint relative to reference:
#   timepoints/t01.nii.gz + reference.nii.gz → transforms/t01.tfm
#   timepoints/t02.nii.gz + reference.nii.gz → transforms/t02.tfm


if __name__ == "__main__":
    app()
