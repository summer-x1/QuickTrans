"""Menu bar status item for QuickTrans."""

import logging
import os
import subprocess
from types import SimpleNamespace
from typing import Optional

from AppKit import (
    NSStatusBar,
    NSMenu,
    NSMenuItem,
    NSApplication,
    NSFont,
    NSAttributedString,
    NSFontAttributeName,
    NSVariableStatusItemLength,
)
from Foundation import NSObject

from quicktrans.config import CONFIG_FILE
from quicktrans.log import LOG_FILE

logger = logging.getLogger("quicktrans")

_status_item = None
_pause_item = None
_is_paused = False
_on_pause_toggle = None


class _MenuDelegate(NSObject):
    def togglePause_(self, sender):
        global _is_paused
        _is_paused = not _is_paused
        if _pause_item:
            _pause_item.setTitle_("Resume" if _is_paused else "Pause")
        _update_title()
        if _on_pause_toggle:
            _on_pause_toggle(_is_paused)
        logger.info("QuickTrans %s", "paused" if _is_paused else "resumed")

    def openConfig_(self, sender):
        subprocess.run(["open", CONFIG_FILE])

    def viewLog_(self, sender):
        subprocess.run(["open", LOG_FILE])

    def quitApp_(self, sender):
        logger.info("Quit from menu bar.")
        NSApplication.sharedApplication().terminate_(None)


_menu_delegate = None


def _update_title():
    if _status_item:
        title = "译" if not _is_paused else "译 ⏸"
        attrs = {NSFontAttributeName: NSFont.systemFontOfSize_(14)}
        attr_str = NSAttributedString.alloc().initWithString_attributes_(title, attrs)
        _status_item.button().setAttributedTitle_(attr_str)


def is_paused() -> bool:
    """Check if translation is paused."""
    return _is_paused


def setup(config: SimpleNamespace, on_pause_toggle=None) -> None:
    """Create the menu bar status item."""
    global _status_item, _pause_item, _menu_delegate, _on_pause_toggle

    _on_pause_toggle = on_pause_toggle
    _menu_delegate = _MenuDelegate.alloc().init()

    _status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
        NSVariableStatusItemLength
    )
    _update_title()

    menu = NSMenu.alloc().init()

    # Title
    title_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "QuickTrans v0.2.0", None, ""
    )
    title_item.setEnabled_(False)
    menu.addItem_(title_item)
    menu.addItem_(NSMenuItem.separatorItem())

    # Pause/Resume
    _pause_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Pause", "togglePause:", ""
    )
    _pause_item.setTarget_(_menu_delegate)
    menu.addItem_(_pause_item)
    menu.addItem_(NSMenuItem.separatorItem())

    # Open Config
    config_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Open Config...", "openConfig:", ""
    )
    config_item.setTarget_(_menu_delegate)
    menu.addItem_(config_item)

    # View Log
    log_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "View Log...", "viewLog:", ""
    )
    log_item.setTarget_(_menu_delegate)
    menu.addItem_(log_item)
    menu.addItem_(NSMenuItem.separatorItem())

    # Quit
    quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Quit", "quitApp:", ""
    )
    quit_item.setTarget_(_menu_delegate)
    menu.addItem_(quit_item)

    _status_item.setMenu_(menu)
    logger.info("Menu bar icon created.")
