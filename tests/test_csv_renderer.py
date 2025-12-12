import csv
import io
import unittest

from svlang.model import BasicType, Port, Parameter, StructField, StructType, UnionType
from svlang.renderer import CsvTableRenderer


class TestCsvRendererBasic(unittest.TestCase):
    """Test basic CSV rendering functionality."""

    def setUp(self):
        self.renderer = CsvTableRenderer()

    def test_simple_port_rendering(self):
        """Simple ports should render with single type column."""
        ports = [
            Port(name="clk", direction="input", data_type=BasicType("logic")),
            Port(name="data_out", direction="output", data_type=BasicType("logic", "[31:0]")),
        ]
        result = self.renderer.render_signal_table(ports)

        # Parse CSV output
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Check headers
        self.assertIn("Signal Name", rows[0])
        self.assertIn("Type Level 1", rows[0])

        # Check data rows
        self.assertEqual(rows[1][0], "clk")
        self.assertEqual(rows[1][1], "input")
        self.assertEqual(rows[2][0], "data_out")
        self.assertEqual(rows[2][1], "output")

    def test_parameter_rendering(self):
        """Parameters should render as simple CSV table."""
        params = [
            Parameter(name="WIDTH", data_type=BasicType("integer"), default="32"),
            Parameter(name="DEPTH", data_type=BasicType("integer"), default="16"),
        ]
        result = self.renderer.render_parameter_table(params)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Check headers
        self.assertEqual(rows[0][0], "Generic Name")
        self.assertEqual(rows[0][1], "Type")
        self.assertEqual(rows[0][3], "Default Value")

        # Check data
        self.assertEqual(rows[1][0], "WIDTH")
        self.assertEqual(rows[1][3], "32")
        self.assertEqual(rows[2][0], "DEPTH")
        self.assertEqual(rows[2][3], "16")


class TestCsvRendererHierarchy(unittest.TestCase):
    """Test CSV rendering with hierarchical struct columns."""

    def setUp(self):
        self.renderer = CsvTableRenderer()

    def test_nested_struct_creates_hierarchy_columns(self):
        """Nested struct fields should appear in separate hierarchy columns."""
        inner = StructType("inner_t", [
            StructField("x", BasicType("logic")),
            StructField("y", BasicType("logic", "[7:0]")),
        ])
        outer = StructType("outer_t", [
            StructField("inner", inner),
            StructField("z", BasicType("logic")),
        ])
        ports = [
            Port(name="data", direction="output", data_type=outer),
        ]
        result = self.renderer.render_signal_table(ports)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Should have Type Level 1, Type Level 2, Type Level 3 columns
        self.assertIn("Type Level 1", rows[0])
        self.assertIn("Type Level 2", rows[0])
        self.assertIn("Type Level 3", rows[0])

        # First row: port with outer_t in Level 1
        type_level_1_idx = rows[0].index("Type Level 1")
        self.assertEqual(rows[1][type_level_1_idx], "outer_t")

        # Nested field rows should have empty base columns
        # inner_t inner at Level 2
        self.assertEqual(rows[2][0], "")  # Signal Name empty
        self.assertEqual(rows[2][type_level_1_idx], "")  # Level 1 empty
        self.assertIn("inner_t inner", rows[2][type_level_1_idx + 1])  # Level 2

    def test_deeply_nested_struct_columns(self):
        """3-level nested struct should use 4 type columns."""
        level3 = StructType("level3_t", [
            StructField("deep", BasicType("logic", "[31:0]")),
        ])
        level2 = StructType("level2_t", [
            StructField("mid", level3),
        ])
        level1 = StructType("level1_t", [
            StructField("top", level2),
        ])
        ports = [
            Port(name="nested_port", direction="input", data_type=level1),
        ]
        result = self.renderer.render_signal_table(ports)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Should have 4 type level columns (1 for port type + 3 nesting levels)
        type_cols = [h for h in rows[0] if h.startswith("Type Level")]
        self.assertEqual(len(type_cols), 4)

        # Verify hierarchy:
        # Row 1: level1_t in Level 1
        # Row 2: level2_t top in Level 2
        # Row 3: level3_t mid in Level 3
        # Row 4: logic [31:0] deep in Level 4
        type_level_1_idx = rows[0].index("Type Level 1")
        self.assertEqual(rows[1][type_level_1_idx], "level1_t")
        self.assertIn("level2_t top", rows[2][type_level_1_idx + 1])
        self.assertIn("level3_t mid", rows[3][type_level_1_idx + 2])
        self.assertIn("logic [31:0] deep", rows[4][type_level_1_idx + 3])

    def test_union_nested_in_struct(self):
        """Union nested in struct should also be recursively expanded."""
        inner_union = UnionType("inner_union_t", [
            StructField("opt_a", BasicType("logic", "[7:0]")),
            StructField("opt_b", BasicType("logic", "[15:0]")),
        ])
        outer = StructType("outer_t", [
            StructField("data", inner_union),
        ])
        ports = [
            Port(name="union_port", direction="output", data_type=outer),
        ]
        result = self.renderer.render_signal_table(ports)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Should have union fields expanded
        all_text = result
        self.assertIn("inner_union_t data", all_text)
        self.assertIn("logic [7:0] opt_a", all_text)
        self.assertIn("logic [15:0] opt_b", all_text)

    def test_empty_columns_for_hierarchy(self):
        """Nested field rows should have empty preceding columns."""
        inner = StructType("inner_t", [
            StructField("field", BasicType("logic")),
        ])
        outer = StructType("outer_t", [
            StructField("inner", inner),
        ])
        ports = [
            Port(name="test", direction="input", data_type=outer),
        ]
        result = self.renderer.render_signal_table(ports)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Row 3 should be the deeply nested field (logic field)
        # All base columns should be empty
        nested_row = rows[3]  # Header, port row, inner_t inner row, logic field row
        self.assertEqual(nested_row[0], "")  # Signal Name
        self.assertEqual(nested_row[1], "")  # Direction
        self.assertEqual(nested_row[2], "")  # Reset Value
        self.assertEqual(nested_row[3], "")  # Default Value
        self.assertEqual(nested_row[4], "")  # clk Domain


class TestCsvRendererMaxDepth(unittest.TestCase):
    """Test max depth limiting for CSV renderer."""

    def test_max_depth_limits_columns(self):
        """Renderer should respect max_depth setting."""
        renderer = CsvTableRenderer(max_depth=2)

        level3 = StructType("level3_t", [
            StructField("deep", BasicType("logic")),
        ])
        level2 = StructType("level2_t", [
            StructField("mid", level3),
        ])
        level1 = StructType("level1_t", [
            StructField("top", level2),
        ])
        ports = [
            Port(name="test", direction="input", data_type=level1),
        ]
        result = renderer.render_signal_table(ports)

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Should only have 2 type columns due to max_depth
        type_cols = [h for h in rows[0] if h.startswith("Type Level")]
        self.assertEqual(len(type_cols), 2)

    def test_get_max_struct_depth(self):
        """_get_max_struct_depth should correctly calculate nesting depth."""
        renderer = CsvTableRenderer()

        # Simple type - depth 1
        basic = BasicType("logic")
        self.assertEqual(renderer._get_max_struct_depth(basic), 1)

        # One level struct - depth 2 (port type + 1 field level)
        simple_struct = StructType("s", [
            StructField("a", BasicType("logic")),
        ])
        self.assertEqual(renderer._get_max_struct_depth(simple_struct), 2)

        # Two level nested - depth 3
        inner = StructType("inner", [StructField("x", BasicType("logic"))])
        outer = StructType("outer", [StructField("i", inner)])
        self.assertEqual(renderer._get_max_struct_depth(outer), 3)


class TestCsvRendererCLIIntegration(unittest.TestCase):
    """Test CSV renderer integration with CLI."""

    def test_csv_format_accepted(self):
        """CLI should accept --format csv without error."""
        import chef

        # This should not raise - just check it parses
        parser = chef.build_arg_parser()
        args = parser.parse_args(["--format", "csv", "fetchif", "dummy.sv"])
        self.assertEqual(args.format, "csv")


if __name__ == '__main__':
    unittest.main()
