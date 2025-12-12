"""Rendering utilities for SystemVerilog models.

This module defines a simple table rendering interface and concrete
implementations for Markdown output.  The renderer abstracts away
formatting details and makes it easy to add additional output formats
without modifying the core parser or model classes (Open/Closed
principle).  For example, a CSV renderer could inherit from
:class:`TableRenderer` and override the rendering methods to output
comma-separated values.
"""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Tuple

from .model import Parameter, Port, StructType, UnionType, IDataType
from .registry import Registry

# Registry for renderer implementations
renderer_registry = Registry("renderer")


class TableRenderer(ABC):
    """Abstract base class for rendering tables of parameters and ports."""

    @abstractmethod
    def render_signal_table(self, signals: Iterable[Port]) -> str:
        """Render a table of port signals.

        Args:
            signals: Iterable of :class:`Port` objects.

        Returns:
            A string containing the formatted table.
        """
        raise NotImplementedError

    @abstractmethod
    def render_parameter_table(self, params: Iterable[Parameter]) -> str:
        """Render a table of module parameters.

        Args:
            params: Iterable of :class:`Parameter` objects.

        Returns:
            A string containing the formatted table.
        """
        raise NotImplementedError


@renderer_registry.register("markdown")
class MarkdownTableRenderer(TableRenderer):
    """Render tables in GitHub Flavoured Markdown format."""

    def _format_struct_fields(self, data_type, indent: int = 0) -> str:
        """Format struct/union fields for display in the Description column.

        Recursively formats nested structs with 4-space indentation per level.
        Returns fields formatted with <br/> separators for vertical display.
        """
        if not isinstance(data_type, (StructType, UnionType)):
            return ""

        field_strs = []
        indent_str = "&nbsp;" * (indent * 4)  # 4 spaces per indent level
        for field in data_type.fields:
            field_type_str = str(field.data_type)
            field_strs.append(f"{indent_str}{field_type_str} {field.name}")
            # Recursively format nested structs/unions
            if isinstance(field.data_type, (StructType, UnionType)):
                nested = self._format_struct_fields(field.data_type, indent + 1)
                if nested:
                    field_strs.append(nested)

        return "<br/>".join(field_strs)

    def render_signal_table(self, signals: Iterable[Port]) -> str:
        headers = [
            "Signal Name",
            "Type",
            "Direction",
            "Reset Value",
            "Default Value",
            "clk Domain",
            "Description",
        ]
        # Header row with alignment specifier
        header_line = "| " + " | ".join(headers) + " |"
        align_line = "|" + "|".join([":" + "-" * (len(h) + 1) for h in headers]) + "|"
        rows: List[str] = [header_line, align_line]
        for sig in signals:
            width_str = str(sig.data_type)
            # Build description: include struct fields if applicable
            desc_parts = []
            if sig.description:
                desc_parts.append(sig.description)
            struct_fields = self._format_struct_fields(sig.data_type)
            if struct_fields:
                desc_parts.append(struct_fields)
            desc = "<br/>".join(desc_parts) if desc_parts else ""

            row = "| {name} | {width} | {dir} | {rst} | {default} | {clk} | {desc} |".format(
                name=sig.name,
                width=width_str,
                dir=sig.direction,
                rst=sig.reset_value or "",
                default=sig.default_value or "",
                clk=sig.clk_domain or "",
                desc=desc,
            )
            rows.append(row)
        return "\n".join(rows)

    def render_parameter_table(self, params: Iterable[Parameter]) -> str:
        headers = [
            "Generic Name",
            "Type",
            "Range of Values",
            "Default Value",
            "Description",
        ]
        header_line = "| " + " | ".join(headers) + " |"
        align_line = "|" + "|".join([":" + "-" * (len(h) + 1) for h in headers]) + "|"
        rows: List[str] = [header_line, align_line]
        for p in params:
            row = "| {name} | {typ} | {range} | {default} | {desc} |".format(
                name=p.name,
                typ=str(p.data_type),
                range="",
                default=p.default or "",
                desc=p.description or "",
            )
            rows.append(row)
        return "\n".join(rows)


@renderer_registry.register("csv")
class CsvTableRenderer(TableRenderer):
    """Render tables in CSV format with hierarchical columns for nested structs.

    Instead of indentation, nested struct fields are displayed in separate
    columns. Each nesting level gets its own column, with empty cells in
    preceding columns to visually represent the hierarchy.

    Example output for a port with nested struct:
        Signal Name,Direction,Reset Value,Default Value,clk Domain,Type Level 1,Type Level 2,Type Level 3
        out_stream,output,,,,outer_stream_s,,
        ,,,,,,inner_trans_s trans,
        ,,,,,,,logic [63:0] data
    """

    def __init__(self, max_depth: int = 20) -> None:
        """Initialize the CSV renderer.

        Args:
            max_depth: Maximum nesting depth for struct hierarchy columns.
        """
        self.max_depth = max_depth

    def _get_max_struct_depth(self, data_type: IDataType, current_depth: int = 1) -> int:
        """Calculate the maximum nesting depth of a data type."""
        if not isinstance(data_type, (StructType, UnionType)):
            return current_depth

        max_child_depth = current_depth
        for field in data_type.fields:
            child_depth = self._get_max_struct_depth(field.data_type, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        return max_child_depth

    def _flatten_struct_fields(
        self, data_type: IDataType, level: int = 0
    ) -> List[Tuple[int, str]]:
        """Flatten struct fields into (level, field_string) tuples.

        Args:
            data_type: The data type to flatten.
            level: Current nesting level (0 = top level).

        Returns:
            List of (level, field_string) tuples for each field.
        """
        if not isinstance(data_type, (StructType, UnionType)):
            return []

        result: List[Tuple[int, str]] = []
        for field in data_type.fields:
            field_str = f"{field.data_type} {field.name}"
            result.append((level, field_str))
            # Recursively add nested fields
            if isinstance(field.data_type, (StructType, UnionType)):
                result.extend(self._flatten_struct_fields(field.data_type, level + 1))
        return result

    def render_signal_table(self, signals: Iterable[Port]) -> str:
        """Render a table of port signals in CSV format.

        Struct fields are expanded into hierarchical columns where each
        nesting level occupies a separate column.
        """
        signals_list = list(signals)

        # Calculate max depth needed across all signals
        max_depth = 1
        for sig in signals_list:
            depth = self._get_max_struct_depth(sig.data_type)
            max_depth = max(max_depth, depth)

        # Cap at configured maximum
        max_depth = min(max_depth, self.max_depth)

        # Build headers
        base_headers = [
            "Signal Name",
            "Direction",
            "Reset Value",
            "Default Value",
            "clk Domain",
        ]
        type_headers = [f"Type Level {i + 1}" for i in range(max_depth)]
        headers = base_headers + type_headers + ["Description"]

        # Build rows
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for sig in signals_list:
            # Base row with signal info
            base_row = [
                sig.name,
                sig.direction,
                sig.reset_value or "",
                sig.default_value or "",
                sig.clk_domain or "",
            ]

            # Type columns - first level is the port's type
            type_cols = [""] * max_depth
            type_cols[0] = str(sig.data_type)

            row = base_row + type_cols + [sig.description or ""]
            writer.writerow(row)

            # If it's a struct/union, add rows for nested fields
            if isinstance(sig.data_type, (StructType, UnionType)):
                nested_fields = self._flatten_struct_fields(sig.data_type, level=1)
                for level, field_str in nested_fields:
                    # Empty base columns for nested rows
                    nested_base = [""] * len(base_headers)
                    # Type columns with field at appropriate level
                    nested_type_cols = [""] * max_depth
                    if level < max_depth:
                        nested_type_cols[level] = field_str
                    nested_row = nested_base + nested_type_cols + [""]
                    writer.writerow(nested_row)

        return output.getvalue().rstrip("\r\n")

    def render_parameter_table(self, params: Iterable[Parameter]) -> str:
        """Render a table of module parameters in CSV format."""
        headers = [
            "Generic Name",
            "Type",
            "Range of Values",
            "Default Value",
            "Description",
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for p in params:
            row = [
                p.name,
                str(p.data_type),
                "",  # Range of Values
                p.default or "",
                p.description or "",
            ]
            writer.writerow(row)

        return output.getvalue().rstrip("\r\n")


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
