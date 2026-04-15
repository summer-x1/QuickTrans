"""Trigger icon — rounded square button with '译' shown after text selection."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import objc
from AppKit import (
    NSApplication,
    NSWindow,
    NSView,
    NSFont,
    NSColor,
    NSScreen,
    NSTimer,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSBezierPath,
    NSMutableParagraphStyle,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName,
    NSCenterTextAlignment,
    NSTrackingArea,
    NSTrackingMouseEnteredAndExited,
    NSTrackingActiveAlways,
    NSCursor,
    NSAttributedString,
    NSProgressIndicator,
    NSProgressIndicatorSpinningStyle,
    NSControlSizeSmall,
)

logger = logging.getLogger("quicktrans")

# Module-level state
_trigger_window = None
_trigger_timer = None
_on_click_callback = None
_config = None
_trigger_view = None


class TriggerView(NSView):
    """A rounded square button with '译' that triggers translation on click."""

    def initWithFrame_(self, frame):
        self = objc.super(TriggerView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.hovered = False
        self.loading = False
        self._spinner = None
        return self

    def acceptsFirstMouse_(self, event):
        return True

    def resetCursorRects(self):
        if not self.loading:
            self.addCursorRect_cursor_(self.bounds(), NSCursor.pointingHandCursor())

    def updateTrackingAreas(self):
        for ta in self.trackingAreas():
            self.removeTrackingArea_(ta)
        ta = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(),
            NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways,
            self, None,
        )
        self.addTrackingArea_(ta)
        objc.super(TriggerView, self).updateTrackingAreas()

    def mouseEntered_(self, event):
        if not self.loading:
            self.hovered = True
            self.setNeedsDisplay_(True)

    def mouseExited_(self, event):
        self.hovered = False
        self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        if self.loading:
            return
        logger.info("Trigger clicked — starting translation.")
        self.setLoading_(True)
        if _on_click_callback:
            _on_click_callback()

    def setLoading_(self, loading):
        self.loading = loading
        icon_size = _config.icon_size if _config else 26

        if loading:
            NSColor.systemGrayColor().setFill()
        else:
            NSColor.controlAccentColor().setFill()
        self.setWantsLayer_(True)
        self.layer().setCornerRadius_(8)  # Rounded square

        # Draw "译" text
        if not self.loading:
            font = NSFont.boldSystemFontOfSize_(icon_size * 0.5)
            style = NSMutableParagraphStyle.alloc().init()
            style.setAlignment_(NSCenterTextAlignment)
            attrs = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: NSColor.whiteColor(),
                NSParagraphStyleAttributeName: style,
            }
            s = NSAttributedString.alloc().initWithString_attributes_("译", attrs)
            h = s.size().height
            s.drawInRect_(NSMakeRect(0, (icon_size - h) / 2 - 1, icon_size, h))

    def show(x: float, y: float, config: SimpleNamespace, on_click) -> None:
        """Show trigger icon near mouse position."""
        global _trigger_window, _trigger_timer, _on_click_callback, _config, _trigger_view
        dismiss()

        _config = config
        _on_click_callback = on_click
        icon_size = config.icon_size

        screen = NSScreen.mainScreen()
        if not screen:
            return
        scr_h = screen.frame().size.height
        scr_w = screen.frame().size.width

        win_x = x + 8
        win_y = scr_h - y - icon_size - 8
        if win_x + icon_size > scr_w:
            win_x = x - icon_size - 8
        if win_y < 0:
            win_y = scr_h - y + 8

        frame = NSMakeRect(win_x, win_y, icon_size, icon_size)
        _trigger_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
        )
        _trigger_window.setLevel_(NSFloatingWindowLevel + 1)
        _trigger_window.setOpaque_(False)
        _trigger_window.setBackgroundColor_(NSColor.clearColor())
        _trigger_window.setHasShadow_(True)
        _trigger_window.setIgnoresMouseEvents_(False)
        _trigger_window.setWantsLayer_(True)
        _trigger_window.layer().setCornerRadius_(8)

        tv = TriggerView.alloc().initWithFrame_(NSMakeRect(0, 0, icon_size, icon_size))
        _trigger_window.contentView().addSubview_(tv)
        _trigger_window.orderFrontRegardless()

        _trigger_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            config.icon_dismiss_delay,
            NSApplication.sharedApplication().delegate(),
            "dismissTrigger:", None, False,
        )
        logger.debug("Trigger shown at (%d, %d)", int(x), int(y))


def show_loading() -> None:
    """Switch to trigger icon to loading state."""
    if _trigger_view:
        _trigger_view.setLoading_(True)
        # Cancel auto-dismiss timer while loading
        global _trigger_timer
        if _trigger_timer:
            _trigger_timer.invalidate()
            _trigger_timer = None


def dismiss(_=None) -> None:
    """Dismiss trigger icon."""
    global _trigger_window, _trigger_timer, _trigger_view
    if _trigger_window:
        _trigger_window.orderOut_(None)
        _trigger_window = None
    if _trigger_timer:
        _trigger_timer.invalidate()
        _trigger_timer = None
    _trigger_view = None
