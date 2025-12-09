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

    def get_modules(self) -> List[Module]:
        return self.backend.get_modules()