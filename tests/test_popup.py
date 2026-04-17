"""Tests for popup lifecycle helpers."""

import unittest


try:
    from quicktrans.ui import popup
    HAS_POPUP = True
except Exception:
    HAS_POPUP = False


class _DummyWindow:
    def __init__(self):
        self.closed = False

    def orderOut_(self, _sender):
        self.closed = True


class _DummyTimer:
    def __init__(self):
        self.invalidated = False

    def invalidate(self):
        self.invalidated = True


@unittest.skipUnless(HAS_POPUP, "popup dependencies not available")
class TestPopupLifecycle(unittest.TestCase):
    def test_dismiss_respects_pinned_popup(self):
        old_window = popup._popup_window
        old_timer = popup._popup_timer
        old_is_pinned = popup._is_pinned
        try:
            window = _DummyWindow()
            timer = _DummyTimer()
            popup._popup_window = window
            popup._popup_timer = timer
            popup._is_pinned = True

            popup.dismiss()

            self.assertIs(popup._popup_window, window)
            self.assertIs(popup._popup_timer, timer)
            self.assertFalse(window.closed)
            self.assertFalse(timer.invalidated)
        finally:
            popup._popup_window = old_window
            popup._popup_timer = old_timer
            popup._is_pinned = old_is_pinned

    def test_force_close_replaces_pinned_popup(self):
        old_window = popup._popup_window
        old_timer = popup._popup_timer
        old_is_pinned = popup._is_pinned
        old_copy_action_ref = popup._copy_action_ref
        old_pin_action_ref = popup._pin_action_ref
        try:
            window = _DummyWindow()
            timer = _DummyTimer()
            popup._popup_window = window
            popup._popup_timer = timer
            popup._is_pinned = True
            popup._copy_action_ref = object()
            popup._pin_action_ref = object()

            popup._close_popup(force=True)

            self.assertIsNone(popup._popup_window)
            self.assertIsNone(popup._popup_timer)
            self.assertFalse(popup._is_pinned)
            self.assertTrue(window.closed)
            self.assertTrue(timer.invalidated)
            self.assertIsNone(popup._copy_action_ref)
            self.assertIsNone(popup._pin_action_ref)
        finally:
            popup._popup_window = old_window
            popup._popup_timer = old_timer
            popup._is_pinned = old_is_pinned
            popup._copy_action_ref = old_copy_action_ref
            popup._pin_action_ref = old_pin_action_ref


if __name__ == "__main__":
    unittest.main()
