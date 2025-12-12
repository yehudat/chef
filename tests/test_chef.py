import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock

import chef


class TestChefCLI(unittest.TestCase):
    def test_no_arguments_prints_help_and_returns_nonzero(self):
        """Calling main([]) should print help and return 1."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = chef.main([])

        output = buf.getvalue()
        self.assertNotEqual(rc, 0)
        self.assertIn("Facade for SystemVerilog utilities", output)
        # Sanity: should show usage / help
        self.assertIn("usage:", output)

    def test_csv_format_accepted(self):
        """--format csv should be accepted and use CsvTableRenderer."""
        # Just verify parsing accepts the format - actual rendering tested in test_csv_renderer.py
        parser = chef.build_arg_parser()
        args = parser.parse_args(["--format", "csv", "fetchif", "dummy.sv"])
        self.assertEqual(args.format, "csv")

    @patch("chef.renderer_registry")
    @patch("chef.strategy_registry")
    def test_fetch_if_invokes_strategy_and_renderer(self, mock_strategy_reg, mock_renderer_reg):
        """fetchif should call the selected strategy and render tables."""
        # Arrange: fake strategy and renderer
        mock_strategy = MagicMock()
        mock_renderer = MagicMock(spec=["render_signal_table", "render_parameter_table"])

        mock_strategy_reg.create.return_value = mock_strategy
        mock_strategy_reg.keys.return_value = ["lrm", "genesis2"]
        mock_renderer_reg.create.return_value = mock_renderer
        mock_renderer_reg.keys.return_value = ["markdown", "csv", "html"]

        mock_module = MagicMock()
        mock_module.name = "my_mod"
        mock_module.ports = ["PORT1", "PORT2"]
        mock_module.parameters = ["PARAM1"]

        mock_strategy.get_modules.return_value = [mock_module]
        mock_renderer.render_signal_table.return_value = "SIGNAL_TABLE_MD"
        mock_renderer.render_parameter_table.return_value = "PARAM_TABLE_MD"

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = chef.main(["fetchif", "--strategy", "lrm", "my_design.sv"])

        # Assert exit code
        self.assertEqual(rc, 0)

        # Assert strategy registry is used correctly
        mock_strategy_reg.create.assert_called_once_with("lrm")
        mock_strategy.load_design.assert_called_once_with(["my_design.sv"])
        mock_strategy.get_modules.assert_called_once_with()

        # Assert renderer registry is used correctly
        mock_renderer_reg.create.assert_called_once_with("markdown")
        mock_renderer.render_signal_table.assert_called_once_with(mock_module.ports)
        mock_renderer.render_parameter_table.assert_called_once_with(mock_module.parameters)

        output = buf.getvalue()

        # High-level sanity checks on output
        self.assertIn("# Module my_mod", output)
        self.assertIn("SIGNAL_TABLE_MD", output)
        self.assertIn("PARAM_TABLE_MD", output)


if __name__ == "__main__":
    unittest.main()
