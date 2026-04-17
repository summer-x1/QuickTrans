"""Main daemon — event monitoring, selection handling, translation orchestration."""

import atexit
import fcntl
import logging
import os
import signal
import sys
import threading
import time
from types import SimpleNamespace
from typing import Optional

from AppKit import (
    NSApplication,
    NSEvent,
    NSScreen,
    NSLeftMouseDownMask,
    NSLeftMouseUpMask,
    NSKeyUpMask,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from quicktrans import clipboard, translate
from quicktrans.ui import trigger, popup, menubar

logger = logging.getLogger("quicktrans")

# Daemon state
_mouse_down_pos = None
_last_translated = ""
_pending_text = ""
_pending_old_clipboard = ""
_pending_anchor = None
_selection_lock = threading.Lock()
_config = None
_lock_fp = None

_DOUBLE_CLICK_DELAY = 0.2
_ARROW_KEYS = {123, 124, 125, 126}  # left, right, down, up

PID_DIR = os.path.expanduser("~/.config/quicktrans")
PID_FILE = os.path.join(PID_DIR, "quicktrans.pid")


def _ensure_single_instance():
    """Ensure only one daemon instance runs. Returns file handle (must keep ref)."""
    os.makedirs(PID_DIR, exist_ok=True)
    pid_fp = None
    try:
        pid_fp = open(PID_FILE, "a+")
        fcntl.flock(pid_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pid_fp.seek(0)
        pid_fp.truncate()
        pid_fp.write(str(os.getpid()))
        pid_fp.flush()
        return pid_fp
    except (IOError, OSError):
        if pid_fp is not None:
            try:
                pid_fp.close()
            except Exception:
                pass
        print("Another QuickTrans instance is already running. Exiting.")
        sys.exit(0)


def _cleanup_single_instance() -> None:
    """Release the instance lock and remove the PID file on normal shutdown."""
    global _lock_fp

    if _lock_fp is None:
        return

    try:
        try:
            _lock_fp.close()
        except Exception:
            pass

        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.debug("Could not remove PID file: %s", exc)
    finally:
        _lock_fp = None


def _handle_shutdown_signal(signum, frame):
    """Handle termination signals with explicit cleanup."""
    _cleanup_single_instance()
    raise SystemExit(0)


def _get_mouse_pos():
    """Get current mouse position in screen coordinates (top-left origin)."""
    loc = NSEvent.mouseLocation()
    screen = NSScreen.mainScreen()
    if screen:
        return (loc.x, screen.frame().size.height - loc.y)
    return (loc.x, loc.y)


def _resolve_anchor(anchor=None):
    """Resolve a stable UI anchor captured at selection time."""
    return anchor if anchor is not None else _get_mouse_pos()


def _do_translate():
    """Translate pending text and show popup. Runs in worker thread."""
    global _last_translated, _pending_old_clipboard, _pending_anchor

    text = _pending_text
    if not text:
        return

    logger.info("Translating: %s...", text[:60])
    mx, my = _resolve_anchor(_pending_anchor)
    translated, error = translate.translate_text(text, _config)

    if _pending_old_clipboard:
        clipboard.set_clipboard(_pending_old_clipboard)

    _present_translation_result(text, translated, error, mx, my)


def _present_translation_result(
    source_text: str,
    translated: Optional[str],
    error: Optional[str],
    x: float,
    y: float,
) -> None:
    """Update UI after a translation attempt finishes."""
    global _last_translated

    if error:
        logger.error("Translation failed: %s", error)
        AppHelper.callAfter(trigger.dismiss)
        AppHelper.callAfter(popup.show_error, error, x, y, _config)
        return

    if translated and translated.strip() != source_text.strip():
        _last_translated = source_text
        logger.info("Result: %s...", translated[:60])
        AppHelper.callAfter(trigger.dismiss)
        AppHelper.callAfter(popup.show, translated, x, y, _config)
        return

    logger.info("No translation or same as original.")
    AppHelper.callAfter(trigger.dismiss)
    AppHelper.callAfter(popup.show_notice, "原文无需翻译", x, y, _config)


def _on_trigger_click():
    """Called when user clicks the trigger icon."""
    mx, my = _resolve_anchor(_pending_anchor)
    AppHelper.callAfter(trigger.dismiss)
    AppHelper.callAfter(popup.show_loading, mx, my, _config)
    threading.Thread(target=_do_translate, daemon=True).start()


def _handle_selection(anchor=None):
    """Copy selected text and show trigger icon if text found."""
    global _pending_text, _pending_old_clipboard, _pending_anchor

    if not _selection_lock.acquire(blocking=False):
        return
    try:
        logger.debug("Drag detected, getting selection...")

        old_cb = clipboard.get_clipboard()
        old_change_count = clipboard.get_clipboard_change_count()
        direct_text = clipboard.copy_selection()

        if direct_text and len(direct_text.strip()) >= _config.min_text_length:
            text = direct_text.strip()
            _pending_old_clipboard = ""
            logger.debug("Got text via AX API: %s...", text[:40])
        else:
            new_cb = clipboard.wait_for_new_clipboard(old_change_count, old_cb)
            if not new_cb or len(new_cb.strip()) < _config.min_text_length:
                logger.debug("No new text, skipping.")
                return
            text = new_cb.strip()
            _pending_old_clipboard = old_cb
            logger.debug("Got text via clipboard: %s...", text[:40])

        _pending_text = text
        _pending_anchor = _resolve_anchor(anchor)
        mx, my = _pending_anchor
        AppHelper.callAfter(trigger.show, mx, my, _config, _on_trigger_click)
    finally:
        _selection_lock.release()


class _AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        # Set up menu bar
        menubar.setup(_config)

        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSLeftMouseDownMask, self.handleMouseDown_
        )
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSLeftMouseUpMask, self.handleMouseUp_
        )
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyUpMask, self.handleKeyUp_
        )
        logger.info("QuickTrans daemon started. Select text to translate.")

    def handleMouseDown_(self, event):
        global _mouse_down_pos
        loc = NSEvent.mouseLocation()
        screen = NSScreen.mainScreen()
        if screen:
            _mouse_down_pos = (loc.x, screen.frame().size.height - loc.y)
        else:
            _mouse_down_pos = (loc.x, loc.y)
        AppHelper.callAfter(trigger.dismiss)
        AppHelper.callAfter(popup.dismiss)

    def handleMouseUp_(self, event):
        global _mouse_down_pos
        if menubar.is_paused():
            _mouse_down_pos = None
            return

        if _mouse_down_pos:
            loc = NSEvent.mouseLocation()
            screen = NSScreen.mainScreen()
            if screen:
                up_y = screen.frame().size.height - loc.y
            else:
                up_y = loc.y
            dx = loc.x - _mouse_down_pos[0]
            dy = up_y - _mouse_down_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist >= _config.min_drag_distance:
                # Drag selection
                anchor = (loc.x, up_y)
                threading.Thread(target=_handle_selection, args=(anchor,), daemon=True).start()
            elif event.clickCount() == 2:
                # Double-click word selection
                def delayed_selection():
                    time.sleep(_DOUBLE_CLICK_DELAY)
                    _handle_selection((loc.x, up_y))
                threading.Thread(target=delayed_selection, daemon=True).start()

        _mouse_down_pos = None

    def handleKeyUp_(self, event):
        if menubar.is_paused():
            return
        # Detect Shift+Arrow key release (keyboard text selection)
        flags = event.modifierFlags()
        key_code = event.keyCode()
        shift_held = flags & (1 << 17)  # NSEventModifierFlagShift
        if shift_held and key_code in _ARROW_KEYS:
            anchor = _get_mouse_pos()
            threading.Thread(target=_handle_selection, args=(anchor,), daemon=True).start()

    def dismissPopup_(self, timer):
        popup.dismiss()

    def dismissTrigger_(self, timer):
        trigger.dismiss()


def main(config: SimpleNamespace) -> None:
    """Start the QuickTrans daemon."""
    global _config, _lock_fp
    _config = config

    _lock_fp = _ensure_single_instance()
    atexit.register(_cleanup_single_instance)

    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = _AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    logger.info("Starting event loop...")
    try:
        AppHelper.runEventLoop()
    finally:
        _cleanup_single_instance()
