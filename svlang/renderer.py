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

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from .model import Parameter, Port, StructType, UnionType


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
