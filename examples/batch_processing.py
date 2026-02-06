"""Example: Batch processing with sitk-cli.

This example demonstrates how to use create_batch_command() to process
multiple files in directories.

Features demonstrated:
- Single input directory → multiple outputs
- Multiple input directories matched by stem
- Mixed file and directory inputs
- Custom output naming templates
- BIDS-compatible naming preservation
"""

import SimpleITK as sitk
import typer

from sitk_cli import create_batch_command

app = typer.Typer(pretty_exceptions_enable=False)

#
# Example 1: Process a directory of images with a filter
#


def median_filter(input: sitk.Image, radius: int = 2) -> sitk.Image:
    """Apply median filter to reduce noise."""
    return sitk.Median(input, [radius] * input.GetDimension())


# Create batch version - processes all *.nii.gz files in input directory
batch_median = create_batch_command(median_filter)
app.command(name="median")(batch_median)

# CLI Usage:
# python examples/batch_processing.py median input_dir/ output_dir/ --radius 3
# Processes: input_dir/brain_001.nii.gz → output_dir/brain_001.nii.gz
#            input_dir/brain_002.nii.gz → output_dir/brain_002.nii.gz
#            ...

#
# Example 2: Simple smoothing - single directory to outputs
#


def smooth(input: sitk.Image, sigma: float = 1.0) -> sitk.Image:
    """Apply Gaussian smoothing."""
    return sitk.SmoothingRecursiveGaussian(input, sigma)


batch_smooth = create_batch_command(smooth)
app.command(name="smooth")(batch_smooth)

# CLI Usage: Works seamlessly with BIDS naming
# python examples/batch_processing.py smooth bids_dir/ smoothed/ --sigma 2.0
# Preserves naming:
#   sub-01_ses-01_T1w.nii.gz → sub-01_ses-01_T1w.nii.gz
#   sub-01_ses-02_T1w.nii.gz → sub-01_ses-02_T1w.nii.gz

#
# Example 3: Custom output naming template
#


def threshold(input: sitk.Image, value: int = 128) -> sitk.Image:
    """Apply binary threshold."""
    return sitk.BinaryThreshold(input, lowerThreshold=value)


# Custom output template with prefix
batch_threshold = create_batch_command(
    threshold, output_template="thresholded_{stem}{suffix}"
)
app.command(name="threshold")(batch_threshold)

# CLI Usage:
# python examples/batch_processing.py threshold scans/ outputs/ --value 100
# Processes: scans/patient01.nii.gz → outputs/thresholded_patient01.nii.gz
#            scans/patient02.nii.gz → outputs/thresholded_patient02.nii.gz

#
# Example 4: Multiple directories matched by stem
#


def apply_transform(image: sitk.Image, transform: sitk.Transform) -> sitk.Image:
    """Apply transform to image."""
    return sitk.Resample(image, transform)


# Processes matching pairs from two directories
batch_resample = create_batch_command(apply_transform)
app.command(name="resample")(batch_resample)

# CLI Usage:
# python examples/batch_processing.py resample images/ transforms/ outputs/
# Matches by stem:
#   images/brain_001.nii.gz + transforms/brain_001.tfm → outputs/brain_001.nii.gz
#   images/brain_002.nii.gz + transforms/brain_002.tfm → outputs/brain_002.nii.gz

#
# Example 5: Multiple fixed images to single moving (with optional mask)
#


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


# Register multiple subjects to a single template
# Outputs are transforms named after the fixed images
batch_register_multi = create_batch_command(
    register_fixed_to_moving,
    output_template="{stem}.tfm",
    output_stem="fixed",
)
app.command(name="register-multi")(batch_register_multi)

# CLI Usage (without mask):
# python examples/batch_processing.py register-multi \
#     subjects/ template.nii.gz transforms/
# Registers each subject to template:
#   subjects/sub-01.nii.gz + template.nii.gz → transforms/sub-01.tfm
#   subjects/sub-02.nii.gz + template.nii.gz → transforms/sub-02.tfm
#
# CLI Usage (with masks matching subjects):
# python examples/batch_processing.py register-multi \
#     subjects/ template.nii.gz masks/ transforms/
# Matches masks by stem:
#   subjects/sub-01.nii.gz + masks/sub-01.nii.gz + template.nii.gz → transforms/sub-01.tfm
#   subjects/sub-02.nii.gz + masks/sub-02.nii.gz + template.nii.gz → transforms/sub-02.tfm

#
# Example 6: Mixed file and directory (atlas registration)
#


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


# Use single atlas file for all moving images
# Specify output_stem="moving" to name outputs after moving images
batch_register = create_batch_command(register_to_atlas, output_stem="moving")
app.command(name="register-atlas")(batch_register)

# CLI Usage:
# python examples/batch_processing.py register-atlas \
#     subjects/ atlas.nii.gz outputs/ --iterations 200
# Processes each file in subjects/ with the same atlas.nii.gz:
#   subjects/sub-01.nii.gz + atlas.nii.gz → outputs/sub-01.nii.gz
#   subjects/sub-02.nii.gz + atlas.nii.gz → outputs/sub-02.nii.gz

#
# Example 7: Generate transforms (different output type)
#


def estimate_motion(fixed: sitk.Image, moving: sitk.Image) -> sitk.Transform:
    """Estimate motion between two images."""
    # Simplified rigid registration
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMeanSquares()
    registration.SetOptimizerAsRegularStepGradientDescent(1.0, 0.001, 100)

    initial_transform = sitk.Euler3DTransform()
    registration.SetInitialTransform(initial_transform)

    return registration.Execute(fixed, moving)


# Output .tfm files instead of images
batch_motion = create_batch_command(
    estimate_motion,
    output_template="{stem}.tfm",
    output_stem="moving",
)
app.command(name="motion")(batch_motion)

# CLI Usage:
# python examples/batch_processing.py motion \
#     reference.nii.gz timepoints/ transforms/
# Estimates motion for each timepoint relative to reference:
#   timepoints/t01.nii.gz + reference.nii.gz → transforms/t01.tfm
#   timepoints/t02.nii.gz + reference.nii.gz → transforms/t02.tfm


if __name__ == "__main__":
    app()
