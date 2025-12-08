"""Top level package for the SystemVerilog parsing library.

This package exposes a small set of classes that can be used to
programmatically inspect SystemVerilog source files.  It is intended
for design‐verification engineers who need to extract information
about modules, their parameters and ports, and the data types used by
those ports.  The parser is intentionally lightweight and does not
attempt to implement the full SystemVerilog language; rather it
focuses on the ANSI style module headers, user defined struct/union
types and simple parameter declarations.

Key concepts:

* **Model classes** represent SystemVerilog constructs such as
  modules, ports, parameters and data types.  These are defined in
  :mod:`svlang.model`.
* **Parser** reads SystemVerilog text and produces model objects.  See
  :mod:`svlang.parser`.
* **Renderer** provides pluggable output formats (e.g. Markdown,
  CSV).  See :mod:`svlang.renderer`.

The design follows the SOLID principles: responsibilities are kept
focused, high level modules depend on abstractions instead of
concrete implementations, and new output formats can be added by
extending :class:`svlang.renderer.TableRenderer` without modifying
existing code.
"""

from .model import (
    IDataType,
    BasicType,
    StructType,
    UnionType,
    Parameter,
    Port,
    Module,
)

from .parser import SVParser
from .genesis2 import Genesis2Parser
from .renderer import TableRenderer, MarkdownTableRenderer

__all__ = [
    "SVParser",
    "Genesis2Parser",
    "TableRenderer",
    "MarkdownTableRenderer",
    "IDataType",
    "BasicType",
    "StructType",
    "UnionType",
    "Parameter",
    "Port",
    "Module",
]
