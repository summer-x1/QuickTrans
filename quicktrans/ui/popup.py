"""Translation result popup window with copy button and original text."""

import logging
from types import SimpleNamespace

import objc
from AppKit import (
    NSApplication,
    NSWindow,
    NSTextView,
    NSButton,
    NSFont,
    NSColor,
    NSScreen,
    NSTimer,
    NSView,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSBezierPath,
    NSBezelStyleSmallSquare,
)

from quicktrans import clipboard as cb

logger = logging.getLogger("quicktrans")

# Module-level state
_popup_window = None
_popup_timer = None
_is_pinned = False


class _CopyButton(NSButton):
    """Copy button that copies translated text to clipboard."""

    _translated_text = ""

    def initWithFrame_text_(self, frame, text):
        self = objc.super(_CopyButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self._translated_text = text
        self.setTitle_("Copy")
        self.setBezelStyle_(NSBezelStyleSmallSquare)
        self.setFont_(NSFont.systemFontOfSize_(11))
        self.setTarget_(self)
        self.setAction_("doCopy:")
        return self

    def doCopy_(self, sender):
        cb.set_clipboard(self._translated_text)
        self.setTitle_("Copied!")
        logger.debug("Translation copied to clipboard.")


class _PinButton(NSButton):
    """Pin/unpin button to keep popup visible."""

    def initWithFrame_(self, frame):
        self = objc.super(_PinButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self.setTitle_("Pin")
        self.setBezelStyle_(NSBezelStyleSmallSquare)
        self.setFont_(NSFont.systemFontOfSize_(11))
        self.setTarget_(self)
        self.setAction_("doPin:")
        return self

    def doPin_(self, sender):
        global _is_pinned, _popup_timer
        _is_pinned = not _is_pinned
        self.setTitle_("Unpin" if _is_pinned else "Pin")
        if _is_pinned and _popup_timer:
            _popup_timer.invalidate()
            _popup_timer = None
        logger.debug("Popup %s", "pinned" if _is_pinned else "unpinned")


def _measure_text(text: str, font, max_width: float):
    """Measure text height and width for given font and max width."""
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
    return used.size.width, used.size.height


def show(translated: str, x: float, y: float, config: SimpleNamespace,
         original: str = "") -> None:
    """Show a floating popup with original and translated text."""
    global _popup_window, _popup_timer, _is_pinned
    dismiss()
    _is_pinned = False

    padding = 16
    max_w = 480
    content_w = max_w - padding * 2
    btn_h = 22
    btn_bar_h = btn_h + 8

    main_font = NSFont.systemFontOfSize_(config.font_size)
    orig_font = NSFont.systemFontOfSize_(config.font_size - 3)

    # Measure translated text
    trans_w, trans_h = _measure_text(translated, main_font, content_w)

    # Measure original text (if provided)
    orig_h = 0
    separator_h = 0
    if original:
        _, orig_h = _measure_text(original, orig_font, content_w)
        separator_h = 12  # spacing + line

    text_w = min(content_w, max(trans_w, 100))
    win_w = text_w + padding * 2 + 4
    win_h = padding + orig_h + separator_h + trans_h + btn_bar_h + padding

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
    cv.layer().setBackgroundColor_(NSColor.windowBackgroundColor().CGColor())

    y_cursor = padding  # Build from bottom up in AppKit coords

    # Button bar at bottom
    copy_btn = _CopyButton.alloc().initWithFrame_text_(
        NSMakeRect(padding, y_cursor, 50, btn_h), translated
    )
    cv.addSubview_(copy_btn)

    pin_btn = _PinButton.alloc().initWithFrame_(
        NSMakeRect(padding + 56, y_cursor, 50, btn_h)
    )
    cv.addSubview_(pin_btn)
    y_cursor += btn_bar_h

    # Translated text
    tv_trans = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, y_cursor, text_w + 4, trans_h + 4)
    )
    tv_trans.setString_(translated)
    tv_trans.setFont_(main_font)
    tv_trans.setEditable_(False)
    tv_trans.setSelectable_(True)
    tv_trans.setDrawsBackground_(False)
    tv_trans.setTextColor_(NSColor.labelColor())
    tv_trans.setTextContainerInset_((0, 0))
    tv_trans.textContainer().setLineFragmentPadding_(0)
    cv.addSubview_(tv_trans)
    y_cursor += trans_h + 4

    # Original text (if provided)
    if original:
        y_cursor += 4
        # Separator line
        sep = NSView.alloc().initWithFrame_(
            NSMakeRect(padding, y_cursor, text_w, 1)
        )
        sep.setWantsLayer_(True)
        sep.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        cv.addSubview_(sep)
        y_cursor += separator_h - 4

        tv_orig = NSTextView.alloc().initWithFrame_(
            NSMakeRect(padding, y_cursor, text_w + 4, orig_h + 4)
        )
        tv_orig.setString_(original)
        tv_orig.setFont_(orig_font)
        tv_orig.setEditable_(False)
        tv_orig.setSelectable_(True)
        tv_orig.setDrawsBackground_(False)
        tv_orig.setTextColor_(NSColor.secondaryLabelColor())
        tv_orig.setTextContainerInset_((0, 0))
        tv_orig.textContainer().setLineFragmentPadding_(0)
        cv.addSubview_(tv_orig)

    _popup_window.orderFrontRegardless()
    logger.debug("Popup shown at (%d, %d)", int(x), int(y))

    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        config.popup_duration,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )


def dismiss(_=None) -> None:
    """Dismiss the translation popup."""
    global _popup_window, _popup_timer, _is_pinned
    if _is_pinned:
        return  # Don't dismiss pinned popup
    if _popup_window:
        _popup_window.orderOut_(None)
        _popup_window = None
    if _popup_timer:
        _popup_timer.invalidate()
        _popup_timer = None
