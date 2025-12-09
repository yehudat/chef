"""Slang‑backed parsing engine.

This module defines a :class:`SlangBackend` class that wraps the
``pyslang`` Python bindings to compile and elaborate SystemVerilog
source files.  Unlike the lightweight regex parser provided by
``svlang.parser``, this backend invokes a real SystemVerilog
front‑end (the `slang` compiler) to build an abstract syntax tree
(AST) and semantic model.  The resulting design includes resolved
types, port directions and widths, and parameter values where
possible.

Because this backend depends on compiled extensions, it will raise an
exception if the `pyslang` package cannot be imported.  There is
intentionally **no** fallback to the handwritten parser in strict
mode.  Consumers who select the slang engine must ensure that
``pyslang`` and its build dependencies are installed in their
environment.  See the project documentation for details.

The backend exposes two primary methods:

* :meth:`load_design` – compile one or more SystemVerilog source
  files.  Any compilation errors will raise a :class:`RuntimeError`.
* :meth:`get_modules` – retrieve a list of :class:`svlang.model.Module`
  objects representing the modules in the design.

Internally this class converts slang's AST nodes into the simple
data model defined in :mod:`svlang.model`.  Composite types (structs
and unions) are recursively expanded into :class:`StructType` and
their fields.  Primitive bit‑vector types capture their packed range
and signedness.  Other types are represented by their string name.

This implementation handles a subset of the slang type system; you
may extend :meth:`_convert_type` to add support for interfaces, enums
and other kinds as needed.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .model import (
    BasicType,
    StructField,
    StructType,
    UnionType,
    Parameter,
    Port,
    Module,
)

# Attempt to import the pyslang package.  If unavailable we set
# imported symbols to None.  Strict option C means there is no
# fallback parser; calling :meth:`load_design` will raise an error
# when pyslang isn't installed.
try:
    import pyslang  # type: ignore[import]
    from pyslang import (
        SyntaxTree,
        SourceManager,
        Compilation,
        DiagnosticSeverity,
        SymbolKind,
    )  # type: ignore[import]
except Exception:
    pyslang = None  # type: ignore
    SyntaxTree = SourceManager = Compilation = DiagnosticSeverity = SymbolKind = None  # type: ignore


class SlangBackend:
    """Compile SystemVerilog sources using the slang compiler.

    When instantiated, this class records include directories and
    preprocessor defines, which will be passed to the slang
    compilation if possible.  The :meth:`load_design` method must be
    called before :meth:`get_modules` will return anything useful.

    Parameters are not elaborated beyond capturing their declared
    type and any default value as a string.  Port types are
    converted into instances of :class:`svlang.model.BasicType`,
    :class:`StructType` or :class:`UnionType` as appropriate.
    """

    def __init__(self, include_dirs: Optional[List[str]] = None, defines: Optional[List[str]] = None) -> None:
        self.include_dirs = include_dirs or []
        self.defines = defines or []
        self._modules: List[Module] = []

    def load_design(self, files: List[str]) -> None:
        """Compile the given SystemVerilog source files.

        Args:
            files: A list of file system paths pointing to SV source files.

        Raises:
            ImportError: If the ``pyslang`` package is not available.
            RuntimeError: If the slang compiler reports any errors.
        """
        if pyslang is None:
            raise ImportError(
                "pyslang is required for the SlangBackend but is not installed. "
                "Install it via `pip install pyslang` and ensure build dependencies such as "
                "cmake and a C++ compiler are available."
            )

        sm = SourceManager()
        trees = []
        for path in files:
            tree = SyntaxTree.fromFile(path, sm)
            trees.append(tree)

        comp = Compilation()
        for tree in trees:
            comp.addSyntaxTree(tree)

        diags = comp.getAllDiagnostics()
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        if errors:
            messages = []
            for diag in errors:
                try:
                    messages.append(str(diag))
                except Exception:
                    messages.append(repr(diag))
            raise RuntimeError("Slang compilation failed: " + "; ".join(messages))

        self._modules = self._convert_modules(comp)

    def get_modules(self) -> List[Module]:
        """Return a list of modules extracted from the most recent design."""
        return list(self._modules)

    # ------------------------------------------------------------------
    # Internal conversion helpers

    def _convert_modules(self, comp: Compilation) -> List[Module]:  # type: ignore[override]
        modules: List[Module] = []
        root = comp.getRoot()
        for member in getattr(root, "members", []):
            try:
                kind = member.kind  # type: ignore[attr-defined]
            except Exception:
                continue
            if SymbolKind is not None and kind == SymbolKind.Module:  # type: ignore[comparison-overlap]
                modules.append(self._convert_module(member))
        return modules

    def _convert_module(self, mod_sym) -> Module:
        name: str = getattr(mod_sym, "name", "unknown")
        parameters: List[Parameter] = []
        for param in getattr(mod_sym, "parameters", []):
            parameters.append(self._convert_parameter(param))
        ports: List[Port] = []
        for port in getattr(mod_sym, "ports", []):
            ports.append(self._convert_port(port))
        return Module(name=name, parameters=parameters, ports=ports)

    def _convert_parameter(self, param_sym) -> Parameter:
        name: str = getattr(param_sym, "name", "")
        data_type = self._convert_type(getattr(param_sym, "type", None))
        default: Optional[str] = None
        if hasattr(param_sym, "getValue"):
            try:
                default_val = param_sym.getValue()
                default = str(default_val)
            except Exception:
                default = None
        elif hasattr(param_sym, "value"):
            try:
                default = str(param_sym.value)
            except Exception:
                default = None
        return Parameter(name=name, data_type=data_type, default=default)

    def _convert_port(self, port_sym) -> Port:
        name: str = getattr(port_sym, "name", "")
        dir_obj = getattr(port_sym, "direction", None)
        direction = ""
        if dir_obj is not None:
            direction = getattr(dir_obj, "name", None) or str(dir_obj)
        direction = direction.lower() if isinstance(direction, str) else str(direction)
        data_type = self._convert_type(getattr(port_sym, "type", None))
        return Port(name=name, direction=direction, data_type=data_type)

    def _convert_type(self, type_sym) -> BasicType | StructType | UnionType:
        """Convert a pyslang Type into a svlang.model type.

        For bit‑vector types we capture the signedness and packed range.  For
        structs and unions we recursively convert their members.  All
        other types are represented by their name and any simple attributes
        we can glean from the slang API.  Unsupported or unrecognised
        types are returned as a :class:`BasicType` with the best
        available name.
        """
        if type_sym is None:
            return BasicType(name="logic")

        try:
            is_signed = getattr(type_sym, "isSigned", lambda: False)()
            width_range = None
            if hasattr(type_sym, "getBitVectorRange"):
                try:
                    rng = type_sym.getBitVectorRange()
                    if rng is not None:
                        width_range = f"[{rng[0]}:{rng[1]}]"
                except Exception:
                    width_range = None
            type_name = getattr(type_sym, "name", None) or str(type_sym)
            if hasattr(type_sym, "isStruct") and type_sym.isStruct():
                fields: List[StructField] = []
                for member in getattr(type_sym, "members", []):
                    field_name = getattr(member, "name", "")
                    field_type = self._convert_type(getattr(member, "type", None))
                    fields.append(StructField(field_name, field_type))
                return StructType(type_name, fields)
            if hasattr(type_sym, "isUnion") and type_sym.isUnion():
                fields = []
                for member in getattr(type_sym, "members", []):
                    field_name = getattr(member, "name", "")
                    field_type = self._convert_type(getattr(member, "type", None))
                    fields.append(StructField(field_name, field_type))
                return UnionType(type_name, fields)
            return BasicType(name=type_name, bit_range=width_range, signed=is_signed)
        except Exception:
            return BasicType(name=str(type_sym))