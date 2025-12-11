import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import io

import chef

try:
    import pyslang  # type: ignore[import]
except Exception:
    pyslang = None  # type: ignore


# Mock Genesis2 module content with import statements
MOCK_GENESIS2_MODULE = """\
// Genesis2 generated file
module test_genesis2
import test_pkg::*;
import other_pkg::*;(
    // Ports for interface
    output my_struct_t     port_a,
    output logic           port_b,
    input var my_struct_t  port_c,
    input var logic [31:0] port_d
);

// Module body
endmodule
"""

# Mock package content
MOCK_TEST_PKG = """\
package test_pkg;
    typedef struct packed {
        logic [7:0] field_a;
        logic [7:0] field_b;
    } my_struct_t;
endpackage
"""

MOCK_OTHER_PKG = """\
package other_pkg;
    typedef logic [15:0] other_type_t;
endpackage
"""


@unittest.skipIf(pyslang is None, "pyslang is not installed, skipping genesis2 tests")
class TestGenesis2Strategy(unittest.TestCase):
    def setUp(self):
        """Set up temporary directory with mock files for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name

        # Create mock module file
        self.module_path = os.path.join(self.test_dir, "test_module.sv")
        with open(self.module_path, "w") as f:
            f.write(MOCK_GENESIS2_MODULE)

        # Create mock package files
        self.pkg_path = os.path.join(self.test_dir, "test_pkg.sv")
        with open(self.pkg_path, "w") as f:
            f.write(MOCK_TEST_PKG)

        self.other_pkg_path = os.path.join(self.test_dir, "other_pkg.sv")
        with open(self.other_pkg_path, "w") as f:
            f.write(MOCK_OTHER_PKG)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_parse_genesis2_module(self):
        from svlang.strategy import Genesis2Strategy

        strategy = Genesis2Strategy()

        # Mock _find_git_root to return our temp directory
        with patch.object(strategy, '_find_git_root', return_value=self.test_dir):
            strategy.load_design([self.module_path])
            modules = strategy.get_modules()

        self.assertTrue(any(mod.name == "test_genesis2" for mod in modules))
        mod = next(m for m in modules if m.name == "test_genesis2")
        port_names = [p.name for p in mod.ports]

        self.assertIn("port_a", port_names)
        self.assertIn("port_b", port_names)
        self.assertIn("port_c", port_names)
        self.assertIn("port_d", port_names)
        self.assertEqual(len(mod.parameters), 0)

    def test_chef_cli_genesis2_strategy(self):
        from svlang.strategy import Genesis2Strategy

        # Capture the test_dir to use in the mock
        test_dir = self.test_dir
        module_path = self.module_path

        # We need to patch it differently for the CLI - use closure to capture test_dir
        with patch.object(Genesis2Strategy, '_find_git_root', lambda self, path: test_dir):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = chef.main(["fetchif", "--strategy", "genesis2", module_path])
            output = buf.getvalue()

        # Should exit successfully
        self.assertEqual(rc, 0)
        self.assertIn("port_a", output)
        self.assertIn("port_d", output)

    def test_extract_imports(self):
        """Test that import extraction works correctly."""
        from svlang.strategy import Genesis2Strategy

        strategy = Genesis2Strategy()
        imports = strategy._extract_imports(self.module_path)

        self.assertIn("test_pkg", imports)
        self.assertIn("other_pkg", imports)
        self.assertEqual(len(imports), 2)

    def test_resolve_packages(self):
        """Test that package resolution finds the correct files."""
        from svlang.strategy import Genesis2Strategy

        strategy = Genesis2Strategy()
        package_names = {"test_pkg", "other_pkg"}
        resolved = strategy._resolve_packages(package_names, self.test_dir)

        self.assertEqual(len(resolved), 2)
        resolved_basenames = {os.path.basename(p) for p in resolved}
        self.assertIn("test_pkg.sv", resolved_basenames)
        self.assertIn("other_pkg.sv", resolved_basenames)


if __name__ == '__main__':
    unittest.main()
