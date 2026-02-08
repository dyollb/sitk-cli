"""Tests for type introspection utilities.

Note: Uses Union[] and Optional[] syntax intentionally to test legacy type annotation support.
"""

from __future__ import annotations

from inspect import Parameter, Signature
from typing import List, Optional, Union  # noqa: UP035

import SimpleITK as sitk

from sitk_cli.introspection import (
    find_image_transform_params,
    parse_annotation,
    resolve_optional_type,
)


class TestParseAnnotation:
    """Test parse_annotation with edge cases."""

    def test_string_annotation_returned_as_is(self) -> None:
        """Test that string annotations are returned unchanged.

        String annotations should be resolved by get_type_hints() before
        calling parse_annotation(). This function just returns them as-is.
        """
        result = parse_annotation("SomeType")
        assert result == "SomeType"

    def test_complex_string_annotation_returned_as_is(self) -> None:
        """Test that complex string annotations are returned unchanged."""
        result = parse_annotation("List[Image]")
        assert result == "List[Image]"

    def test_union_extracts_non_none_type(self) -> None:
        """Test that Union types extract the non-None type correctly."""
        result = parse_annotation(Union[sitk.Image, None])  # noqa: UP007
        assert result is sitk.Image

    def test_optional_extracts_base_type(self) -> None:
        """Test that Optional types extract the base type."""
        result = parse_annotation(Optional[sitk.Transform])  # noqa: UP045
        assert result is sitk.Transform

    def test_plain_type_returned_unchanged(self) -> None:
        """Test that non-Union types are returned as-is."""
        result = parse_annotation(sitk.Image)
        assert result is sitk.Image


class TestResolveOptionalType:
    """Test resolve_optional_type with various Union configurations."""

    def test_union_single_non_none_type(self) -> None:
        """Test Union with single non-None type is marked optional."""
        resolved_type, is_optional = resolve_optional_type(
            Union[sitk.Image, None],  # noqa: UP007
            has_default=False,
        )
        assert resolved_type is sitk.Image
        assert is_optional is True

    def test_optional_type(self) -> None:
        """Test Optional is correctly resolved and marked optional."""
        resolved_type, is_optional = resolve_optional_type(
            Optional[sitk.Transform],  # noqa: UP045
            has_default=False,
        )
        assert resolved_type is sitk.Transform
        assert is_optional is True

    def test_union_multiple_types_not_optional(self) -> None:
        """Test Union with multiple non-None types is not simplified."""
        # Union[str, int, None] should not be treated as Optional[str]
        annotation = Union[str, int, None]  # noqa: UP007
        resolved_type, is_optional = resolve_optional_type(
            annotation, has_default=False
        )
        # Should return the annotation unchanged since multiple non-None types
        assert resolved_type == annotation
        assert is_optional is False

    def test_parameter_with_default_is_optional(self) -> None:
        """Test that has_default=True marks parameter as optional."""
        resolved_type, is_optional = resolve_optional_type(sitk.Image, has_default=True)
        assert resolved_type is sitk.Image
        assert is_optional is True


class TestFindImageTransformParams:
    """Test find_image_transform_params with edge cases."""

    def test_missing_annotation_skipped(self) -> None:
        """Test parameters without type hints are skipped."""
        # Create signature with unannotated parameter
        sig = Signature(
            parameters=[
                Parameter("input", Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        type_hints = {}  # No type hints

        params, optional = find_image_transform_params(sig, type_hints)

        assert params == {}
        assert optional == set()

    def test_optional_image_parameter(self) -> None:
        """Test Optional[Image] is correctly identified as optional."""
        sig = Signature(
            parameters=[
                Parameter(
                    "mask",
                    Parameter.KEYWORD_ONLY,
                    default=None,
                ),
            ]
        )
        type_hints = {"mask": Optional[sitk.Image]}  # noqa: UP045

        params, optional = find_image_transform_params(sig, type_hints)

        assert params == {"mask": sitk.Image}
        assert optional == {"mask"}

    def test_non_type_annotation_handled(self) -> None:
        """Test that non-type annotations don't crash issubclass."""
        # This tests the TypeError exception handler in find_image_transform_params
        sig = Signature(
            parameters=[
                Parameter("data", Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        # Use a non-type object that would cause issubclass to fail
        type_hints = {"data": "not_a_type"}  # String, not a type

        params, optional = find_image_transform_params(sig, type_hints)

        # Should handle gracefully and skip this parameter
        assert params == {}
        assert optional == set()

    def test_transform_with_default_value(self) -> None:
        """Test Transform with default value is marked optional."""
        sig = Signature(
            parameters=[
                Parameter(
                    "transform",
                    Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                ),
            ]
        )
        type_hints = {"transform": sitk.Transform}

        params, optional = find_image_transform_params(sig, type_hints)

        assert params == {"transform": sitk.Transform}
        assert optional == {"transform"}

    def test_generic_type_annotation_handled(self) -> None:
        """Test that generic types that break issubclass are handled gracefully."""
        # Test with a generic type that might cause issubclass to raise TypeError
        sig = Signature(
            parameters=[
                Parameter("data", Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        # List[int] passes isinstance(x, type) but can fail with issubclass
        # in some Python versions
        type_hints = {"data": List[int]}  # noqa: UP006

        params, optional = find_image_transform_params(sig, type_hints)

        # Should handle gracefully and skip this parameter
        assert params == {}
        assert optional == set()
