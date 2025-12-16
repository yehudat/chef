import unittest
from pathlib import Path

from svlang.model import BasicType, Port, Parameter, StructField, StructType, UnionType
from svlang.renderers import HtmlTreeRenderer
from svlang.renderers.html import TEMPLATES_DIR


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


class TestHtmlRendererFilterPanel(unittest.TestCase):
    """Test HTML filter panel functionality."""

    def setUp(self):
        self.renderer = HtmlTreeRenderer()

    def test_filter_panel_in_full_page(self):
        """Full page should contain filter panel."""
        result = self.renderer.render_full_page("test_module", "", "")

        self.assertIn("filter-panel", result)
        self.assertIn("filter-input", result)
        self.assertIn("filter-exclude", result)
        self.assertIn("filter-clear", result)

    def test_filter_panel_has_exclude_checkbox(self):
        """Filter panel should have 'Hide matching' checkbox."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn('type="checkbox"', result)
        self.assertIn("Hide matching", result)
        self.assertIn("filter-exclude", result)

    def test_filter_panel_has_clear_button(self):
        """Filter panel should have clear button."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn("filter-clear", result)
        self.assertIn("Clear", result)

    def test_filter_panel_has_status(self):
        """Filter panel should have status area."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn("filter-status", result)

    def test_js_contains_filter_logic(self):
        """JavaScript should contain filter logic."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn("applyFilter", result)
        self.assertIn("RegExp", result)
        self.assertIn("filter-input", result)

    def test_css_contains_filter_styles(self):
        """CSS should contain filter panel styles."""
        result = self.renderer.render_full_page("test", "", "")

        self.assertIn(".filter-panel", result)
        self.assertIn(".filter-input", result)
        self.assertIn(".hidden", result)


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


class TestHtmlTemplateFiles(unittest.TestCase):
    """Test that template files exist and are properly structured."""

    def test_templates_directory_exists(self):
        """Templates directory should exist."""
        self.assertTrue(TEMPLATES_DIR.exists())
        self.assertTrue(TEMPLATES_DIR.is_dir())

    def test_css_file_exists(self):
        """CSS template file should exist."""
        css_path = TEMPLATES_DIR / "html_styles.css"
        self.assertTrue(css_path.exists())
        self.assertTrue(css_path.is_file())

    def test_js_file_exists(self):
        """JavaScript template file should exist."""
        js_path = TEMPLATES_DIR / "html_scripts.js"
        self.assertTrue(js_path.exists())
        self.assertTrue(js_path.is_file())

    def test_jinja2_template_exists(self):
        """Jinja2 page template should exist."""
        template_path = TEMPLATES_DIR / "html_page.jinja2"
        self.assertTrue(template_path.exists())
        self.assertTrue(template_path.is_file())

    def test_all_template_files_readable(self):
        """All template files should be readable."""
        for filename in ["html_styles.css", "html_scripts.js", "html_page.jinja2"]:
            path = TEMPLATES_DIR / filename
            content = path.read_text()
            self.assertGreater(len(content), 0, f"{filename} should not be empty")


class TestHtmlTemplateCss(unittest.TestCase):
    """Test CSS template file content."""

    @classmethod
    def setUpClass(cls):
        cls.css_content = (TEMPLATES_DIR / "html_styles.css").read_text()

    def test_css_has_root_variables(self):
        """CSS should define root CSS variables."""
        self.assertIn(":root", self.css_content)
        self.assertIn("--bg-primary", self.css_content)
        self.assertIn("--text-primary", self.css_content)

    def test_css_has_tree_styles(self):
        """CSS should have signal tree styles."""
        self.assertIn(".tree", self.css_content)
        self.assertIn(".tree-item", self.css_content)
        self.assertIn(".tree-header", self.css_content)

    def test_css_has_direction_classes(self):
        """CSS should have direction indicator classes."""
        self.assertIn(".dir-input", self.css_content)
        self.assertIn(".dir-output", self.css_content)
        self.assertIn(".dir-inout", self.css_content)

    def test_css_has_filter_panel_styles(self):
        """CSS should have filter panel styles."""
        self.assertIn(".filter-panel", self.css_content)
        self.assertIn(".filter-input", self.css_content)
        self.assertIn(".filter-checkbox", self.css_content)

    def test_css_has_hidden_class(self):
        """CSS should define hidden class for filtering."""
        self.assertIn(".hidden", self.css_content)
        self.assertIn("display: none", self.css_content)

    def test_css_has_parameter_table_styles(self):
        """CSS should have parameter table styles."""
        self.assertIn(".param-table", self.css_content)
        self.assertIn(".param-name", self.css_content)


class TestHtmlTemplateJs(unittest.TestCase):
    """Test JavaScript template file content."""

    @classmethod
    def setUpClass(cls):
        cls.js_content = (TEMPLATES_DIR / "html_scripts.js").read_text()

    def test_js_has_dom_ready_handler(self):
        """JavaScript should have DOMContentLoaded handler."""
        self.assertIn("DOMContentLoaded", self.js_content)
        self.assertIn("addEventListener", self.js_content)

    def test_js_has_tree_expansion_logic(self):
        """JavaScript should handle tree expansion."""
        self.assertIn(".tree-header.expandable", self.js_content)
        self.assertIn("classList.toggle", self.js_content)
        self.assertIn("expanded", self.js_content)

    def test_js_has_filter_functionality(self):
        """JavaScript should have filter functionality."""
        self.assertIn("applyFilter", self.js_content)
        self.assertIn("filter-input", self.js_content)
        self.assertIn("filter-exclude", self.js_content)

    def test_js_has_regex_support(self):
        """JavaScript should support regex filtering."""
        self.assertIn("RegExp", self.js_content)
        self.assertIn("regex.test", self.js_content)

    def test_js_has_error_handling(self):
        """JavaScript should handle invalid regex."""
        self.assertIn("try", self.js_content)
        self.assertIn("catch", self.js_content)
        self.assertIn("error", self.js_content)

    def test_js_has_status_update(self):
        """JavaScript should update filter status."""
        self.assertIn("filter-status", self.js_content)
        self.assertIn("textContent", self.js_content)


class TestHtmlTemplateJinja2(unittest.TestCase):
    """Test Jinja2 template file content."""

    @classmethod
    def setUpClass(cls):
        cls.template_content = (TEMPLATES_DIR / "html_page.jinja2").read_text()

    def test_template_has_html_structure(self):
        """Template should have proper HTML structure."""
        self.assertIn("<!DOCTYPE html>", self.template_content)
        self.assertIn("<html", self.template_content)
        self.assertIn("</html>", self.template_content)

    def test_template_has_jinja2_variables(self):
        """Template should use Jinja2 variables."""
        self.assertIn("{{ module_name }}", self.template_content)
        self.assertIn("{{ css }}", self.template_content)
        self.assertIn("{{ js }}", self.template_content)
        self.assertIn("{{ signals_html", self.template_content)
        self.assertIn("{{ params_html", self.template_content)

    def test_template_has_safe_filter(self):
        """Template should use safe filter for HTML content."""
        self.assertIn("| safe", self.template_content)

    def test_template_has_filter_panel_markup(self):
        """Template should contain filter panel markup."""
        self.assertIn("filter-panel", self.template_content)
        self.assertIn("filter-input", self.template_content)
        self.assertIn("Hide matching", self.template_content)

    def test_template_has_sections(self):
        """Template should have signals and parameters sections."""
        self.assertIn("Signals", self.template_content)
        self.assertIn("Parameters", self.template_content)


class TestHtmlRendererTemplateLoading(unittest.TestCase):
    """Test that renderer properly loads templates."""

    def setUp(self):
        self.renderer = HtmlTreeRenderer()

    def test_renderer_has_jinja_environment(self):
        """Renderer should have Jinja2 environment."""
        self.assertIsNotNone(self.renderer._env)

    def test_css_property_returns_content(self):
        """CSS property should return CSS content."""
        css = self.renderer.css
        self.assertIsInstance(css, str)
        self.assertGreater(len(css), 0)
        self.assertIn(":root", css)

    def test_js_property_returns_content(self):
        """JS property should return JavaScript content."""
        js = self.renderer.js
        self.assertIsInstance(js, str)
        self.assertGreater(len(js), 0)
        self.assertIn("addEventListener", js)

    def test_template_renders_without_error(self):
        """Jinja2 template should render without error."""
        result = self.renderer.render_full_page("test", "<div>signals</div>", "<div>params</div>")
        self.assertIsInstance(result, str)
        self.assertIn("test", result)


class TestHtmlRendererCaching(unittest.TestCase):
    """Test template caching behavior."""

    def test_css_is_cached(self):
        """CSS should be cached after first load."""
        renderer = HtmlTreeRenderer()
        self.assertIsNone(renderer._css)

        css1 = renderer.css
        self.assertIsNotNone(renderer._css)

        css2 = renderer.css
        self.assertIs(css1, css2)  # Same object reference

    def test_js_is_cached(self):
        """JavaScript should be cached after first load."""
        renderer = HtmlTreeRenderer()
        self.assertIsNone(renderer._js)

        js1 = renderer.js
        self.assertIsNotNone(renderer._js)

        js2 = renderer.js
        self.assertIs(js1, js2)  # Same object reference

    def test_multiple_renderers_independent_cache(self):
        """Each renderer instance should have its own cache."""
        renderer1 = HtmlTreeRenderer()
        renderer2 = HtmlTreeRenderer()

        _ = renderer1.css
        self.assertIsNotNone(renderer1._css)
        self.assertIsNone(renderer2._css)


if __name__ == '__main__':
    unittest.main()
