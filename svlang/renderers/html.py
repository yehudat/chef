"""HTML tree renderer.

Renders ports as an interactive HTML tree with expand/collapse
functionality for nested struct types.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader

from ..model import Parameter, Port, StructType, UnionType, IDataType
from .base import TableRenderer, renderer_registry

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


@renderer_registry.register("html")
class HtmlTreeRenderer(TableRenderer):
    """Render ports as an interactive HTML tree with expand/collapse.

    Generates a static HTML file with embedded CSS and JavaScript.
    Complex types (structs/unions) are expandable nodes showing their
    internal structure recursively.
    """

    def __init__(self):
        """Initialize renderer with Jinja2 environment."""
        self._env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=False,
        )
        self._css = None
        self._js = None

    @property
    def css(self) -> str:
        """Load and cache CSS from template file."""
        if self._css is None:
            css_path = TEMPLATES_DIR / "html_styles.css"
            self._css = css_path.read_text()
        return self._css

    @property
    def js(self) -> str:
        """Load and cache JavaScript from template file."""
        if self._js is None:
            js_path = TEMPLATES_DIR / "html_scripts.js"
            self._js = js_path.read_text()
        return self._js

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    def _render_struct_fields(self, data_type: IDataType) -> str:
        """Render struct/union fields as nested HTML list items."""
        if not isinstance(data_type, (StructType, UnionType)):
            return ""

        items = []
        for field in data_type.fields:
            field_name = self._escape_html(field.name)
            field_type = self._escape_html(str(field.data_type))
            is_complex = isinstance(field.data_type, (StructType, UnionType))

            expandable_class = " expandable" if is_complex else ""
            expand_icon = "▶" if is_complex else ""

            item = f'''<div class="field-item{expandable_class}">
                <span class="expand-icon">{expand_icon}</span>
                <span class="field-type">{field_type}</span>
                <span class="field-name">{field_name}</span>
            </div>'''

            if is_complex:
                nested = self._render_struct_fields(field.data_type)
                item += f'<ul class="nested-fields">{nested}</ul>'

            items.append(f"<li>{item}</li>")

        return "\n".join(items)

    def render_signal_table(self, signals: Iterable[Port]) -> str:
        """Render ports as an interactive HTML tree."""
        signals_list = list(signals)

        items = []
        for sig in signals_list:
            name = self._escape_html(sig.name)
            sig_type = self._escape_html(str(sig.data_type))
            direction = self._escape_html(sig.direction)

            is_complex = isinstance(sig.data_type, (StructType, UnionType))
            has_children_class = " has-children" if is_complex else ""
            expandable_class = " expandable" if is_complex else ""
            expand_icon = "▶" if is_complex else ""

            # Determine direction class
            dir_class = "dir-input"
            if "output" in direction.lower():
                dir_class = "dir-output"
            elif "inout" in direction.lower():
                dir_class = "dir-inout"

            item = f'''<li class="tree-item{has_children_class}">
                <div class="tree-header{expandable_class}">
                    <span class="expand-icon">{expand_icon}</span>
                    <span class="signal-name">{name}</span>
                    <span class="signal-type">{sig_type}</span>
                    <span class="signal-direction {dir_class}">{direction}</span>
                </div>'''

            if is_complex:
                nested = self._render_struct_fields(sig.data_type)
                item += f'<ul class="tree-children">{nested}</ul>'

            item += "</li>"
            items.append(item)

        tree_html = "\n".join(items)
        return f'<ul class="tree">\n{tree_html}\n</ul>'

    def render_parameter_table(self, params: Iterable[Parameter]) -> str:
        """Render parameters as an HTML table."""
        params_list = list(params)

        if not params_list:
            return '<p class="no-params">No parameters</p>'

        rows = []
        for p in params_list:
            name = self._escape_html(p.name)
            p_type = self._escape_html(str(p.data_type))
            default = self._escape_html(p.default or "—")
            desc = self._escape_html(p.description or "")

            rows.append(f'''<tr>
                <td class="param-name">{name}</td>
                <td class="param-type">{p_type}</td>
                <td class="param-default">{default}</td>
                <td>{desc}</td>
            </tr>''')

        rows_html = "\n".join(rows)
        return f'''<table class="param-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Default</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>'''

    def render_full_page(self, module_name: str, signals_html: str, params_html: str) -> str:
        """Render a complete HTML page with signals and parameters."""
        template = self._env.get_template("html_page.jinja2")
        return template.render(
            module_name=self._escape_html(module_name),
            css=self.css,
            js=self.js,
            signals_html=signals_html,
            params_html=params_html,
        )
