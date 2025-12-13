"""Integration tests for nested struct parsing and rendering.

These tests verify the complete pipeline from parsing SV files with nested
structs through to rendering them correctly in markdown.
"""
import os
import unittest

from svlang.model import BasicType, StructType, StructField

try:
    import pyslang  # type: ignore[import]
except Exception:
    pyslang = None


class TestSlangBackendNestedStructLookup(unittest.TestCase):
    """Unit test verifying _extract_field_from_member_syntax uses _lookup_type.

    This test verifies the bug fix: nested struct fields should be resolved
    via _lookup_type, not created as BasicType with just the type name.
    """

    @unittest.skipIf(pyslang is None, "pyslang not installed")
    def test_lookup_type_resolves_nested_struct(self):
        """Verify _lookup_type returns StructType for known struct types."""
        from svlang.slang_backend import SlangBackend

        backend = SlangBackend()

        # Load the mini package to populate compilation
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        pkg_path = os.path.join(fixtures_dir, "mini_pkg.sv")

        backend.load_design([pkg_path])

        # Look up a nested struct type - should return StructType, not BasicType
        result = backend._lookup_type("inner_trans_s")

        self.assertIsInstance(result, StructType,
            "inner_trans_s should be resolved as StructType, not BasicType")
        self.assertEqual(result.name, "inner_trans_s")
        # Verify it has the expected fields
        field_names = [f.name for f in result.fields]
        self.assertIn("data", field_names)
        self.assertIn("typ", field_names)
        self.assertIn("sop", field_names)

    @unittest.skipIf(pyslang is None, "pyslang not installed")
    def test_lookup_type_resolves_outer_struct_with_nested(self):
        """Verify outer struct contains properly resolved nested structs."""
        from svlang.slang_backend import SlangBackend

        backend = SlangBackend()

        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        pkg_path = os.path.join(fixtures_dir, "mini_pkg.sv")

        backend.load_design([pkg_path])

        # Look up outer_stream_s which contains inner_trans_s and inner_cred_s
        result = backend._lookup_type("outer_stream_s")

        self.assertIsInstance(result, StructType)
        self.assertEqual(result.name, "outer_stream_s")

        # Find the 'trans' field - should be StructType, not BasicType
        trans_field = next((f for f in result.fields if f.name == "trans"), None)
        self.assertIsNotNone(trans_field, "outer_stream_s should have 'trans' field")
        self.assertIsInstance(trans_field.data_type, StructType,
            "trans field should be StructType (inner_trans_s), not BasicType")

        # Find the 'cred' field - should also be StructType
        cred_field = next((f for f in result.fields if f.name == "cred"), None)
        self.assertIsNotNone(cred_field, "outer_stream_s should have 'cred' field")
        self.assertIsInstance(cred_field.data_type, StructType,
            "cred field should be StructType (inner_cred_s), not BasicType")


@unittest.skipIf(pyslang is None, "pyslang not installed")
class TestNestedStructIntegration(unittest.TestCase):
    """Integration tests parsing mini SV files with nested structs."""

    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.pkg_path = os.path.join(self.fixtures_dir, "mini_pkg.sv")
        self.module_path = os.path.join(self.fixtures_dir, "mini_module.sv")

    def test_parse_module_with_nested_struct_ports(self):
        """Parse mini_module.sv and verify nested struct ports are resolved."""
        from svlang.strategy import Genesis2Strategy

        strategy = Genesis2Strategy()

        # Mock _find_git_root to return fixtures directory
        original_find_git_root = strategy._find_git_root
        strategy._find_git_root = lambda path: self.fixtures_dir

        try:
            strategy.load_design([self.module_path])
            modules = strategy.get_modules()
        finally:
            strategy._find_git_root = original_find_git_root

        self.assertEqual(len(modules), 1)
        mod = modules[0]
        self.assertEqual(mod.name, "mini_module")

        # Find out_stream port - should have outer_stream_s type with nested structs
        out_stream = next((p for p in mod.ports if p.name == "out_stream"), None)
        self.assertIsNotNone(out_stream, "Should have out_stream port")
        self.assertIsInstance(out_stream.data_type, StructType,
            "out_stream should be StructType (outer_stream_s)")

        # Verify nested struct fields are resolved
        if isinstance(out_stream.data_type, StructType):
            trans_field = next((f for f in out_stream.data_type.fields if f.name == "trans"), None)
            self.assertIsNotNone(trans_field)
            self.assertIsInstance(trans_field.data_type, StructType,
                "trans field should be resolved as StructType")

    def test_render_nested_struct_with_indentation(self):
        """Verify markdown renderer shows nested struct fields with indentation."""
        from svlang.strategy import Genesis2Strategy
        from svlang.renderers import MarkdownTableRenderer

        strategy = Genesis2Strategy()
        strategy._find_git_root = lambda path: self.fixtures_dir

        try:
            strategy.load_design([self.module_path])
            modules = strategy.get_modules()
        finally:
            pass

        mod = modules[0]
        renderer = MarkdownTableRenderer()

        # Find a port with nested struct
        out_stream = next((p for p in mod.ports if p.name == "out_stream"), None)
        self.assertIsNotNone(out_stream)

        # Render the struct fields
        if isinstance(out_stream.data_type, StructType):
            result = renderer._format_struct_fields(out_stream.data_type)

            # Should have top-level fields
            self.assertIn("trans", result)
            self.assertIn("cred", result)

            # Should have indented nested fields (4 spaces = 4 &nbsp;)
            # inner_trans_s fields should be indented
            self.assertIn("&nbsp;&nbsp;&nbsp;&nbsp;", result,
                "Nested struct fields should be indented with &nbsp;")

    def test_full_signal_table_with_nested_structs(self):
        """Verify complete signal table renders nested structs in Description."""
        from svlang.strategy import Genesis2Strategy
        from svlang.renderers import MarkdownTableRenderer

        strategy = Genesis2Strategy()
        strategy._find_git_root = lambda path: self.fixtures_dir

        strategy.load_design([self.module_path])
        modules = strategy.get_modules()

        mod = modules[0]
        renderer = MarkdownTableRenderer()
        table = renderer.render_signal_table(mod.ports)

        # Table should contain the signal names
        self.assertIn("out_stream", table)
        self.assertIn("in_stream", table)
        self.assertIn("deep_data", table)

        # Table should show nested struct info in Description column
        # The Description column contains struct field breakdowns
        self.assertIn("trans", table)
        self.assertIn("cred", table)


if __name__ == '__main__':
    unittest.main()
