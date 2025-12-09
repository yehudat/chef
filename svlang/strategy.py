"""Interpretation strategies for SystemVerilog designs.

This module defines a small hierarchy of strategy classes that
encapsulate post‑processing of modules returned by a parsing
back‑end.  The default strategy, :class:`LRM2017Strategy`, simply
returns the modules exactly as produced by the back‑end.  A second
strategy, :class:`Genesis2Strategy`, exists as a hook for handling
Genesis2‑generated RTL; it currently performs no additional
processing but can be extended to group flattened interface ports or
interpret debug annotations.

All strategies rely on :class:`svlang.slang_backend.SlangBackend` to
obtain the raw modules.  Because this back‑end depends on the
presence of the `pyslang` package, callers must ensure it is
installed or catch the :class:`ImportError` raised by
:meth:`SlangBackend.load_design`.
"""

from __future__ import annotations

from typing import Iterable, List

from .model import Module
from .slang_backend import SlangBackend


class InterfaceStrategy:
    """Abstract base class for design interpretation strategies.

    A strategy defines how to obtain and possibly transform the list
    of modules returned by a back‑end parser.  Subclasses must
    implement :meth:`get_modules` to return an iterable of
    :class:`svlang.model.Module` objects.
    """

    def __init__(self, include_dirs: Iterable[str] | None = None, defines: Iterable[str] | None = None) -> None:
        self.backend = SlangBackend(include_dirs=list(include_dirs or []), defines=list(defines or []))

    def load_design(self, files: List[str]) -> None:
        """Load one or more source files via the underlying back‑end."""
        self.backend.load_design(files)

    def get_modules(self) -> List[Module]:  # pragma: no cover
        """Return the processed modules for this strategy.

        Subclasses should override this to perform strategy‑specific
        transformations.  By default this returns the raw modules from
        the back‑end.
        """
        raise NotImplementedError


class LRM2017Strategy(InterfaceStrategy):
    """Interpretation strategy adhering to the SystemVerilog‑2017 LRM.

    This strategy simply returns the modules exactly as parsed by the
    back‑end.  It does not perform any post‑processing.  Use this
    strategy when working with hand‑written SystemVerilog code that
    conforms to the language reference manual.
    """

    def load_design(self, files: List[str]) -> None:
        """Load the design and enforce strict LRM semantics.

        This overrides :meth:`InterfaceStrategy.load_design` to
        ensure that any compilation errors reported by the slang
        backend cause an immediate failure.  It delegates to the
        underlying backend for parsing and then checks the error
        status.  If errors were encountered, a :class:`RuntimeError`
        is raised with the collected diagnostic messages.
        """
        super().load_design(files)
        if self.backend.had_errors():
            # Compose a message from the error list.  If no messages
            # were recorded, fall back to a generic error string.
            msgs = self.backend.get_error_messages()
            if msgs:
                raise RuntimeError("Slang compilation failed: " + "; ".join(msgs))
            else:
                raise RuntimeError("Slang compilation failed with unknown errors")

    def get_modules(self) -> List[Module]:
        return self.backend.get_modules()


class Genesis2Strategy(InterfaceStrategy):
    """Interpretation strategy for Genesis2‑generated RTL.

    Genesis2 (a code generator from Stanford) produces SystemVerilog
    modules with certain idiosyncrasies such as ``import`` statements
    between the module name and the port list, and flattened interface
    ports with encoded names.  The slang back‑end correctly parses
    these modules, so this strategy currently performs no additional
    processing.  In the future you can extend this class to group
    flattened ports into higher‑level interface constructs or to
    interpret special debug comments emitted by Genesis2.
    """

    def load_design(self, files: List[str]) -> None:
        """Preprocess Genesis2 RTL and load it with the slang backend.

        Genesis2 emits RTL with debug comment lines and `var` modifiers
        that are not part of the SystemVerilog LRM.  To give slang a
        fighting chance at compiling these files we perform a simple
        textual transformation:

        * Lines containing ``DBG:`` (debug annotations) are dropped.
        * ``var`` keywords immediately following a port direction
          (``input``, ``output`` or ``inout``) are removed.
        * Top‑level ``import`` statements (prior to the port list) are
          removed.

        Each source file is read, transformed and written to a
        temporary file.  The slang backend is then invoked on these
        pre‑processed files.  Any compilation errors are recorded but
        not raised; Genesis2 code is tolerated even if slang finds
        unresolved references or other issues.
        """
        # Preprocess each input file into a temporary file.
        processed: List[str] = []
        for path in files:
            processed.append(self._preprocess_file(path))
        # Load the cleaned files using the backend.  Errors are not
        # considered fatal for Genesis2; we ignore any exceptions.
        self.backend.load_design(processed)

    def get_modules(self) -> List[Module]:
        return self.backend.get_modules()

    # ------------------------------------------------------------------
    # Internal helpers

    def _preprocess_file(self, path: str) -> str:
        """Return a path to a cleaned copy of the given SystemVerilog file.

        The cleaning process removes Genesis2 debug comments (``// DBG:``),
        strips the ``var`` keyword after port directions, and drops
        ``import`` statements.  The returned file is created in a
        temporary directory and should be cleaned up by the caller if
        necessary.
        """
        import os
        import re
        import tempfile
        # Read the original file
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        cleaned: List[str] = []
        saw_module = False
        for line in lines:
            # Skip lines containing debug annotations
            if "DBG:" in line:
                continue
            # Skip import statements entirely
            if re.match(r"\s*import\s+.*;", line):
                continue
            # Once we have seen the module line, remove 'var' after port direction
            # e.g. 'input var logic [31:0] foo' -> 'input logic [31:0] foo'
            stripped = line
            # Replace 'input var', 'output var', 'inout var'
            stripped = re.sub(r"\b(input|output|inout)\s+var\b", r"\1", stripped)
            cleaned.append(stripped)
        # Write to a temporary file
        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=os.path.splitext(path)[1], prefix="gen2_", encoding="utf-8")
        tmp.writelines(cleaned)
        tmp.close()
        return tmp.name
