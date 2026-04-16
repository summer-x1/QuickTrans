"""Tests for daemon single-instance cleanup."""

import fcntl
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


try:
    from quicktrans import daemon
    HAS_DAEMON = True
except Exception:
    HAS_DAEMON = False


@unittest.skipUnless(HAS_DAEMON, "daemon dependencies not available")
class TestDaemonCleanup(unittest.TestCase):
    def test_ensure_single_instance_writes_pid_after_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_file = os.path.join(tmpdir, "quicktrans.pid")
            old_pid_file = daemon.PID_FILE
            try:
                daemon.PID_FILE = pid_file
                lock_fp = daemon._ensure_single_instance()
                try:
                    with open(pid_file, "r", encoding="utf-8") as f:
                        self.assertEqual(f.read().strip(), str(os.getpid()))
                finally:
                    lock_fp.close()
                    if os.path.exists(pid_file):
                        os.remove(pid_file)
            finally:
                daemon.PID_FILE = old_pid_file

    def test_ensure_single_instance_does_not_truncate_pid_file_on_lock_conflict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_file = os.path.join(tmpdir, "quicktrans.pid")
            with open(pid_file, "w+", encoding="utf-8") as holder:
                holder.write("12345")
                holder.flush()
                fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)

                old_pid_file = daemon.PID_FILE
                try:
                    daemon.PID_FILE = pid_file
                    with self.assertRaises(SystemExit):
                        daemon._ensure_single_instance()
                finally:
                    daemon.PID_FILE = old_pid_file

                holder.seek(0)
                self.assertEqual(holder.read(), "12345")

    def test_cleanup_single_instance_removes_pid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_file = os.path.join(tmpdir, "quicktrans.pid")
            lock_fp = open(pid_file, "w", encoding="utf-8")
            lock_fp.write(str(os.getpid()))
            lock_fp.flush()

            old_pid_file = daemon.PID_FILE
            old_lock_fp = daemon._lock_fp
            try:
                daemon.PID_FILE = pid_file
                daemon._lock_fp = lock_fp

                daemon._cleanup_single_instance()

                self.assertIsNone(daemon._lock_fp)
                self.assertFalse(os.path.exists(pid_file))
            finally:
                daemon.PID_FILE = old_pid_file
                daemon._lock_fp = old_lock_fp

    def test_cleanup_single_instance_is_idempotent(self):
        old_lock_fp = daemon._lock_fp
        try:
            daemon._lock_fp = None
            daemon._cleanup_single_instance()
            self.assertIsNone(daemon._lock_fp)
        finally:
            daemon._lock_fp = old_lock_fp

    def test_present_translation_result_shows_notice_for_same_text(self):
        with patch.object(daemon, "_config", object()), \
             patch("quicktrans.daemon.AppHelper.callAfter") as mock_call_after:
            daemon._present_translation_result(
                "python3 -m compileall quicktrans",
                "python3 -m compileall quicktrans",
                None,
                10,
                20,
            )

        self.assertEqual(mock_call_after.call_count, 2)
        self.assertEqual(mock_call_after.call_args_list[0].args[0], daemon.trigger.dismiss)
        self.assertEqual(mock_call_after.call_args_list[1].args[0], daemon.popup.show_notice)
        self.assertEqual(mock_call_after.call_args_list[1].args[1], "原文无需翻译")

    def test_present_translation_result_shows_error_popup(self):
        with patch.object(daemon, "_config", object()), \
             patch("quicktrans.daemon.AppHelper.callAfter") as mock_call_after:
            daemon._present_translation_result("hello", None, "网络连接失败，请检查网络", 1, 2)

        self.assertEqual(mock_call_after.call_count, 2)
        self.assertEqual(mock_call_after.call_args_list[0].args[0], daemon.trigger.dismiss)
        self.assertEqual(mock_call_after.call_args_list[1].args[0], daemon.popup.show_error)

    def test_handle_selection_allows_same_text_when_clipboard_change_count_updates(self):
        old_config = daemon._config
        old_pending_text = daemon._pending_text
        old_pending_old_clipboard = daemon._pending_old_clipboard
        old_pending_anchor = daemon._pending_anchor
        old_last_translated = daemon._last_translated
        try:
            daemon._config = SimpleNamespace(min_text_length=1)
            daemon._pending_text = ""
            daemon._pending_old_clipboard = ""
            daemon._pending_anchor = None
            daemon._last_translated = "repeat"

            with patch("quicktrans.daemon.clipboard.get_clipboard", return_value="repeat"), \
                 patch("quicktrans.daemon.clipboard.get_clipboard_change_count", return_value=1), \
                 patch("quicktrans.daemon.clipboard.copy_selection", return_value=None), \
                 patch("quicktrans.daemon.clipboard.wait_for_new_clipboard", return_value="repeat"), \
                 patch("quicktrans.daemon.AppHelper.callAfter") as mock_call_after:
                daemon._handle_selection((30, 40))

            self.assertEqual(daemon._pending_text, "repeat")
            self.assertEqual(daemon._pending_anchor, (30, 40))
            self.assertEqual(mock_call_after.call_args_list[-1].args[0], daemon.trigger.show)
            self.assertEqual(mock_call_after.call_args_list[-1].args[1:3], (30, 40))
        finally:
            daemon._config = old_config
            daemon._pending_text = old_pending_text
            daemon._pending_old_clipboard = old_pending_old_clipboard
            daemon._pending_anchor = old_pending_anchor
            daemon._last_translated = old_last_translated


if __name__ == "__main__":
    unittest.main()
