import unittest

from svlang.model import BasicType, Port, Parameter, StructField, StructType, UnionType
from svlang.renderers import HtmlTreeRenderer


class TestHtmlRendererBasic(unittest.TestCase):
    """Test basic HTML rendering functionality."""

    def setUp(self):
        self.renderer = HtmlTreeRenderer()

    def test_simple_port_rendering(self):
        """Simple ports should render as tree items."""
        ports = [
            Port(name="clk", direction="input", data_type=BasicType("logic")),
            Port(name="data_out", direction="output", data_type=BasicType("logic", "[31:0]")),
        ]
        result = self.renderer.render_signal_table(ports)

        self.assertIn("clk", result)
        self.assertIn("data_out", result)
        self.assertIn("tree-item", result)
        self.assertIn("dir-input", result)
        self.assertIn("dir-output", result)

    def test_html_escaping(self):
        """Special characters should be escaped."""
        ports = [
            Port(name="data<0>", direction="input", data_type=BasicType("logic")),
        ]
        result = self.renderer.render_signal_table(ports)

        self.assertIn("data&lt;0&gt;", result)
        self.assertNotIn("data<0>", result)

    def test_parameter_rendering(self):
        """Parameters should render as HTML table."""
        params = [
            Parameter(name="WIDTH", data_type=BasicType("integer"), default="32"),
        ]
        result = self.renderer.render_parameter_table(params)

        self.assertIn("param-table", result)
        self.assertIn("WIDTH", result)
        self.assertIn("32", result)

    def test_empty_parameters(self):
        """Empty parameters should show 'No parameters'."""
        result = self.renderer.render_parameter_table([])
        self.assertIn("No parameters", result)


class TestHtmlRendererExpandable(unittest.TestCase):
    """Test expandable tree functionality for complex types."""

    def setUp(self):
        self.renderer = HtmlTreeRenderer()

    def test_struct_port_is_expandable(self):
        """Struct ports should have expandable class."""
        inner = StructType("inner_t", [
            StructField("x", BasicType("logic")),
        ])
        ports = [
            Port(name="data", direction="output", data_type=inner),
        ]
        result = self.renderer.render_signal_table(ports)

        self.assertIn("expandable", result)
        self.assertIn("has-children", result)
        self.assertIn("tree-children", result)

    def test_nested_struct_fields_rendered(self):
        """Nested struct fields should be rendered."""
        inner = StructType("inner_t", [
            StructField("field_a", BasicType("logic")),
            StructField("field_b", BasicType("logic", "[7:0]")),
        ])
        ports = [
            Port(name="data", direction="output", data_type=inner),
        ]
        result = self.renderer.render_signal_table(ports)

        self.assertIn("field_a", result)
        self.assertIn("field_b", result)
        self.assertIn("field-item", result)

    def test_deeply_nested_struct(self):
        """3-level nested struct should render recursively."""
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

        self.assertIn("level1_t", result)
        self.assertIn("level2_t", result)
        self.assertIn("level3_t", result)
        self.assertIn("deep", result)
        self.assertIn("nested-fields", result)

    def test_union_is_expandable(self):
        """Union types should also be expandable."""
        union = UnionType("my_union_t", [
            StructField("opt_a", BasicType("logic", "[7:0]")),
            StructField("opt_b", BasicType("logic", "[15:0]")),
        ])
        ports = [
            Port(name="union_port", direction="output", data_type=union),
        ]
        result = self.renderer.render_signal_table(ports)

        self.assertIn("expandable", result)
        self.assertIn("opt_a", result)
        self.assertIn("opt_b", result)


class TestHtmlRendererFullPage(unittest.TestCase):
    """Test full HTML page rendering."""

    def setUp(self):
        self.renderer = HtmlTreeRenderer()

    def test_full_page_structure(self):
        """Full page should have proper HTML structure."""
        signals_html = "<ul>signals</ul>"
        params_html = "<table>params</table>"
        result = self.renderer.render_full_page("test_module", signals_html, params_html)

        self.assertIn("<!DOCTYPE html>", result)
        self.assertIn("<html", result)
        self.assertIn("</html>", result)
        self.assertIn("<head>", result)
        self.assertIn("<body>", result)
        self.assertIn("<style>", result)
        self.assertIn("<script>", result)

    def test_full_page_contains_module_name(self):
        """Full page should contain module name in title and heading."""
        result = self.renderer.render_full_page("my_module", "", "")

        self.assertIn("my_module", result)
        self.assertIn("<title>my_module", result)
        self.assertIn("<h1>my_module</h1>", result)

    def test_full_page_contains_css(self):
        """Full page should contain embedded CSS."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn("--accent-blue", result)
        self.assertIn("--accent-green", result)
        self.assertIn(".tree-item", result)

    def test_full_page_contains_js(self):
        """Full page should contain embedded JavaScript."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn("addEventListener", result)
        self.assertIn("classList.toggle", result)


class TestHtmlRendererRegistry(unittest.TestCase):
    """Test HTML renderer registry integration."""

    def test_html_registered(self):
        """HTML renderer should be registered."""
        from svlang.renderers import renderer_registry
        self.assertIn("html", renderer_registry)

    def test_html_creation(self):
        """HTML renderer should be creatable from registry."""
        from svlang.renderers import renderer_registry
        renderer = renderer_registry.create("html")
        self.assertIsInstance(renderer, HtmlTreeRenderer)


if __name__ == '__main__':
    unittest.main()
