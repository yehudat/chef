import os
import unittest
from contextlib import redirect_stdout
import io

import chef

try:
    import pyslang  # type: ignore[import]
except Exception:
    pyslang = None  # type: ignore


@unittest.skipIf(pyslang is None, "pyslang is not installed, skipping genesis2 tests")
class TestGenesis2Strategy(unittest.TestCase):
    def test_parse_genesis2_module(self):
        here = os.path.dirname(__file__)
        sv_path = os.path.abspath(os.path.join(here, os.pardir, "ppc_d2d.sv"))

        from svlang.strategy import Genesis2Strategy
        strategy = Genesis2Strategy()
        strategy.load_design([sv_path])
        modules = strategy.get_modules()

        self.assertTrue(any(mod.name == "ppc_d2d" for mod in modules))
        mod = next(m for m in modules if m.name == "ppc_d2d")
        port_names = [p.name for p in mod.ports]

        self.assertIn("noc_pipe0_out_if__bus", port_names)
        self.assertIn("pll0_apb_if__paddr", port_names)
        self.assertEqual(len(mod.parameters), 0)

    def test_chef_cli_genesis2_strategy(self):
        # Capture output of chef CLI using genesis2 strategy
        here = os.path.dirname(__file__)
        sv_path = os.path.abspath(os.path.join(here, os.pardir, "ppc_d2d.sv"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = chef.main(["fetchif", "--strategy", "genesis2", sv_path])
        output = buf.getvalue()
        # Should exit successfully
        self.assertEqual(rc, 0)
        self.assertIn("noc_pipe0_out_if__bus", output)
        self.assertIn("pll0_apb_if__paddr", output)


if __name__ == '__main__':
    unittest.main()
