"""SystemVerilog parser implementation.

The :class:`SVParser` class provides a high level API for parsing
SystemVerilog source files.  It is intentionally focused on module
headers (ANSI style) and user defined ``struct``/``union`` types.  The
parser does not attempt to evaluate all parameter expressions or
perform full language elaboration.  Instead it produces a simple
semantic model consisting of :class:`svlang.model.Module` objects,
complete with their ports, parameters and referenced data types.

The parser is designed so that it can easily be extended.  If you need
additional capabilities (such as interface parsing, generate
constructs, etc.) you can subclass :class:`SVParser` and override
specific parsing methods without touching the rest of the code.

Example usage::

    from svlang import SVParser, MarkdownTableRenderer

    parser = SVParser()
    modules = parser.parse_file("my_design.sv")
    renderer = MarkdownTableRenderer()
    for mod in modules:
        print(f"# Module {mod.name}\n")
        print(renderer.render_signal_table(mod.ports))
        print(renderer.render_parameter_table(mod.parameters))

"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .model import (
    BasicType,
    IDataType,
    Module,
    Parameter,
    Port,
    StructField,
    StructType,
    UnionType,
)


class SVParser:
    """Parser for SystemVerilog modules, parameters and data types."""

    def __init__(self) -> None:
        # Mapping of type name to composite type definitions
        self._types: Dict[str, IDataType] = {}

    def parse_file(self, path: str) -> List[Module]:
        """Parse a SystemVerilog file.

        Args:
            path: File system path to the SV source.

        Returns:
            A list of :class:`svlang.model.Module` objects representing all
            modules found in the file.
        """
        with open(path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        return self.parse_text(text)

    def parse_text(self, text: str) -> List[Module]:
        """Parse SystemVerilog source from a string.

        Args:
            text: SystemVerilog source code.

        Returns:
            List of module objects.
        """
        # First extract composite type definitions
        self._types = self._extract_composite_types(text)
        # Then extract modules
        modules = self._extract_modules(text)
        return modules

    # ------------------------------------------------------------------
    # Composite type parsing

    def _extract_composite_types(self, text: str) -> Dict[str, IDataType]:
        """Find all ``typedef struct`` and ``typedef union`` definitions.

        The parser uses a simple scanning approach rather than regex
        balancing to reliably handle nested braces within struct bodies.

        Args:
            text: Entire source file text.

        Returns:
            A mapping of type names to :class:`IDataType` objects.
        """
        types: Dict[str, IDataType] = {}
        # Regex to find 'typedef struct' or 'typedef union'
        pattern = re.compile(r'\btypedef\s+(struct|union)\b', re.IGNORECASE)
        pos = 0
        while True:
            m = pattern.search(text, pos)
            if not m:
                break
            kind = m.group(1).lower()
            # Find opening brace
            brace_pos = text.find('{', m.end())
            if brace_pos == -1:
                break
            # Scan forward to find matching '}'
            depth = 1
            i = brace_pos + 1
            while i < len(text) and depth > 0:
                ch = text[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                i += 1
            body = text[brace_pos + 1 : i - 1]
            remainder = text[i:]
            # Extract type name following the '}'
            nm = re.match(r'\s*(\w+)', remainder)
            if nm:
                type_name = nm.group(1)
                fields = self._parse_composite_fields(body)
                if kind == 'struct':
                    types[type_name] = StructType(type_name, fields)
                else:
                    types[type_name] = UnionType(type_name, fields)
            # Advance position
            pos = i
        return types

    def _parse_composite_fields(self, body: str) -> List[StructField]:
        """Parse the contents of a struct/union definition into fields.

        Args:
            body: Text between the opening and closing braces of the
                struct/union body (excluding the braces).

        Returns:
            List of :class:`StructField` objects.
        """
        fields: List[StructField] = []
        # Remove comments to avoid splitting on semicolons inside
        body_no_comments = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
        body_no_comments = re.sub(r'//.*', '', body_no_comments)
        # Split by ';' to get individual declarations
        for decl in body_no_comments.split(';'):
            decl = decl.strip()
            if not decl:
                continue
            # Support declarations separated by commas
            # Keep track of type tokens from first part
            parts = [p.strip() for p in decl.split(',') if p.strip()]
            if not parts:
                continue
            # Determine common type spec from the first part
            type_part, first_name = self._split_type_and_name(parts[0])
            base_type = self._parse_data_type(type_part)
            # Add first field
            if first_name:
                fields.append(StructField(first_name, base_type))
            # Add subsequent fields sharing the same type
            for extra in parts[1:]:
                _, name = self._split_type_and_name(extra)
                if name:
                    fields.append(StructField(name, base_type))
        return fields

    def _split_type_and_name(self, decl: str) -> Tuple[str, Optional[str]]:
        """Split a declaration into type part and identifier.

        Example::

            'logic [7:0] data'  -> ('logic [7:0]', 'data')
            'my_struct_t s'     -> ('my_struct_t', 's')

        Args:
            decl: declaration string with type and name.

        Returns:
            A tuple of (type_part, name).  If no name can be
            determined the second element will be ``None``.
        """
        decl = decl.strip()
        # Remove any assignment
        assign_split = decl.split('=')[0].strip()
        tokens = assign_split.split()
        if not tokens:
            return (assign_split, None)
        name_token = tokens[-1]
        # If name token contains array dimensions (e.g. foo[3:0]) drop them
        name_match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', name_token)
        name = name_match.group(1) if name_match else None
        type_part = ' '.join(tokens[:-1])
        return (type_part, name)

    # ------------------------------------------------------------------
    # Module parsing

    def _extract_modules(self, text: str) -> List[Module]:
        """Extract module declarations from the source text.

        Only ANSI style module headers are recognised.  The parser
        finds occurrences of the ``module`` keyword, extracts the name,
        optional parameter list (``#( ... )``) and port list (``( ... )``)
        and constructs :class:`Module` objects accordingly.

        Args:
            text: Entire source file text.

        Returns:
            List of :class:`Module` objects.
        """
        modules: List[Module] = []
        pattern = re.compile(r'\bmodule\b', re.IGNORECASE)
        idx = 0
        while True:
            m = pattern.search(text, idx)
            if not m:
                break
            start = m.start()
            # Extract module name
            name_match = re.match(r'module\s+(\w+)', text[start:], re.IGNORECASE)
            if not name_match:
                idx = m.end()
                continue
            name = name_match.group(1)
            pos = start + name_match.end()
            # Skip whitespace
            while pos < len(text) and text[pos].isspace():
                pos += 1
            # Parse parameter list if present
            param_list_text = ''
            if pos < len(text) and text[pos] == '#':
                pos += 1
                # Skip whitespace
                while pos < len(text) and text[pos].isspace():
                    pos += 1
                if pos < len(text) and text[pos] == '(':  # begin parameter block
                    param_list_text, pos = self._extract_parenthesised(text, pos)
            # Skip whitespace before port list
            while pos < len(text) and text[pos].isspace():
                pos += 1
            # Parse port list
            port_list_text = ''
            if pos < len(text) and text[pos] == '(':  # begin port list
                port_list_text, pos = self._extract_parenthesised(text, pos)
            # Create module object
            parameters = self._parse_parameter_list(param_list_text)
            ports = self._parse_port_list(port_list_text)
            modules.append(Module(name=name, parameters=parameters, ports=ports))
            # Advance search index
            idx = pos
        return modules

    def _extract_parenthesised(self, text: str, start_idx: int) -> Tuple[str, int]:
        """Extract a parenthesised expression, handling nested parentheses.

        Args:
            text: Full text.
            start_idx: Index where the opening parenthesis '(' is found.

        Returns:
            A tuple (content, next_idx) where ``content`` is the text
            inside the parentheses (excluding the outer '(' and ')') and
            ``next_idx`` is the index of the character following the
            closing ')'.
        """
        assert text[start_idx] == '(', "Expected '(' at start_idx"
        depth = 1
        i = start_idx + 1
        start_content = i
        while i < len(text) and depth > 0:
            ch = text[i]
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            i += 1
        content = text[start_content:i - 1]
        return content, i

    # ------------------------------------------------------------------
    # Parameter/Port parsing

    def _parse_parameter_list(self, text: str) -> List[Parameter]:
        """Parse a parameter list.

        The input is the text inside a parameter list (excluding the
        outer parentheses).  Parameters are separated by commas at the
        top level.  Each parameter may be of the form ``parameter
        type name = default`` or ``localparam type name = default``.

        Args:
            text: The raw parameter list text.

        Returns:
            A list of :class:`Parameter` objects.
        """
        if not text.strip():
            return []
        params: List[Parameter] = []
        # Split on top-level commas
        items = self._split_top_level(text, ',')
        for item in items:
            item = item.strip()
            if not item:
                continue
            # Remove trailing parentheses or semicolons
            item = item.rstrip(',;')
            # Strip keyword parameter/localparam
            m = re.match(r'(parameter|localparam)\b', item)
            if m:
                item = item[m.end():].strip()
            # Identify default value
            if '=' in item:
                type_and_name, default = item.split('=', 1)
                default = default.strip()
            else:
                type_and_name = item
                default = None
            type_and_name = type_and_name.strip()
            # Split type and name
            type_part, name = self._split_type_and_name(type_and_name)
            if not name:
                continue
            data_type = self._parse_data_type(type_part)
            params.append(Parameter(name=name, data_type=data_type, default=default))
            # If this parameter declares a type alias (parameter type), update type registry
            # Recognise 'type' keyword in the type part.  Example: "parameter type data_t = payload_t"
            if type_part.strip().startswith('type'):
                # If a default is provided and refers to a known type, register alias
                if default:
                    default_name = default.strip()
                    # Remove any trailing semicolon or comma in default
                    default_name = re.sub(r'[;,]\s*$', '', default_name)
                    if default_name in self._types:
                        self._types[name] = self._types[default_name]
        return params

    def _parse_port_list(self, text: str) -> List[Port]:
        """Parse a module port list.

        The input is the text inside the port list (excluding the
        outer parentheses).  Ports are separated by commas at the top
        level.  Each port declaration may include direction, net type,
        sign, packed range and name.

        Args:
            text: Raw port list text.

        Returns:
            List of :class:`Port` objects.
        """
        ports: List[Port] = []
        if not text.strip():
            return ports
        items = self._split_top_level(text, ',')
        for item in items:
            # Trim whitespace and skip empty items
            item = item.strip()
            if not item:
                continue
            # Remove any trailing comma or semicolon remnants
            item = item.rstrip(',;')
            # Extract direction (must appear at start of remaining text)
            mdir = re.match(r'(input|output|inout)\b', item)
            if not mdir:
                # Non-ANSI port declaration not supported
                continue
            direction = mdir.group(1)
            remainder = item[mdir.end():].strip()
            # Split into type specification and name
            type_part, name = self._split_type_and_name(remainder)
            if not name:
                continue
            data_type = self._parse_data_type(type_part)
            ports.append(Port(name=name, direction=direction, data_type=data_type))
        return ports

    def _split_top_level(self, text: str, delimiter: str) -> List[str]:
        """Split a string by a delimiter at top level (not nested).

        This helper is used to split parameter and port lists by commas
        while respecting nested parentheses, brackets and braces.  Only
        delimiters encountered at depth zero are considered separators.

        Args:
            text: Text to split.
            delimiter: Delimiter string.

        Returns:
            List of substrings.
        """
        parts: List[str] = []
        current = []
        depth_paren = 0
        depth_bracket = 0
        depth_brace = 0
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '(':
                depth_paren += 1
            elif ch == ')':
                if depth_paren > 0:
                    depth_paren -= 1
            elif ch == '[':
                depth_bracket += 1
            elif ch == ']':
                if depth_bracket > 0:
                    depth_bracket -= 1
            elif ch == '{':
                depth_brace += 1
            elif ch == '}':
                if depth_brace > 0:
                    depth_brace -= 1
            # Check delimiter
            if ch == delimiter and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(ch)
            i += 1
        if current:
            parts.append(''.join(current))
        return parts

    def _parse_data_type(self, type_part: str) -> IDataType:
        """Parse a textual data type specification into a :class:`IDataType`.

        This method recognises basic SystemVerilog net types (e.g.
        ``logic``, ``wire``, ``bit``, ``reg``, etc.), optional ``signed``
        modifiers and packed ranges.  If a user defined type is found in
        ``self._types`` it is returned directly.  Otherwise a
        :class:`BasicType` is constructed.

        In addition to handling whitespace-separated tokens, this
        implementation also detects packed ranges attached to a base
        type without an intervening space (e.g. ``logic[31:0]``) and
        splits them into separate base type and range tokens.

        Args:
            type_part: The textual specification of the type (without
                the variable name).

        Returns:
            An :class:`IDataType` instance representing the parsed type.
        """
        type_part = type_part.strip()
        if not type_part:
            # Default type is logic
            return BasicType(name='logic')
        tokens = type_part.split()
        nettype = None
        signed = False
        bit_range = None
        type_name = None
        for tok in tokens:
            # Capture packed range tokens like [7:0] or [WIDTH-1:0]
            if tok.startswith('[') and tok.endswith(']'):
                if bit_range is None:
                    bit_range = tok
                else:
                    bit_range += ' ' + tok
            elif tok.lower() == 'signed':
                signed = True
            elif tok.lower() in {
                'logic', 'wire', 'reg', 'bit', 'var', 'integer', 'int', 'byte',
                'shortint', 'longint', 'time', 'real', 'realtime', 'shortreal'
            }:
                nettype = tok
            else:
                type_name = tok
        # If user defined type exists, use it
        if type_name and type_name in self._types:
            return self._types[type_name]
        # Otherwise derive basic type
        name = type_name if type_name else (nettype if nettype else 'logic')
        return BasicType(name=name, bit_range=bit_range, signed=signed)
