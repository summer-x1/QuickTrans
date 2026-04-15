"""Translation result popup window."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import objc
from AppKit import (
    NSApplication,
    NSAppearance,
    NSColor,
    NSScreen,
    NSTextView,
    NSButton,
    NSBezelStyleSmallSquare,
    NSFont,
    NSWindow,
    NSTimer,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
)

from quicktrans import clipboard as cb

logger = logging.getLogger("quicktrans")

_popup_window = None
_popup_timer = None
_is_pinned = False
_translated_text = ""


def show(translated: str, x: float, y: float, config: SimpleNamespace) -> None:
    """Show a floating popup with translated text."""
    global _popup_window, _popup_timer, _is_pinned, _translated_text
    dismiss()
    _is_pinned = False
    _translated_text = translated

    font_size = config.font_size
    font = NSFont.systemFontOfSize_(font_size)
    padding = 18
    max_w = 480
    btn_h = 22
    btn_bar_h = btn_h + 10

    # Measure text
    tv_measure = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, max_w - padding * 2, 1000))
    tv_measure.setString_(translated)
    tv_measure.setFont_(font)
    tv_measure.setEditable_(False)
    tv_measure.setDrawsBackground_(False)
    tv_measure.setTextContainerInset_((0, 0))
    tv_measure.textContainer().setLineFragmentPadding_(0)
    tv_measure.textContainer().setWidthTracksTextView_(True)
    tv_measure.layoutManager().ensureLayoutForTextContainer_(tv_measure.textContainer())
    used = tv_measure.layoutManager().usedRectForTextContainer_(tv_measure.textContainer())
    text_h = used.size.height
    text_w = min(max_w - padding * 2, used.size.width)

    win_w = text_w + padding * 2 + 4
    win_h = text_h + padding * 2 + btn_bar_h

    # Position near mouse
    screen = NSScreen.mainScreen()
    if screen:
        scr_h = screen.frame().size.height
        scr_w = screen.frame().size.width
        win_x = x + 12
        win_y = scr_h - y - win_h - 8
        if win_x + win_w > scr_w:
            win_x = x - win_w - 12
        if win_y < 0:
            win_y = scr_h - y + 12
    else:
        win_x, win_y = x + 12, y + 12

    frame = NSMakeRect(win_x, win_y, win_w, win_h)
    _popup_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _popup_window.setLevel_(NSFloatingWindowLevel)
    _popup_window.setOpaque_(False)
    _popup_window.setHasShadow_(True)
    _popup_window.setAlphaValue_(0.96)
    _popup_window.setMovableByWindowBackground_(True)

    cv = _popup_window.contentView()
    cv.setWantsLayer_(True)
    cv.layer().setCornerRadius_(12)
    cv.layer().setMasksToBounds_(True)

    # Dark mode detection
    appearance = NSAppearance.currentAppearance()
    is_dark = "Dark" in (appearance.name() or "")
    if is_dark:
        bg_color = NSColor.colorWithRed_green_blue_alpha_(0.15, 0.15, 0.17, 1.0)
        text_color = NSColor.colorWithRed_green_blue_alpha_(0.92, 0.92, 0.92, 1.0)
    else:
        bg_color = NSColor.windowBackgroundColor()
        text_color = NSColor.labelColor()
    cv.layer().setBackgroundColor_(bg_color.CGColor())

    # Text view (bottom-up layout in AppKit)
    tv = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, padding + btn_bar_h, text_w + 4, text_h + 4)
    )
    tv.setString_(translated)
    tv.setFont_(font)
    tv.setEditable_(False)
    tv.setSelectable_(True)
    tv.setDrawsBackground_(False)
    tv.setTextColor_(text_color)
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    cv.addSubview_(tv)

    # Copy button
    copy_btn = _CopyButton.alloc().initWithFrame_(
        NSMakeRect(padding, padding, 70, btn_h)
    )
    copy_btn.setBezelStyle_(NSBezelStyleSmallSquare)
    copy_btn.setTitle_("复制")
    copy_btn.setFont_(NSFont.systemFontOfSize_(11))
    copy_btn.setTarget_(copy_btn)
    copy_btn.setAction_("doCopy:")
    cv.addSubview_(copy_btn)

    # Pin button
    pin_btn = _PinButton.alloc().initWithFrame_(
        NSMakeRect(padding + 76, padding, 60, btn_h)
    )
    pin_btn.setBezelStyle_(NSBezelStyleSmallSquare)
    pin_btn.setTitle_("固定")
    pin_btn.setFont_(NSFont.systemFontOfSize_(11))
    pin_btn.setTarget_(pin_btn)
    pin_btn.setAction_("doPin:")
    cv.addSubview_(pin_btn)

    _popup_window.orderFrontRegardless()

    # Dynamic duration: base 5s + 1s per 50 chars
    duration = max(5.0, config.popup_duration * 0.5 + len(translated) / 50.0)

    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        duration,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )
    logger.debug("Popup shown at (%d, %d)", int(x), int(y))


def show_error(message: str, x: float, y: float, config: SimpleNamespace) -> None:
    """Show a floating error popup with retry hint."""
    global _popup_window, _popup_timer, _is_pinned
    dismiss()
    _is_pinned = False

    font = NSFont.systemFontOfSize_(config.font_size - 2)
    padding = 18
    max_w = 360

    tv_measure = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, max_w - padding * 2, 1000))
    tv_measure.setString_(message)
    tv_measure.setFont_(font)
    tv_measure.setEditable_(False)
    tv_measure.setDrawsBackground_(False)
    tv_measure.setTextContainerInset_((0, 0))
    tv_measure.textContainer().setLineFragmentPadding_(0)
    tv_measure.textContainer().setWidthTracksTextView_(True)
    tv_measure.layoutManager().ensureLayoutForTextContainer_(tv_measure.textContainer())
    used = tv_measure.layoutManager().usedRectForTextContainer_(tv_measure.textContainer())
    text_h = used.size.height
    text_w = min(max_w - padding * 2, used.size.width)

    win_w = text_w + padding * 2 + 4
    win_h = text_h + padding * 2 + 12

    screen = NSScreen.mainScreen()
    if screen:
        scr_h = screen.frame().size.height
        scr_w = screen.frame().size.width
        win_x = x + 12
        win_y = scr_h - y - win_h - 8
        if win_x + win_w > scr_w:
            win_x = x - win_w - 12
        if win_y < 0:
            win_y = scr_h - y + 12
    else:
        win_x, win_y = x + 12, y + 12

    frame = NSMakeRect(win_x, win_y, win_w, win_h)
    _popup_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _popup_window.setLevel_(NSFloatingWindowLevel)
    _popup_window.setOpaque_(False)
    _popup_window.setHasShadow_(True)
    _popup_window.setAlphaValue_(0.96)
    _popup_window.setMovableByWindowBackground_(True)

    cv = _popup_window.contentView()
    cv.setWantsLayer_(True)
    cv.layer().setCornerRadius_(12)
    cv.layer().setMasksToBounds_(True)
    # Red-tinted background for error
    cv.layer().setBackgroundColor_(NSColor.colorWithRed_green_blue_alpha_(0.98, 0.95, 0.95, 1.0).CGColor())

    tv = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, padding, text_w + 4, text_h + 4)
    )
    tv.setString_(message)
    tv.setFont_(font)
    tv.setEditable_(False)
    tv.setSelectable_(False)
    tv.setDrawsBackground_(False)
    tv.setTextColor_(NSColor.colorWithRed_green_blue_alpha_(0.8, 0.1, 0.1, 1.0))
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    cv.addSubview_(tv)

    _popup_window.orderFrontRegardless()

    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        4.0,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )
    logger.debug("Error popup shown: %s", message)


def dismiss(_=None) -> None:
    """Dismiss the translation popup."""
    global _popup_window, _popup_timer, _is_pinned
    if _is_pinned:
        return
    if _popup_window:
        _popup_window.orderOut_(None)
        _popup_window = None
    if _popup_timer:
        _popup_timer.invalidate()
        _popup_timer = None


class _CopyButton(NSButton):
    """Copies translated text to clipboard."""

    def initWithFrame_(self, frame):
        self = objc.super(_CopyButton, self).initWithFrame_(frame)
        return self

    def doCopy_(self, sender):
        cb.set_clipboard(_translated_text)
        self.setTitle_("已复制")
        logger.debug("Translation copied to clipboard.")


class _PinButton(NSButton):
    """Pin/unpin to keep popup visible."""

    def initWithFrame_(self, frame):
        self = objc.super(_PinButton, self).initWithFrame_(frame)
        return self

    def doPin_(self, sender):
        global _is_pinned, _popup_timer
        _is_pinned = not _is_pinned
        self.setTitle_("取消" if _is_pinned else "固定")
        if _is_pinned and _popup_timer:
            _popup_timer.invalidate()
            _popup_timer = None
        logger.debug("Popup %s", "pinned" if _is_pinned else "unpinned")
