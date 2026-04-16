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

        with patch("quicktrans.clipboard.Quartz.AXUIElementCreateSystemWide", create=True) as mock_create:
            with patch("quicktrans.clipboard.Quartz.AXUIElementCopyAttributeValue", create=True) as mock_copy:
                # Mock AX API failure
                mock_create.return_value = Mock()
                mock_copy.return_value = (-1, None)  # AXFocusedApplication fails

                result = copy_selection()
                # Should return None, caller reads clipboard
                self.assertIsNone(result)
                # Should have called osascript for Cmd+C
                self.assertTrue(any("osascript" in str(call) for call in mock_run.call_args_list))

    @patch("quicktrans.clipboard.time.sleep")
    @patch("quicktrans.clipboard.get_clipboard_change_count")
    @patch("quicktrans.clipboard.get_clipboard")
    def test_wait_for_new_clipboard_returns_changed_text(self, mock_get_clipboard, mock_change_count, mock_sleep):
        from quicktrans.clipboard import wait_for_new_clipboard

        mock_get_clipboard.side_effect = ["old", "old", "new value"]
        mock_change_count.side_effect = [1, 1, 2]

        result = wait_for_new_clipboard(1, "old", timeout=0.2, poll_interval=0.01)
        self.assertEqual(result, "new value")

    @patch("quicktrans.clipboard.time.sleep")
    @patch("quicktrans.clipboard.time.time")
    @patch("quicktrans.clipboard.get_clipboard_change_count")
    @patch("quicktrans.clipboard.get_clipboard")
    def test_wait_for_new_clipboard_times_out(self, mock_get_clipboard, mock_change_count, mock_time, mock_sleep):
        from quicktrans.clipboard import wait_for_new_clipboard

        mock_get_clipboard.return_value = "old"
        mock_change_count.return_value = 1
        mock_time.side_effect = [0.0, 0.05, 0.1, 0.15, 0.21]

        result = wait_for_new_clipboard(1, "old", timeout=0.2, poll_interval=0.01)
        self.assertIsNone(result)

    @patch("quicktrans.clipboard.time.sleep")
    @patch("quicktrans.clipboard.get_clipboard_change_count")
    @patch("quicktrans.clipboard.get_clipboard")
    def test_wait_for_new_clipboard_accepts_same_text_when_change_count_updates(
        self,
        mock_get_clipboard,
        mock_change_count,
        mock_sleep,
    ):
        from quicktrans.clipboard import wait_for_new_clipboard

        mock_get_clipboard.return_value = "repeat"
        mock_change_count.side_effect = [1, 1, 2]

        result = wait_for_new_clipboard(1, "repeat", timeout=0.2, poll_interval=0.01)
        self.assertEqual(result, "repeat")


if __name__ == "__main__":
    unittest.main()
