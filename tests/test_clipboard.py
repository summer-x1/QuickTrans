"""Tests for clipboard module."""

import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
from types import SimpleNamespace

# Skip all tests in this module if Quartz isn't available (non-macOS)
try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


@unittest.skipUnless(HAS_QUARTZ, "Quartz not available (macOS only)")
class TestClipboard(unittest.TestCase):
    @patch("quicktrans.clipboard.subprocess.run")
    def test_get_clipboard(self, mock_run):
        mock_run.return_value = MagicMock(stdout="test text")
        from quicktrans.clipboard import get_clipboard
        result = get_clipboard()
        self.assertEqual(result, "test text")
        mock_run.assert_called_once_with(["pbpaste"], capture_output=True, text=True)

    @patch("quicktrans.clipboard.subprocess.run")
    def test_set_clipboard(self, mock_run):
        from quicktrans.clipboard import set_clipboard
        set_clipboard("new text")
        mock_run.assert_called_once_with(["pbcopy"], input=b"new text")

    @patch("quicktrans.clipboard.subprocess.run")
    @patch("quicktrans.clipboard.time.sleep")
    def test_copy_selection_fallback_to_cmd_c(self, mock_sleep, mock_run):
        from quicktrans.clipboard import copy_selection

        with patch("quicktrans.clipboard.Quartz.AXUIElementCreateSystemWide") as mock_create:
            with patch("quicktrans.clipboard.Quartz.AXUIElementCopyAttributeValue") as mock_copy:
                # Mock AX API failure
                mock_create.return_value = Mock()
                mock_copy.return_value = (-1, None)  # AXFocusedApplication fails

                result = copy_selection()
                # Should return None, caller reads clipboard
                self.assertIsNone(result)
                # Should have called osascript for Cmd+C
                self.assertTrue(any("osascript" in str(call) for call in mock_run.call_args_list))


if __name__ == "__main__":
    unittest.main()
