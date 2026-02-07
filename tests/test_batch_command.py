"""Tests for batch processing functionality."""

from __future__ import annotations

from inspect import signature
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import SimpleITK as sitk

from sitk_cli import create_batch_command

if TYPE_CHECKING:
    from pytest import TempPathFactory


@pytest.fixture
def test_images(tmp_path_factory: TempPathFactory) -> Path:
    """Create test images with BIDS-like names."""
    img_dir = tmp_path_factory.mktemp("images")

    # Create test images with different stems
    for idx, name in enumerate(["brain_001", "brain_002", "brain_003"]):
        img = sitk.Image([10, 10, 10], sitk.sitkUInt8)
        img = img + idx  # Set pixel values
        sitk.WriteImage(img, str(img_dir / f"{name}.nii.gz"))

    return img_dir


@pytest.fixture
def test_images_bids(tmp_path_factory: TempPathFactory) -> Path:
    """Create test images with BIDS naming convention."""
    img_dir = tmp_path_factory.mktemp("images_bids")

    # Create BIDS-style filenames
    for sub in [1, 2]:
        for ses in [1, 2]:
            name = f"sub-{sub:02d}_ses-{ses:02d}_T1w"
            img = sitk.Image([10, 10, 10], sitk.sitkUInt8)
            img = img + (sub * 10 + ses)  # Set pixel values
            sitk.WriteImage(img, str(img_dir / f"{name}.nii.gz"))

    return img_dir


@pytest.fixture
def test_transforms(tmp_path_factory: TempPathFactory) -> Path:
    """Create test transforms."""
    tfm_dir = tmp_path_factory.mktemp("transforms")

    for name in ["brain_001", "brain_002", "brain_003"]:
        tfm = sitk.TranslationTransform(3, [1.0, 2.0, 3.0])
        sitk.WriteTransform(tfm, str(tfm_dir / f"{name}.tfm"))

    return tfm_dir


def test_batch_single_input_directory(test_images: Path, tmp_path: Path) -> None:
    """Test batch processing with single input directory."""

    def median_filter(input: sitk.Image, radius: int = 2) -> sitk.Image:
        """Apply median filter."""
        return sitk.Median(input, [radius] * input.GetDimension())

    batch_filter = create_batch_command(median_filter)
    output_dir = tmp_path / "output"

    # Call batch wrapper directly
    batch_filter(test_images, output_dir=output_dir, radius=1)

    # Check outputs were created
    output_files = sorted(output_dir.glob("*.nii.gz"))
    assert len(output_files) == 3
    assert output_files[0].name == "brain_001.nii.gz"
    assert output_files[1].name == "brain_002.nii.gz"
    assert output_files[2].name == "brain_003.nii.gz"


def test_batch_multiple_input_directories(
    test_images: Path, test_transforms: Path, tmp_path: Path
) -> None:
    """Test batch processing with multiple directories matched by stem."""

    def apply_transform(image: sitk.Image, transform: sitk.Transform) -> sitk.Image:
        """Apply transform to image."""
        return sitk.Resample(image, transform)

    batch_resample = create_batch_command(apply_transform)
    output_dir = tmp_path / "output"

    batch_resample(test_images, test_transforms, output_dir=output_dir)

    # Check outputs
    output_files = sorted(output_dir.glob("*.nii.gz"))
    assert len(output_files) == 3


def test_batch_mixed_file_and_directory(test_images: Path, tmp_path: Path) -> None:
    """Test batch with one file (used for all) and one directory."""
    # Create a single reference image
    ref_img = sitk.Image([10, 10, 10], sitk.sitkUInt8)
    ref_img = ref_img + 100  # Set pixel value
    ref_path = tmp_path / "reference.nii.gz"
    sitk.WriteImage(ref_img, str(ref_path))

    def add_images(fixed: sitk.Image, moving: sitk.Image) -> sitk.Image:
        """Add two images."""
        return fixed + moving

    batch_add = create_batch_command(add_images, output_stem="moving")
    output_dir = tmp_path / "output"

    batch_add(ref_path, test_images, output_dir=output_dir)

    # Should process all images in test_images with same reference
    output_files = sorted(output_dir.glob("*.nii.gz"))
    assert len(output_files) == 3

    # Output names should match the moving images (from test_images)
    assert output_files[0].name == "brain_001.nii.gz"


def test_batch_custom_output_template(test_images: Path, tmp_path: Path) -> None:
    """Test custom output naming template."""

    def invert(input: sitk.Image) -> sitk.Image:
        """Invert image."""
        return sitk.InvertIntensity(input)

    batch_invert = create_batch_command(
        invert, output_template="inverted_{stem}{suffix}"
    )
    output_dir = tmp_path / "output"

    batch_invert(test_images, output_dir=output_dir)

    output_files = sorted(output_dir.glob("*.nii.gz"))
    assert len(output_files) == 3
    assert output_files[0].name == "inverted_brain_001.nii.gz"
    assert output_files[1].name == "inverted_brain_002.nii.gz"


def test_batch_bids_naming(test_images_bids: Path, tmp_path: Path) -> None:
    """Test that BIDS naming convention is preserved."""

    def threshold(input: sitk.Image, value: int = 50) -> sitk.Image:
        """Apply threshold."""
        return sitk.BinaryThreshold(input, lowerThreshold=value)

    batch_threshold = create_batch_command(threshold)
    output_dir = tmp_path / "output"

    batch_threshold(test_images_bids, output_dir=output_dir, value=30)

    output_files = sorted(output_dir.glob("*.nii.gz"))
    assert len(output_files) == 4

    # Check BIDS names are preserved
    names = [f.name for f in output_files]
    assert "sub-01_ses-01_T1w.nii.gz" in names
    assert "sub-02_ses-02_T1w.nii.gz" in names


def test_batch_transform_output(test_images: Path, tmp_path: Path) -> None:
    """Test batch processing that outputs transforms."""

    def create_transform(image: sitk.Image) -> sitk.Transform:
        """Create identity transform based on image."""
        return sitk.TranslationTransform(image.GetDimension())

    batch_create_tfm = create_batch_command(
        create_transform, output_template="{stem}.tfm"
    )
    output_dir = tmp_path / "output"

    batch_create_tfm(test_images, output_dir=output_dir)

    output_files = sorted(output_dir.glob("*.tfm"))
    assert len(output_files) == 3
    assert output_files[0].name == "brain_001.tfm"


def test_batch_optional_image_parameter(tmp_path: Path) -> None:
    """Test batch processing with optional Image parameter (e.g., mask)."""
    # Setup: multiple fixed images, single moving image, optional masks
    fixed_dir = tmp_path / "fixed"
    mask_dir = tmp_path / "masks"
    fixed_dir.mkdir()
    mask_dir.mkdir()

    # Create fixed images
    for i in range(1, 4):
        img = sitk.Image([10, 10, 10], sitk.sitkUInt8)
        img = img + (i * 10)
        sitk.WriteImage(img, str(fixed_dir / f"sub-{i:02d}.nii.gz"))

    # Create matching masks
    for i in range(1, 4):
        mask = sitk.Image([10, 10, 10], sitk.sitkUInt8)
        mask = mask + 1  # Binary mask
        sitk.WriteImage(mask, str(mask_dir / f"sub-{i:02d}.nii.gz"))

    # Create single moving image
    moving = sitk.Image([10, 10, 10], sitk.sitkUInt8)
    moving = moving + 50
    moving_path = tmp_path / "moving.nii.gz"
    sitk.WriteImage(moving, str(moving_path))

    def register_with_optional_mask(
        fixed: sitk.Image, moving: sitk.Image, fixed_mask: sitk.Image | None = None
    ) -> sitk.Transform:
        """Register with optional mask."""
        # Create identity transform (simplified for testing)
        tfm = sitk.TranslationTransform(fixed.GetDimension())
        # In real scenario, would use mask if provided
        if fixed_mask is not None:
            # Verify mask was loaded
            assert fixed_mask.GetSize() == fixed.GetSize()
        return tfm

    batch_register = create_batch_command(
        register_with_optional_mask, output_template="{stem}.tfm", output_stem="fixed"
    )

    # Test WITHOUT mask
    output_dir1 = tmp_path / "output_no_mask"
    batch_register(fixed_dir, moving_path, output_dir=output_dir1)

    output_files1 = sorted(output_dir1.glob("*.tfm"))
    assert len(output_files1) == 3
    assert output_files1[0].name == "sub-01.tfm"
    assert output_files1[1].name == "sub-02.tfm"
    assert output_files1[2].name == "sub-03.tfm"

    # Test WITH mask (matched by stem to fixed)
    output_dir2 = tmp_path / "output_with_mask"
    batch_register(fixed_dir, moving_path, mask_dir, output_dir=output_dir2)

    output_files2 = sorted(output_dir2.glob("*.tfm"))
    assert len(output_files2) == 3
    assert output_files2[0].name == "sub-01.tfm"


def test_batch_no_matching_files(test_images: Path, tmp_path: Path) -> None:
    """Test batch processing when no files match."""
    # Create empty directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    def dummy(input: sitk.Image) -> sitk.Image:
        return input

    batch_dummy = create_batch_command(dummy)
    output_dir = tmp_path / "output"

    # Should return early with warning
    batch_dummy(empty_dir, output_dir=output_dir)

    # No output directory created when no files processed
    # (mkdir is only called before processing)
    assert not list(output_dir.glob("*")) if output_dir.exists() else True


def test_batch_mismatched_stems(tmp_path: Path) -> None:
    """Test batch processing when stems don't match across directories."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Different stems in each directory
    img1 = sitk.Image([5, 5, 5], sitk.sitkUInt8)
    sitk.WriteImage(img1, str(dir1 / "brain_001.nii.gz"))
    sitk.WriteImage(img1, str(dir2 / "brain_002.nii.gz"))

    def combine(img1: sitk.Image, img2: sitk.Image) -> sitk.Image:
        return img1 + img2

    batch_combine = create_batch_command(combine)
    output_dir = tmp_path / "output"

    # Should not process anything (no matching stems)
    batch_combine(dir1, dir2, output_dir=output_dir)

    # No files should be created
    if output_dir.exists():
        assert list(output_dir.glob("*")) == []


def test_batch_invalid_output_stem_parameter() -> None:
    """Test that invalid output_stem raises error."""

    def process(input: sitk.Image) -> sitk.Image:
        return input

    with pytest.raises(ValueError, match="output_stem 'nonexistent' not found"):
        create_batch_command(process, output_stem="nonexistent")


def test_batch_no_image_transform_params() -> None:
    """Test that function without Image/Transform params raises error."""

    def invalid(x: int, y: int) -> int:
        return x + y

    with pytest.raises(
        ValueError, match="Function must have at least one Image or Transform parameter"
    ):
        create_batch_command(invalid)


def test_batch_stem_extraction_multi_part_extensions(tmp_path: Path) -> None:
    """Test that multi-part extensions like .nii.gz are handled correctly."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    # Create images with multi-part extensions
    img = sitk.Image([5, 5, 5], sitk.sitkUInt8)
    sitk.WriteImage(img, str(img_dir / "image.nii.gz"))

    def identity(input: sitk.Image) -> sitk.Image:
        return input

    batch_id = create_batch_command(identity)
    output_dir = tmp_path / "output"

    batch_id(img_dir, output_dir=output_dir)

    # Check that full extension is preserved
    output_files = list(output_dir.glob("*"))
    assert len(output_files) == 1
    assert output_files[0].name == "image.nii.gz"


def test_batch_output_params_added_when_function_returns_image() -> None:
    """Test that output_dir and output_template are added when function returns Image."""

    def filter_image(input: sitk.Image) -> sitk.Image:
        return input

    batch_fn = create_batch_command(filter_image)
    sig = signature(batch_fn)

    # Check that output_dir and output_template are in the signature
    assert "output_dir" in sig.parameters
    assert "output_template" in sig.parameters


def test_batch_output_params_not_added_when_function_returns_none() -> None:
    """Test that output_dir and output_template are NOT added when function returns None."""

    def analyze_image(input: sitk.Image) -> None:
        """Analysis function that doesn't return anything."""
        pass

    batch_fn = create_batch_command(analyze_image)
    sig = signature(batch_fn)

    # Check that output_dir and output_template are NOT in the signature
    assert "output_dir" not in sig.parameters
    assert "output_template" not in sig.parameters
