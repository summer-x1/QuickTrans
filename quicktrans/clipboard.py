"""Clipboard operations and text selection capture."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

import Quartz

logger: logging.Logger = logging.getLogger("quicktrans")


def get_clipboard() -> str:
    """Read current clipboard text."""
    result = subprocess.run(["pbpaste"], capture_output=True, text=True)
    return result.stdout


def set_clipboard(text: str) -> None:
    """Write text to clipboard."""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"))


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
