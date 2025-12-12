"""Top level package for the SystemVerilog parsing library.

This package exposes a small set of classes that can be used to
programmatically inspect SystemVerilog source files.  It is intended
for design-verification engineers who need to extract information
about modules, their parameters and ports, and the data types used by
those ports.

Key concepts:

* **Model classes** represent SystemVerilog constructs such as
  modules, ports, parameters and data types.  See :mod:`svlang.model`.
* **Backend** uses pyslang for parsing.  See :mod:`svlang.slang_backend`.
* **Strategy** defines how to load and process designs.  See :mod:`svlang.strategy`.
* **Renderer** provides pluggable output formats (Markdown, CSV).
  See :mod:`svlang.renderer`.
* **Registry** enables decorator-based plugin registration.
  See :mod:`svlang.registry`.

The design follows SOLID principles with decorator-based registries
for extensibility.
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

from .slang_backend import SlangBackend  # noqa: F401
from .registry import Registry
from .strategy import InterfaceStrategy, LRM2017Strategy, Genesis2Strategy, strategy_registry  # noqa: F401
from .renderer import TableRenderer, MarkdownTableRenderer, CsvTableRenderer, renderer_registry

__all__ = [
    "SlangBackend",
    "Registry",
    "InterfaceStrategy",
    "LRM2017Strategy",
    "Genesis2Strategy",
    "strategy_registry",
    "TableRenderer",
    "MarkdownTableRenderer",
    "CsvTableRenderer",
    "renderer_registry",
    "IDataType",
    "BasicType",
    "StructType",
    "UnionType",
    "Parameter",
    "Port",
    "Module",
]
