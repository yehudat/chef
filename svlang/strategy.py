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

import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, List, Set

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

        Import statements are preserved and the referenced packages are
        resolved by searching from the git repository root.  The resolved
        package files are written to a hidden ``.imports.f`` file and
        passed to slang for compilation.

        Each source file is read, transformed and written to a
        temporary file.  The slang backend is then invoked on these
        pre‑processed files along with any resolved package files.
        """
        import tempfile

        # Collect all imports from all files
        all_imports: Set[str] = set()
        for path in files:
            all_imports.update(self._extract_imports(path))

        # Resolve package files by searching from git root
        package_files: List[str] = []
        if all_imports:
            git_root = self._find_git_root(files[0])
            if git_root:
                package_files = self._resolve_packages(all_imports, git_root)

        # Preprocess each input file into a temporary file.
        processed: List[str] = []
        for path in files:
            processed.append(self._preprocess_file(path))

        # Create .imports.f file if we have package files
        if package_files:
            imports_f = os.path.join(os.path.dirname(processed[0]), ".imports.f")
            with open(imports_f, "w", encoding="utf-8") as f:
                for pkg_file in package_files:
                    f.write(f"{pkg_file}\n")

        # Load package files first, then the preprocessed main files
        all_files = package_files + processed
        self.backend.load_design(all_files)

    def get_modules(self) -> List[Module]:
        return self.backend.get_modules()

    # ------------------------------------------------------------------
    # Internal helpers

    def _extract_imports(self, path: str) -> Set[str]:
        """Extract package names from import statements in the file.

        Returns a set of package names (e.g., {'nif_pkg', 'sys_pkg'}).
        """
        imports: Set[str] = set()
        import_pattern = re.compile(r'import\s+(\w+)::')
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                for match in import_pattern.finditer(line):
                    imports.add(match.group(1))
        return imports

    def _find_git_root(self, path: str) -> str | None:
        """Find the git repository root for the given file path."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=os.path.dirname(os.path.abspath(path)),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _resolve_packages(self, package_names: Set[str], git_root: str) -> List[str]:
        """Resolve package names to file paths by searching from git root.

        Searches for files named <package_name>.sv or <package_name>.svh
        recursively under the git root.
        """
        resolved: List[str] = []
        root_path = Path(git_root)

        for pkg_name in package_names:
            # Search for <pkg_name>.sv or <pkg_name>.svh
            for pattern in [f"**/{pkg_name}.sv", f"**/{pkg_name}.svh"]:
                matches = list(root_path.glob(pattern))
                if matches:
                    # Use the first match found
                    resolved.append(str(matches[0]))
                    break

        return resolved

    def _preprocess_file(self, path: str) -> str:
        """Return a path to a cleaned copy of the given SystemVerilog file.

        The cleaning process removes Genesis2 debug comments (``// DBG:``),
        strips the ``var`` keyword after port directions.  Import statements
        are preserved so slang can use them with the resolved package files.
        The returned file is created in a temporary directory and should be
        cleaned up by the caller if necessary.
        """
        import tempfile

        # Read the original file
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        cleaned: List[str] = []
        for line in lines:
            # Skip lines containing debug annotations
            if "DBG:" in line:
                continue
            # Replace 'input var', 'output var', 'inout var'
            line = re.sub(r"\b(input|output|inout)\s+var\b", r"\1", line)
            cleaned.append(line)
        # Write to a temporary file
        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=os.path.splitext(path)[1], prefix="gen2_", encoding="utf-8")
        tmp.writelines(cleaned)
        tmp.close()
        return tmp.name
