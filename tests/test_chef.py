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

    def test_rejects_non_markdown_format(self):
        """--format csv is currently unsupported and should return 2."""
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = chef.main(["--format", "csv", "fetchif", "dummy.sv"])

        self.assertEqual(rc, 2)
        stderr_output = err.getvalue()
        self.assertIn("Only markdown output is implemented", stderr_output)

    @patch("chef.MarkdownTableRenderer")
    @patch("chef.LRM2017Strategy")
    def test_fetch_if_invokes_strategy_and_renderer(self, mock_strategy_cls, mock_renderer_cls):
        """fetchif should call the selected strategy and render tables."""
        # Arrange: fake strategy and renderer
        mock_strategy = mock_strategy_cls.return_value
        mock_renderer = mock_renderer_cls.return_value

        mock_module = MagicMock()
        mock_module.name = "my_mod"
        mock_module.ports = ["PORT1", "PORT2"]
        mock_module.parameters = ["PARAM1"]

        mock_strategy.get_modules.return_value = [mock_module]
        mock_renderer.render_signal_table.return_value = "SIGNAL_TABLE_MD"
        mock_renderer.render_parameter_table.return_value = "PARAM_TABLE_MD"

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = chef.main(["fetchif", "my_design.sv"])

        # Assert exit code
        self.assertEqual(rc, 0)

        # Assert parser is used correctly
        mock_strategy_cls.assert_called_once_with()
        mock_strategy.load_design.assert_called_once_with(["my_design.sv"])
        mock_strategy.get_modules.assert_called_once_with()

        # Assert renderer is used correctly
        mock_renderer_cls.assert_called_once_with()
        mock_renderer.render_signal_table.assert_called_once_with(mock_module.ports)
        mock_renderer.render_parameter_table.assert_called_once_with(mock_module.parameters)

        output = buf.getvalue()

        # High-level sanity checks on output
        self.assertIn("# Module my_mod", output)
        self.assertIn("SIGNAL_TABLE_MD", output)
        self.assertIn("PARAM_TABLE_MD", output)


if __name__ == "__main__":
    unittest.main()
