"""Renderer implementations for SystemVerilog port/parameter output.

This package contains various output format renderers:
- markdown: GitHub Flavoured Markdown tables
- csv: CSV with hierarchical columns for nested structs
- html: Interactive HTML tree with expand/collapse

All renderers are automatically registered via decorators.
"""

from .base import TableRenderer, renderer_registry
from .markdown import MarkdownTableRenderer
from .csv import CsvTableRenderer
from .html import HtmlTreeRenderer

__all__ = [
    "TableRenderer",
    "renderer_registry",
    "MarkdownTableRenderer",
    "CsvTableRenderer",
    "HtmlTreeRenderer",
]
