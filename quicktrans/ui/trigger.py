"""Trigger icon — minimal dot button shown after text selection."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import objc
from AppKit import (
    NSApplication,
    NSAppearance,
    NSWindow,
    NSView,
    NSColor,
    NSScreen,
    NSTimer,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSBezierPath,
    NSTrackingArea,
    NSTrackingMouseEnteredAndExited,
    NSTrackingActiveAlways,
    NSCursor,
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


def _is_dark_mode() -> bool:
    appearance = NSAppearance.currentAppearance()
    return "Dark" in (appearance.name() or "")


def _trigger_palette() -> dict[str, NSColor]:
    """Trigger colors aligned with the popup's warm bubble palette."""
    if _is_dark_mode():
        bubble_fill = NSColor.colorWithRed_green_blue_alpha_(0.48, 0.38, 0.12, 0.98)
        bubble_hover = NSColor.colorWithRed_green_blue_alpha_(0.63, 0.50, 0.16, 0.99)
        bubble_border = NSColor.colorWithRed_green_blue_alpha_(1.00, 0.98, 0.94, 0.82)
    else:
        bubble_fill = NSColor.colorWithRed_green_blue_alpha_(0.56, 0.44, 0.12, 0.98)
        bubble_hover = NSColor.colorWithRed_green_blue_alpha_(0.72, 0.58, 0.18, 0.98)
        bubble_border = NSColor.colorWithRed_green_blue_alpha_(1.00, 0.99, 0.97, 0.92)

    return {
        "idle_fill": bubble_fill,
        "idle_border": bubble_border,
        "hover_fill": bubble_hover,
        "hover_border": bubble_border,
        "loading_fill": bubble_fill,
        "loading_border": bubble_border,
    }


class TriggerView(NSView):
    """A minimal circular trigger that starts translation on click."""

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
        trigger_size = _trigger_size(_config)

        if loading:
            palette = _trigger_palette()
            spinner_size = trigger_size * 0.5
            offset = (trigger_size - spinner_size) / 2
            self._spinner = NSProgressIndicator.alloc().initWithFrame_(
                NSMakeRect(offset, offset, spinner_size, spinner_size)
            )
            self._spinner.setStyle_(NSProgressIndicatorSpinningStyle)
            self._spinner.setControlSize_(NSControlSizeSmall)
            self._spinner.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameAqua"))
            self._spinner.setAlphaValue_(0.95)
            self._spinner.setIndeterminate_(True)
            self._spinner.setDisplayedWhenStopped_(False)
            self.addSubview_(self._spinner)
            self._spinner.startAnimation_(None)
        else:
            if self._spinner:
                self._spinner.stopAnimation_(None)
                self._spinner.removeFromSuperview()
                self._spinner = None

        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        palette = _trigger_palette()
        trigger_size = self.bounds().size.width
        outer_inset = 1.5 if self.hovered else 2.5
        outer_size = trigger_size - outer_inset * 2
        outer_rect = NSMakeRect(outer_inset, outer_inset, outer_size, outer_size)
        outer_path = NSBezierPath.bezierPathWithOvalInRect_(outer_rect)

        if self.loading:
            fill_color = palette["loading_fill"]
            border_color = palette["loading_border"]
        elif self.hovered:
            fill_color = palette["hover_fill"]
            border_color = palette["hover_border"]
        else:
            fill_color = palette["idle_fill"]
            border_color = palette["idle_border"]

        fill_color.setFill()
        outer_path.fill()
        border_color.setStroke()
        outer_path.setLineWidth_(1.2 if self.hovered else 1.0)
        outer_path.stroke()


def _trigger_size(config: SimpleNamespace | None) -> float:
    """Compress configured size into a smaller minimal affordance."""
    if config is None:
        return 16.0

    requested = float(getattr(config, "icon_size", 26))
    return max(14.0, min(requested * 0.46, 20.0))


def show(x: float, y: float, config: SimpleNamespace, on_click) -> None:
    """Show trigger icon near mouse position."""
    global _trigger_window, _trigger_timer, _on_click_callback, _config, _trigger_view
    dismiss()

    _config = config
    _on_click_callback = on_click
    icon_size = _trigger_size(config)

    screen = NSScreen.mainScreen()
    if not screen:
        return
    scr_h = screen.frame().size.height
    scr_w = screen.frame().size.width

    win_x = x + 1
    win_y = scr_h - y - icon_size - 1
    if win_x + icon_size > scr_w:
        win_x = x - icon_size - 1
    if win_y < 0:
        win_y = scr_h - y + 1

    frame = NSMakeRect(win_x, win_y, icon_size, icon_size)
    _trigger_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _trigger_window.setLevel_(NSFloatingWindowLevel + 1)
    _trigger_window.setOpaque_(False)
    _trigger_window.setBackgroundColor_(NSColor.clearColor())
    _trigger_window.setHasShadow_(False)
    _trigger_window.setIgnoresMouseEvents_(False)

    _trigger_view = TriggerView.alloc().initWithFrame_(NSMakeRect(0, 0, icon_size, icon_size))
    _trigger_window.contentView().addSubview_(_trigger_view)
    _trigger_window.orderFrontRegardless()

    _trigger_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        config.icon_dismiss_delay,
        NSApplication.sharedApplication().delegate(),
        "dismissTrigger:", None, False,
    )
    logger.debug("Trigger shown at (%d, %d)", int(x), int(y))


def show_loading() -> None:
    """Switch trigger icon to loading state."""
    global _trigger_timer
    if _trigger_view:
        _trigger_view.setLoading_(True)
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
