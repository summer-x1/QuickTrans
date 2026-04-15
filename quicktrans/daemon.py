"""Main daemon — event monitoring, selection handling, translation orchestration."""

import fcntl
import logging
import os
import signal
import sys
import threading
import time
from types import SimpleNamespace

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
_selection_lock = threading.Lock()
_config = None

_DOUBLE_CLICK_DELAY = 0.2
_SHIFT_KEY_CODE = 56
_ARROW_KEYS = {123, 124, 125, 126}  # left, right, down, up

PID_DIR = os.path.expanduser("~/.config/quicktrans")
PID_FILE = os.path.join(PID_DIR, "quicktrans.pid")


def _ensure_single_instance():
    """Ensure only one daemon instance runs. Returns file handle (must keep ref)."""
    os.makedirs(PID_DIR, exist_ok=True)
    try:
        pid_fp = open(PID_FILE, "w")
        fcntl.flock(pid_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pid_fp.write(str(os.getpid()))
        pid_fp.flush()
        return pid_fp
    except (IOError, OSError):
        print("Another QuickTrans instance is already running. Exiting.")
        sys.exit(0)


def _get_mouse_pos():
    """Get current mouse position in screen coordinates (top-left origin)."""
    loc = NSEvent.mouseLocation()
    screen = NSScreen.mainScreen()
    if screen:
        return (loc.x, screen.frame().size.height - loc.y)
    return (loc.x, loc.y)


def _do_translate():
    """Translate pending text and show popup. Runs in worker thread."""
    global _last_translated, _pending_old_clipboard

    text = _pending_text
    if not text:
        return

    logger.info("Translating: %s...", text[:60])
    mx, my = _get_mouse_pos()
    translated, error = translate.translate_text(text, _config)

    if _pending_old_clipboard:
        clipboard.set_clipboard(_pending_old_clipboard)

    if error:
        logger.error("Translation failed: %s", error)
        AppHelper.callAfter(trigger.dismiss)
        AppHelper.callAfter(popup.show_error, error, mx, my, _config)
    elif translated and translated.strip() != text.strip():
        _last_translated = text
        logger.info("Result: %s...", translated[:60])
        AppHelper.callAfter(trigger.dismiss)
        AppHelper.callAfter(popup.show, translated, mx, my, _config)
    else:
        logger.info("No translation or same as original.")
        AppHelper.callAfter(trigger.dismiss)


def _on_trigger_click():
    """Called when user clicks the trigger icon."""
    AppHelper.callAfter(trigger.show_loading)
    threading.Thread(target=_do_translate, daemon=True).start()


def _handle_selection():
    """Copy selected text and show trigger icon if text found."""
    global _pending_text, _pending_old_clipboard

    if not _selection_lock.acquire(blocking=False):
        return
    try:
        logger.debug("Drag detected, getting selection...")

        old_cb = clipboard.get_clipboard()
        direct_text = clipboard.copy_selection()

        if direct_text and len(direct_text.strip()) >= _config.min_text_length:
            text = direct_text.strip()
            _pending_old_clipboard = ""
            logger.debug("Got text via AX API: %s...", text[:40])
        else:
            new_cb = clipboard.get_clipboard()
            if not new_cb or new_cb == old_cb or len(new_cb.strip()) < _config.min_text_length:
                logger.debug("No new text, skipping.")
                return
            text = new_cb.strip()
            _pending_old_clipboard = old_cb
            logger.debug("Got text via clipboard: %s...", text[:40])

        if text == _last_translated:
            if _pending_old_clipboard:
                clipboard.set_clipboard(_pending_old_clipboard)
            return

        _pending_text = text
        mx, my = _get_mouse_pos()
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
                threading.Thread(target=_handle_selection, daemon=True).start()
            elif event.clickCount() == 2:
                # Double-click word selection
                def delayed_selection():
                    time.sleep(_DOUBLE_CLICK_DELAY)
                    _handle_selection()
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
            threading.Thread(target=_handle_selection, daemon=True).start()

    def dismissPopup_(self, timer):
        popup.dismiss()

    def dismissTrigger_(self, timer):
        trigger.dismiss()


def main(config: SimpleNamespace) -> None:
    """Start the QuickTrans daemon."""
    global _config
    _config = config

    lock_fp = _ensure_single_instance()  # noqa: F841

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = _AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    logger.info("Starting event loop...")
    AppHelper.runEventLoop()
