"""Clipboard operations and text selection capture."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

import Quartz
from AppKit import NSPasteboard

logger: logging.Logger = logging.getLogger("quicktrans")


def get_clipboard() -> str:
    """Read current clipboard text."""
    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
    return result.stdout


def set_clipboard(text: str) -> None:
    """Write text to clipboard."""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"))


def get_clipboard_change_count() -> int:
    """Return the current macOS pasteboard change count."""
    return int(NSPasteboard.generalPasteboard().changeCount())


def copy_selection() -> Optional[str]:
    """Get selected text. Tries Accessibility API first, falls back to Cmd+C.

    Returns:
        The selected text if obtained via AX API, or None if the caller
        should read the clipboard (Cmd+C fallback was used).
    """
    # Method 1: Accessibility API — reads selected text directly
    try:
        sys_elem = Quartz.AXUIElementCreateSystemWide()
        err: int
        focused_app: Optional[Quartz.AXUIElementRef] = None
        err, focused_app = Quartz.AXUIElementCopyAttributeValue(
            sys_elem, "AXFocusedApplication", None
        )
        if err == 0 and focused_app:
            focused_elem: Optional[Quartz.AXUIElementRef] = None
            err, focused_elem = Quartz.AXUIElementCopyAttributeValue(
                focused_app, "AXFocusedUIElement", None
            )
            if err == 0 and focused_elem:
                selected: Optional[str] = None
                err, selected = Quartz.AXUIElementCopyAttributeValue(
                    focused_elem, "AXSelectedText", None
                )
                if err == 0 and selected:
                    return str(selected)
    except Exception:
        pass

    # Method 2: Simulate Cmd+C via osascript
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "c" using command down'],
        capture_output=True,
    )
    time.sleep(0.3)
    return None


def wait_for_new_clipboard(
    previous_change_count: int,
    previous_text: str,
    timeout: float = 0.8,
    poll_interval: float = 0.05,
) -> Optional[str]:
    """Wait briefly for clipboard contents to change after Cmd+C fallback."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        current_change_count = get_clipboard_change_count()
        current = get_clipboard()
        if current and current_change_count != previous_change_count:
            return current
        if current and current != previous_text:
            return current
        time.sleep(poll_interval)
    return None
