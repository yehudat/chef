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
