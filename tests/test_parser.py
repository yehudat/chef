import os
import unittest

from svlang import SVParser, MarkdownTableRenderer


class TestSVParser(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.join(os.path.dirname(__file__), "test_module.sv")
        self.parser = SVParser()

    def test_parse_struct(self):
        modules = self.parser.parse_file(self.fixture_path)
        # Ensure composite types are detected
        self.assertIn("payload_t", self.parser._types)
        dtype = self.parser._types["payload_t"]
        # payload_t should be a struct with two fields
        fields = list(dtype.iter_fields())
        self.assertEqual(len(fields), 2)
        self.assertEqual(set(name for name, _ in fields), {"data", "valid"})

    def test_parse_module(self):
        modules = self.parser.parse_file(self.fixture_path)
        self.assertEqual(len(modules), 1)
        mod = modules[0]
        self.assertEqual(mod.name, "my_mod")
        # Check parameters
        self.assertEqual(len(mod.parameters), 2)
        names = {p.name for p in mod.parameters}
        self.assertEqual(names, {"WIDTH", "data_t"})
        # Check ports
        self.assertEqual(len(mod.ports), 4)
        port_names = [p.name for p in mod.ports]
        self.assertEqual(port_names, ["clk", "rst_n", "in_data", "out_data"])
        # Check port types
        for p in mod.ports:
            if p.name == "clk":
                self.assertEqual(str(p.data_type), "logic")
            if p.name == "in_data":
                # Should be payload_t type
                self.assertEqual(str(p.data_type), "payload_t")
                # Expand fields through iter_fields
                fields = list(p.data_type.iter_fields(prefix=p.name))
                field_names = [name for name, _ in fields]
                self.assertEqual(set(field_names), {"in_data.data", "in_data.valid"})

    def test_markdown_renderer(self):
        modules = self.parser.parse_file(self.fixture_path)
        mod = modules[0]
        renderer = MarkdownTableRenderer()
        sig_table = renderer.render_signal_table(mod.ports)
        lines = sig_table.splitlines()
        self.assertTrue(lines[0].startswith("| Signal Name"))
        self.assertIn("clk", sig_table)
        self.assertIn("in_data", sig_table)
        param_table = renderer.render_parameter_table(mod.parameters)
        self.assertTrue(param_table.startswith("| Generic Name"))
        self.assertIn("WIDTH", param_table)
        self.assertIn("data_t", param_table)


if __name__ == '__main__':
    unittest.main()
