"""Unit tests for Genesis2 preprocessing.

This test module exercises the Genesis2Strategy preprocessing stage
without requiring the ``pyslang`` compiler.  The Genesis2 frontend
strips debug annotations and ``var`` keywords from Genesis2‑generated
RTL before handing the cleaned source to the real slang backend.
Import statements are preserved so that slang can resolve types from
packages.  These tests ensure the textual transformations occur as
expected.

The tests in this file are always executed regardless of whether
``pyslang`` is installed, because they do not rely on compiling the
cleaned source.  See :mod:`tests.test_genesis2` for tests that
exercise the full compilation flow when ``pyslang`` is present.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest

from svlang.strategy import Genesis2Strategy


class TestGenesis2Preprocess(unittest.TestCase):
    """Verify that the Genesis2 preprocessing strips unsupported tokens."""

    def _write_temp_sv(self, content: str) -> str:
        """Helper to write a temporary SV file and return its path."""
        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".sv", prefix="testgen2_")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_dbg_and_var_removed_import_preserved(self) -> None:
        """The preprocessing should drop DBG comments and var keywords, but preserve imports."""
        sv_text = """
import pkg::*;
module test;
    // DBG: this is a debug comment
    input var logic [3:0] foo,
          var logic bar;
endmodule
"""
        # Write the source to a temporary file
        path = self._write_temp_sv(sv_text)
        try:
            strategy = Genesis2Strategy()
            cleaned_path = strategy._preprocess_file(path)
            # Read back the cleaned file contents
            with open(cleaned_path, "r", encoding="utf-8") as fh:
                cleaned = fh.read()
            # The import line should be preserved (for package resolution)
            self.assertIn("import pkg::*", cleaned)
            # DBG comment should be absent
            self.assertNotIn("DBG:", cleaned)
            # The 'var' keyword should be removed after directions
            self.assertNotIn("input var", cleaned)
            # Ports should still be present with logic type
            self.assertIn("input logic", cleaned)
            # Multi‑line port declarations should remain intact
            self.assertIn("logic [3:0] foo", cleaned)
            self.assertIn("logic bar", cleaned)
        finally:
            # Clean up temporary files
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()