"""Data model for SystemVerilog parsing.

This module defines a hierarchy of classes to represent the salient
constructs extracted from SystemVerilog source files.  The classes are
designed with clear separation of concerns and a small surface area to
facilitate unit testing and future extension.  Each class is
responsible for representing a single concept and exposes minimal
behaviour.

Following the SOLID principles, the data model leverages
abstractions (via the :class:`IDataType` interface) so that the rest
of the code does not need to know which specific concrete type it is
dealing with.  For example, a port simply has a data type; it does
not care whether that type is a struct, a union or a simple scalar.

At the bottom of the hierarchy are the various concrete data type
classes, each of which knows how to compute its own width and how to
expose any nested fields (recursively).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Iterable, Tuple, Iterator


class IDataType(ABC):
    """Abstract base class representing a SystemVerilog data type.

    Concrete subclasses must implement a width calculation and a method to
    iterate over the (possibly nested) fields contained by this type.
    """

    @abstractmethod
    def width(self) -> Optional[int]:
        """Return the bit width of this data type, or ``None`` if the width
        cannot be determined.  A width of ``None`` may indicate a
        composite type (struct/union) or a scalar whose width is
        architecture dependent (e.g. integer).
        """

    @abstractmethod
    def iter_fields(self, prefix: str = "") -> Iterable[Tuple[str, "IDataType"]]:
        """Iterate over the leaf fields contained in this type.

        For simple scalar types this yields a single entry consisting of
        the prefix and the type itself.  For composite types this will
        recursively iterate through all contained fields, yielding
        fully-qualified names (``prefix.field1.field2``) along with the
        corresponding leaf type.  Clients that only care about the top
        level type can simply ignore this method.
        """


@dataclass
class BasicType(IDataType):
    """A simple scalar data type.

    Examples include ``logic``, ``bit``, ``wire`` and any user defined
    type that does not contain nested fields.  The optional
    ``bit_range`` string holds the text of the packed range (e.g.
    ``[7:0]``).  If provided and both ends of the range can be
    converted to integers the width is computed as ``abs(msb-lsb)+1``.
    Otherwise ``width()`` returns ``None``.
    """

    name: str
    bit_range: Optional[str] = None
    signed: bool = False

    def width(self) -> Optional[int]:
        if self.bit_range:
            # Attempt to parse simple numeric ranges of the form [msb:lsb]
            m = re.match(r"\[(?P<msb>-?\d+)\s*:\s*(?P<lsb>-?\d+)\]", self.bit_range)
            if m:
                msb = int(m.group('msb'))
                lsb = int(m.group('lsb'))
                return abs(msb - lsb) + 1
        # For built-in integer types we cannot reliably determine width
        if self.name.lower() in {"integer", "int", "time", "real", "realtime"}:
            return None
        # Default scalar width of 1 bit
        return 1

    def iter_fields(self, prefix: str = "") -> Iterable[Tuple[str, IDataType]]:
        yield (prefix, self)

    def __str__(self) -> str:
        parts = [self.name]
        if self.signed:
            parts.append("signed")
        if self.bit_range:
            parts.append(self.bit_range)
        return " ".join(parts)


@dataclass
class StructField:
    """Represents a field within a struct or union."""

    name: str
    data_type: IDataType

    def width(self) -> Optional[int]:
        return self.data_type.width()

    def __str__(self) -> str:
        return f"{self.data_type} {self.name}"


class CompositeType(IDataType, ABC):
    """Base class for composite types (structs and unions)."""

    def __init__(self, name: str, fields: List[StructField]):
        self.name = name
        self.fields = fields

    def iter_fields(self, prefix: str = "") -> Iterable[Tuple[str, IDataType]]:
        for field in self.fields:
            new_prefix = f"{prefix}.{field.name}" if prefix else field.name
            for path, dtype in field.data_type.iter_fields(prefix=new_prefix):
                yield (path, dtype)

    def __str__(self) -> str:
        return self.name


class StructType(CompositeType):
    """Represents a user defined ``struct`` type."""

    def width(self) -> Optional[int]:
        # Sum widths of all fields; if any field has unknown width, return None
        total = 0
        for field in self.fields:
            w = field.width()
            if w is None:
                return None
            total += w
        return total


class UnionType(CompositeType):
    """Represents a user defined ``union`` type."""

    def width(self) -> Optional[int]:
        # Width of a union is the maximum of its field widths
        max_width: Optional[int] = 0
        for field in self.fields:
            w = field.width()
            if w is None:
                return None
            max_width = max(max_width, w)
        return max_width


@dataclass
class Parameter:
    """Represents a module parameter (generic)."""

    name: str
    data_type: IDataType
    default: Optional[str] = None
    description: Optional[str] = None

    def type_name(self) -> str:
        return str(self.data_type)

    def __str__(self) -> str:
        return f"parameter {self.type_name()} {self.name} = {self.default}"


@dataclass
class Port:
    """Represents a module port."""

    name: str
    direction: str
    data_type: IDataType
    reset_value: Optional[str] = None
    default_value: Optional[str] = None
    clk_domain: Optional[str] = None
    description: Optional[str] = None

    def type_name(self) -> str:
        return str(self.data_type)

    def width(self) -> Optional[int]:
        return self.data_type.width()

    def __str__(self) -> str:
        return f"{self.direction} {self.type_name()} {self.name}"


@dataclass
class Module:
    """Represents a SystemVerilog module with parameters and ports."""

    name: str
    parameters: List[Parameter] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)
    description: Optional[str] = None

    def get_port(self, name: str) -> Optional[Port]:
        for p in self.ports:
            if p.name == name:
                return p
        return None

    def get_parameter(self, name: str) -> Optional[Parameter]:
        for g in self.parameters:
            if g.name == name:
                return g
        return None

    def __str__(self) -> str:
        return f"module {self.name}"
