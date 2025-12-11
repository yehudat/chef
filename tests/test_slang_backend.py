import unittest

from svlang.slang_backend import SlangBackend


class TestSlangBackendCleanDirection(unittest.TestCase):
    """Test the _clean_direction method for Genesis2 comment handling."""

    def setUp(self):
        self.backend = SlangBackend()

    def test_clean_direction_with_interface_comment(self):
        """Genesis2 comment with interface.modport should be preserved."""
        raw = "// ports for interface 'noc_stream_if.src_mp'\n    output"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "noc_stream_if.src_mp output")

    def test_clean_direction_with_d2d_interface(self):
        """Test with d2d_xpp_if.src_mp interface."""
        raw = "// ports for interface 'd2d_xpp_if.src_mp'\n    output"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "d2d_xpp_if.src_mp output")

    def test_clean_direction_input(self):
        """Test input direction with interface comment."""
        raw = "// ports for interface 'apb_if.snk_mp'\n    input"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "apb_if.snk_mp input")

    def test_clean_direction_plain_output(self):
        """Plain direction without comments should pass through."""
        raw = "output"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "output")

    def test_clean_direction_plain_input(self):
        """Plain input direction without comments should pass through."""
        raw = "input"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "input")

    def test_clean_direction_with_extra_whitespace(self):
        """Direction with extra whitespace should be cleaned."""
        raw = "// ports for interface 'test_if.mp'\n        output  "
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "test_if.mp output")

    def test_clean_direction_inout(self):
        """Test inout direction."""
        raw = "// ports for interface 'bidir_if.mp'\n    inout"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "bidir_if.mp inout")

    def test_clean_direction_with_other_comments(self):
        """Other single-line comments should be removed."""
        raw = "// some other comment\n    output"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "output")

    def test_clean_direction_multiline_genesis2_comment(self):
        """Test multiline Genesis2 comment format."""
        raw = "// per pipe signalling \n    // ports for interface 'd2d_recirc_if.src_mp'\n    input"
        result = self.backend._clean_direction(raw)
        self.assertEqual(result, "d2d_recirc_if.src_mp input")


if __name__ == '__main__':
    unittest.main()
