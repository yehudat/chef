"""HTML tree renderer.

Renders ports as an interactive HTML tree with expand/collapse
functionality for nested struct types.
"""

from __future__ import annotations

from typing import Iterable, List

from ..model import Parameter, Port, StructType, UnionType, IDataType
from .base import TableRenderer, renderer_registry


@renderer_registry.register("html")
class HtmlTreeRenderer(TableRenderer):
    """Render ports as an interactive HTML tree with expand/collapse.

    Generates a static HTML file with embedded CSS and JavaScript.
    Complex types (structs/unions) are expandable nodes showing their
    internal structure recursively.
    """

    CSS = """
    :root {
        --bg-primary: #fafbfc;
        --bg-secondary: #f0f4f8;
        --bg-card: #ffffff;
        --text-primary: #2d3748;
        --text-secondary: #718096;
        --accent-blue: #a3bffa;
        --accent-green: #9ae6b4;
        --accent-purple: #d6bcfa;
        --accent-pink: #fbb6ce;
        --accent-yellow: #faf089;
        --accent-orange: #fbd38d;
        --border-color: #e2e8f0;
        --shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: var(--bg-primary);
        color: var(--text-primary);
        line-height: 1.6;
        padding: 2rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 {
        font-size: 1.75rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        color: var(--text-primary);
    }
    h2 {
        font-size: 1.25rem;
        font-weight: 600;
        margin: 2rem 0 1rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .tree { list-style: none; }
    .tree-item {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        margin-bottom: 0.5rem;
        box-shadow: var(--shadow);
        overflow: hidden;
    }
    .tree-header {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        cursor: default;
        gap: 0.75rem;
    }
    .tree-header.expandable { cursor: pointer; }
    .tree-header.expandable:hover { background: var(--bg-secondary); }
    .expand-icon {
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        color: var(--text-secondary);
        transition: transform 0.2s;
    }
    .tree-item.expanded > .tree-header .expand-icon { transform: rotate(90deg); }
    .tree-item:not(.has-children) .expand-icon { visibility: hidden; }
    .signal-name {
        font-weight: 600;
        color: var(--text-primary);
        min-width: 180px;
    }
    .signal-type {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.875rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: var(--accent-blue);
        color: var(--text-primary);
    }
    .signal-direction {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        text-transform: uppercase;
        font-weight: 600;
    }
    .dir-input { background: var(--accent-green); }
    .dir-output { background: var(--accent-purple); }
    .dir-inout { background: var(--accent-yellow); }
    .tree-children {
        display: none;
        list-style: none;
        padding: 0 0 0.5rem 2.5rem;
        background: var(--bg-secondary);
        border-top: 1px solid var(--border-color);
    }
    .tree-item.expanded > .tree-children { display: block; }
    .field-item {
        display: flex;
        align-items: center;
        padding: 0.5rem 0.75rem;
        margin: 0.25rem 0;
        background: var(--bg-card);
        border-radius: 6px;
        gap: 0.5rem;
        cursor: default;
    }
    .field-item.expandable { cursor: pointer; }
    .field-item.expandable:hover { background: var(--bg-primary); }
    .field-name {
        font-weight: 500;
        color: var(--text-primary);
    }
    .field-type {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        background: var(--accent-orange);
    }
    .nested-fields {
        display: none;
        list-style: none;
        padding-left: 1.5rem;
        margin-top: 0.25rem;
    }
    .field-item.expanded + .nested-fields { display: block; }
    .param-table {
        width: 100%;
        border-collapse: collapse;
        background: var(--bg-card);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: var(--shadow);
    }
    .param-table th {
        background: var(--bg-secondary);
        padding: 0.75rem 1rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.875rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .param-table td {
        padding: 0.75rem 1rem;
        border-top: 1px solid var(--border-color);
    }
    .param-table tr:hover { background: var(--bg-secondary); }
    .param-name { font-weight: 600; }
    .param-type {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.875rem;
    }
    .param-default {
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.875rem;
        color: var(--text-secondary);
    }
    """

    JS = """
    document.addEventListener('DOMContentLoaded', function() {
        // Handle tree item expansion
        document.querySelectorAll('.tree-header.expandable').forEach(function(header) {
            header.addEventListener('click', function() {
                this.parentElement.classList.toggle('expanded');
            });
        });
        // Handle nested field expansion
        document.querySelectorAll('.field-item.expandable').forEach(function(field) {
            field.addEventListener('click', function(e) {
                e.stopPropagation();
                this.classList.toggle('expanded');
            });
        });
    });
    """

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
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(module_name)} - Interface</title>
    <style>{self.CSS}</style>
</head>
<body>
    <div class="container">
        <h1>{self._escape_html(module_name)}</h1>
        <h2>Signals</h2>
        {signals_html}
        <h2>Parameters</h2>
        {params_html}
    </div>
    <script>{self.JS}</script>
</body>
</html>'''
