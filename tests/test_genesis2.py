import os
import unittest
from contextlib import redirect_stdout
import io

import os
import sys
# Insert project root into sys.path so that 'chef' and the svlang package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from svlang.genesis2 import Genesis2Parser
import chef


class TestGenesis2Parser(unittest.TestCase):
    def setUp(self):
        # Path to the genesis2 generated fixture
        self.fixture_path = os.path.join(os.path.dirname(__file__), os.pardir, "ppc_d2d.sv")
        self.parser = Genesis2Parser()

    def test_parse_genesis2_module(self):
        modules = self.parser.parse_file(self.fixture_path)
        # Should at least find one module
        self.assertGreaterEqual(len(modules), 1)
        mod = modules[0]
        # Genesis2 module name should be ppc_d2d
        self.assertEqual(mod.name, "ppc_d2d")
        # Should discover ports
        self.assertGreater(len(mod.ports), 0)
        port_names = [p.name for p in mod.ports]
        # A few specific ports should be present
        self.assertIn("noc_pipe0_out_if__bus", port_names)
        self.assertIn("pll0_apb_if__paddr", port_names)
        # Validate data types of known ports
        for p in mod.ports:
            if p.name == "noc_pipe0_out_if__bus":
                self.assertEqual(str(p.data_type), "noc_stream_s")
            if p.name == "pll0_apb_if__paddr":
                # Expect a packed bit range with 31:0
                self.assertTrue("31:0" in str(p.data_type))
        # Genesis2 fixture has no parameter list
        self.assertEqual(len(mod.parameters), 0)

    def test_chef_cli_genesis2_strategy(self):
        # Capture output of chef CLI using genesis2 strategy
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = chef.main(["fetchif", "--strategy", "genesis2", self.fixture_path])
        output = buf.getvalue()
        # Should exit successfully
        self.assertEqual(rc, 0)
        # Should include module name header
        self.assertIn("# Module ppc_d2d", output)
        # Should include some known port names
        self.assertIn("noc_pipe0_out_if__bus", output)
        self.assertIn("pll0_apb_if__paddr", output)


if __name__ == '__main__':
    unittest.main()