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

    @patch("os.path.isfile", return_value=True)
    @patch("chef.renderer_registry")
    @patch("chef.strategy_registry")
    def test_fetch_if_invokes_strategy_and_renderer(self, mock_strategy_reg, mock_renderer_reg, mock_isfile):
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

    def test_exclude_argument_parsed(self):
        """--exclude should be parsed correctly."""
        parser = chef.build_arg_parser()
        args = parser.parse_args(["fetchif", "--exclude", "clk|rst", "dummy.sv"])
        self.assertEqual(args.exclude, "clk|rst")

    @patch("os.path.isfile", return_value=True)
    @patch("chef.renderer_registry")
    @patch("chef.strategy_registry")
    def test_exclude_filters_ports(self, mock_strategy_reg, mock_renderer_reg, mock_isfile):
        """--exclude should filter out ports matching the regex."""
        mock_strategy = MagicMock()
        mock_renderer = MagicMock(spec=["render_signal_table", "render_parameter_table"])

        mock_strategy_reg.create.return_value = mock_strategy
        mock_strategy_reg.keys.return_value = ["lrm", "genesis2"]
        mock_renderer_reg.create.return_value = mock_renderer
        mock_renderer_reg.keys.return_value = ["markdown", "csv", "html"]

        # Create mock ports with name attribute
        port_clk = MagicMock()
        port_clk.name = "clk"
        port_data = MagicMock()
        port_data.name = "data_in"
        port_rst = MagicMock()
        port_rst.name = "rst_n"

        mock_module = MagicMock()
        mock_module.name = "test_mod"
        mock_module.ports = [port_clk, port_data, port_rst]
        mock_module.parameters = []

        mock_strategy.get_modules.return_value = [mock_module]
        mock_renderer.render_signal_table.return_value = ""
        mock_renderer.render_parameter_table.return_value = ""

        buf = io.StringIO()
        with redirect_stdout(buf):
            chef.main(["fetchif", "--exclude", "clk|rst", "test.sv"])

        # Check that render_signal_table was called with filtered ports
        call_args = mock_renderer.render_signal_table.call_args[0][0]
        filtered_names = [p.name for p in call_args]
        self.assertEqual(filtered_names, ["data_in"])

    @patch("os.path.isfile", return_value=True)
    @patch("chef.renderer_registry")
    @patch("chef.strategy_registry")
    def test_exclude_filters_parameters(self, mock_strategy_reg, mock_renderer_reg, mock_isfile):
        """--exclude should filter out parameters matching the regex."""
        mock_strategy = MagicMock()
        mock_renderer = MagicMock(spec=["render_signal_table", "render_parameter_table"])

        mock_strategy_reg.create.return_value = mock_strategy
        mock_strategy_reg.keys.return_value = ["lrm", "genesis2"]
        mock_renderer_reg.create.return_value = mock_renderer
        mock_renderer_reg.keys.return_value = ["markdown", "csv", "html"]

        # Create mock parameters with name attribute
        param_width = MagicMock()
        param_width.name = "WIDTH"
        param_debug = MagicMock()
        param_debug.name = "DEBUG_MODE"

        mock_module = MagicMock()
        mock_module.name = "test_mod"
        mock_module.ports = []
        mock_module.parameters = [param_width, param_debug]

        mock_strategy.get_modules.return_value = [mock_module]
        mock_renderer.render_signal_table.return_value = ""
        mock_renderer.render_parameter_table.return_value = ""

        buf = io.StringIO()
        with redirect_stdout(buf):
            chef.main(["fetchif", "--exclude", "DEBUG.*", "test.sv"])

        # Check that render_parameter_table was called with filtered params
        call_args = mock_renderer.render_parameter_table.call_args[0][0]
        filtered_names = [p.name for p in call_args]
        self.assertEqual(filtered_names, ["WIDTH"])

    @patch("chef.strategy_registry")
    def test_exclude_invalid_regex_exits(self, mock_strategy_reg):
        """--exclude with invalid regex should exit with error."""
        mock_strategy_reg.keys.return_value = ["lrm", "genesis2"]

        with self.assertRaises(SystemExit) as ctx:
            chef.main(["fetchif", "--exclude", "[invalid", "test.sv"])

        # Check it's a non-zero exit (error message contains "Invalid regex")
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
