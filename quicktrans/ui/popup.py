"""Translation result popup window with improved typography, dark mode, and rounded square."""

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
    NSTextField,
    NSWindow,
    NSView,
    NSTimer,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSParagraphStyle,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName,
)

from quicktrans import clipboard as cb

logger = logging.getLogger("quicktrans")

# Module-level state
_popup_window = None
_popup_timer = None
_is_pinned = False


def _measure_text(text: str, font: NSFont, max_width: float, line_height_mult: float = 1.5) -> tuple[float, float]:
    """Measure text height and width with line spacing."""
    tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, max_width, 1000))
    tv.setString_(text)
    tv.setFont_(font)
    tv.setEditable_(False)
    tv.setDrawsBackground_(False)
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    tv.textContainer().setWidthTracksTextView_(True)
    tv.layoutManager().ensureLayoutForTextContainer_(tv.textContainer())
    used = tv.layoutManager().usedRectForTextContainer_(tv.textContainer())

    line_height = used.size.height * line_height_mult

    return min(max_width, used.size.width), line_height


def show(translated: str, x: float, y: float, config: SimpleNamespace) -> None:
    """Show a floating popup with translated text."""
    global _popup_window, _popup_timer, _is_pinned
    dismiss()
    _is_pinned = False

    # Typography configuration
    font_size = config.font_size - 1  # User wants smaller
    main_font = NSFont.systemFontOfSize_(font_size)
    body_font = NSFont.systemFontOfSize_(font_size - 2)

    padding = 20
    max_w = 500
    btn_h = 24
    btn_bar_h = btn_h + 8

    # Dark mode
    appearance = NSAppearance.currentAppearance()
    is_dark = appearance.name() == "NSAppearanceNameDarkAqua"

    if is_dark:
        bg_color = NSColor.windowBackgroundColor()
        text_color = NSColor.labelColor()
        btn_bg_color = NSColor.controlAccentColor()
    else:
        bg_color = NSColor.windowBackgroundColor()
        text_color = NSColor.labelColor()
        btn_bg_color = NSColor.controlAccentColor()

    # Measure translated text
    trans_w, trans_h = _measure_text(translated, main_font, max_w)

    win_w = trans_w + padding * 2 + 4
    win_h = padding + trans_h + btn_bar_h + padding

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

    # Round square window
    corner_radius = 10
    frame = NSMakeRect(win_x, win_y, win_w, win_h)
    _popup_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _popup_window.setLevel_(NSFloatingWindowLevel)
    _popup_window.setOpaque_(False)
    _popup_window.setHasShadow_(True)
    _popup_window.setAlphaValue_(0.96)
    _popup_window.setMovableByWindowBackground_(True)
    _popup_window.setWantsLayer_(True)
    _popup_window.layer().setCornerRadius_(corner_radius)

    cv = _popup_window.contentView()
    cv.setWantsLayer_(True)
    cv.layer().setMasksToBounds_(True)
    cv.layer().setBackgroundColor_(bg_color.CGColor())

    y_cursor = padding

    # Title (using translated text)
    title_lbl = NSTextField.alloc().initWithFrame_(
        NSMakeRect(padding, y_cursor, win_w - padding * 2, btn_h)
    )
    title_lbl.setString_(translated)
    title_lbl.setFont_(main_font)
    title_lbl.setTextColor_(text_color)
    title_lbl.setBordered_(False)
    title_lbl.setEditable_(False)
    title_lbl.setSelectable_(False)
    title_lbl.setDrawsBackground_(False)
    title_lbl.setAlignment_(NSTextAlignmentNatural)
    cv.addSubview_(title_lbl)
    y_cursor += btn_h

    # Translated text
    tv_trans = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, y_cursor, win_w - padding * 2, win_h - btn_bar_h - padding)
    )
    tv_trans.setString_(translated)
    tv_trans.setFont_(body_font)
    tv_trans.setEditable_(False)
    tv_trans.setSelectable_(True)
    tv_trans.setDrawsBackground_(False)
    tv_trans.setTextColor_(text_color)
    tv_trans.setTextContainerInset_((0, 0))
    tv_trans.textContainer().setLineFragmentPadding_(0)
    tv_trans.textContainer().setWidthTracksTextView_(True)
    tv_trans.layoutManager().ensureLayoutForTextContainer_(tv_trans.textContainer())
    cv.addSubview_(tv_trans)
    y_cursor += trans_h - btn_bar_h - padding

    # Copy button
    copy_btn = NSButton.alloc().initWithBezelStyleTarget_(
        NSMakeRect(padding, y_cursor, 80, btn_h)
    )
    copy_btn.setBezelStyle_(NSBezelStyleSmallSquare)
    copy_btn.setTitle_("复制译文")
    copy_btn.setFont_(NSFont.systemFontOfSize_(12))
    copy_btn.setTarget_(self)
    copy_btn.setAction_("doCopy:")
    cv.addSubview_(copy_btn)

    # Pin button
    pin_btn = NSButton.alloc().initWithBezelStyleTarget_(
        NSMakeRect(padding + 88, y_cursor, 60, btn_h)
    )
    pin_btn.setBezelStyle_(NSBezelStyleSmallSquare)
    pin_btn.setTitle_("固定")
    pin_btn.setFont_(NSFont.systemFontOfSize_(12))
    pin_btn.setTarget_(self)
    pin_btn.setAction_("doPin:")
    cv.addSubview_(pin_btn)

    _popup_window.orderFrontRegardless()

    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        config.popup_duration,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )
    logger.debug("Popup shown at (%d, %d)", int(x), int(y))


def dismiss(_=None) -> None:
    """Dismiss translation popup."""
    global _popup_window, _popup_timer, _is_pinned
    if _is_pinned:
        return
    if _popup_window:
        _popup_window.orderOut_(None)
        _popup_window = None
    if _popup_timer:
        _popup_timer.invalidate_()
        _popup_timer = None


class _CopyButton(NSButton):
    """Copy button that copies translated text to clipboard."""
    _copied = False

    def initWithFrame_(self, frame):
        self = objc.super(_CopyButton, self).initWithFrame_(frame)
        return self

    def doCopy_(self):
        cb.set_clipboard("翻译成功！")
        self.setTitle_("已复制")
        self._copied = True


class _PinButton(NSButton):
    """Pin/unpin button to keep popup visible."""

    def initWithFrame_(self, frame):
        self = objc.super(_PinButton, self).initWithFrame_(frame)
        return self

    def doPin_(self):
        global _is_pinned, _popup_timer
        _is_pinned = not _is_pinned
        if _is_pinned and _popup_timer:
            _popup_timer.invalidate()
            _popup_timer = None
        logger.debug("Popup pinned")


def doCopy_(self):
    """Called when copy button is clicked."""
    cb.set_clipboard("翻译成功！")
    logger.debug("Translation copied to clipboard.")
