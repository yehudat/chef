import unittest

from svlang.model import BasicType, StructField, StructType, UnionType
from svlang.renderer import MarkdownTableRenderer


class TestNestedStructParsing(unittest.TestCase):
    """Test that nested structs are correctly modeled and iterable."""

    def test_simple_struct_iter_fields(self):
        """A simple struct should yield its fields."""
        inner = StructType("inner_t", [
            StructField("a", BasicType("logic")),
            StructField("b", BasicType("logic", "[7:0]")),
        ])
        fields = list(inner.iter_fields())
        self.assertEqual(len(fields), 2)
        names = [name for name, _ in fields]
        self.assertIn("a", names)
        self.assertIn("b", names)

    def test_nested_struct_iter_fields(self):
        """Nested structs should yield flattened field paths."""
        inner = StructType("inner_t", [
            StructField("x", BasicType("logic")),
            StructField("y", BasicType("logic")),
        ])
        outer = StructType("outer_t", [
            StructField("inner", inner),
            StructField("z", BasicType("logic")),
        ])
        fields = list(outer.iter_fields())
        names = [name for name, _ in fields]
        # Should have flattened paths: inner.x, inner.y, z
        self.assertIn("inner.x", names)
        self.assertIn("inner.y", names)
        self.assertIn("z", names)

    def test_deeply_nested_struct_iter_fields(self):
        """Deeply nested structs (3 levels) should yield correct paths."""
        level3 = StructType("level3_t", [
            StructField("deep", BasicType("logic", "[31:0]")),
        ])
        level2 = StructType("level2_t", [
            StructField("mid", level3),
        ])
        level1 = StructType("level1_t", [
            StructField("top", level2),
            StructField("val", BasicType("logic")),
        ])
        fields = list(level1.iter_fields())
        names = [name for name, _ in fields]
        self.assertIn("top.mid.deep", names)
        self.assertIn("val", names)


class TestNestedStructRendering(unittest.TestCase):
    """Test that the markdown renderer correctly formats nested structs."""

    def setUp(self):
        self.renderer = MarkdownTableRenderer()

    def test_simple_struct_rendering(self):
        """Simple struct fields should render without indentation."""
        struct = StructType("my_struct_t", [
            StructField("field_a", BasicType("logic")),
            StructField("field_b", BasicType("logic", "[7:0]")),
        ])
        result = self.renderer._format_struct_fields(struct)
        self.assertIn("logic field_a", result)
        self.assertIn("logic [7:0] field_b", result)
        # No indentation at top level
        self.assertNotIn("&nbsp;logic field_a", result)

    def test_nested_struct_rendering_with_indentation(self):
        """Nested struct fields should have 4-space indentation."""
        inner = StructType("inner_t", [
            StructField("x", BasicType("logic")),
        ])
        outer = StructType("outer_t", [
            StructField("inner", inner),
        ])
        result = self.renderer._format_struct_fields(outer)
        # outer.inner should appear without indentation
        self.assertIn("inner_t inner", result)
        # inner.x should have 4 nbsp (1 indent level)
        self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;logic x", result)

    def test_deeply_nested_struct_rendering(self):
        """3-level nested struct should have correct indentation."""
        level3 = StructType("level3_t", [
            StructField("deep", BasicType("logic")),
        ])
        level2 = StructType("level2_t", [
            StructField("mid", level3),
        ])
        level1 = StructType("level1_t", [
            StructField("top", level2),
        ])
        result = self.renderer._format_struct_fields(level1)
        # level1.top (level2_t) - no indentation
        self.assertIn("level2_t top", result)
        # level2.mid (level3_t) - 4 spaces
        self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;level3_t mid", result)
        # level3.deep - 8 spaces (2 indent levels)
        self.assertIn("&nbsp;" * 8 + "logic deep", result)

    def test_mixed_struct_with_basic_and_nested(self):
        """Struct with both basic and nested fields should render correctly."""
        inner = StructType("inner_t", [
            StructField("nested_field", BasicType("logic")),
        ])
        outer = StructType("outer_t", [
            StructField("basic_field", BasicType("logic", "[31:0]")),
            StructField("struct_field", inner),
        ])
        result = self.renderer._format_struct_fields(outer)
        # Basic field at top level
        self.assertIn("logic [31:0] basic_field", result)
        # Struct field at top level
        self.assertIn("inner_t struct_field", result)
        # Nested field with indentation
        self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;logic nested_field", result)

    def test_union_nested_in_struct(self):
        """Union nested in struct should also be recursively formatted."""
        inner_union = UnionType("inner_union_t", [
            StructField("opt_a", BasicType("logic", "[7:0]")),
            StructField("opt_b", BasicType("logic", "[15:0]")),
        ])
        outer = StructType("outer_t", [
            StructField("data", inner_union),
        ])
        result = self.renderer._format_struct_fields(outer)
        self.assertIn("inner_union_t data", result)
        self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;logic [7:0] opt_a", result)
        self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;logic [15:0] opt_b", result)


if __name__ == '__main__':
    unittest.main()
