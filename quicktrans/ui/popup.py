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
    NSView,
    NSFont,
    NSWindow,
    NSTimer,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSFloatingWindowLevel,
    NSMakeRect,
    NSMutableParagraphStyle,
    NSAttributedString,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSParagraphStyleAttributeName,
    NSBezierPath,
    NSTrackingArea,
    NSTrackingMouseEnteredAndExited,
    NSTrackingActiveAlways,
    NSCursor,
)
from Foundation import NSObject

from quicktrans import clipboard as cb

logger = logging.getLogger("quicktrans")

_popup_window = None
_popup_timer = None
_is_pinned = False
_translated_text = ""


def _is_dark_mode() -> bool:
    appearance = NSAppearance.currentAppearance()
    return "Dark" in (appearance.name() or "")


def _measure(text: str, font, max_w: float):
    tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, max_w, 2000))
    tv.setString_(text)
    tv.setFont_(font)
    tv.setEditable_(False)
    tv.setDrawsBackground_(False)
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    tv.textContainer().setWidthTracksTextView_(True)
    tv.layoutManager().ensureLayoutForTextContainer_(tv.textContainer())
    used = tv.layoutManager().usedRectForTextContainer_(tv.textContainer())
    return min(max_w, used.size.width), used.size.height


class _PopupBackground(NSView):
    """Custom drawn background with rounded corners and shadow."""

    _bg_color = None
    _border_color = None

    def initWithFrame_bgColor_borderColor_(self, frame, bg_color, border_color):
        self = objc.super(_PopupBackground, self).initWithFrame_(frame)
        if self is None:
            return None
        self._bg_color = bg_color
        self._border_color = border_color
        return self

    def isOpaque(self):
        return False

    def drawRect_(self, rect):
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            self.bounds(), 14, 14
        )
        self._bg_color.setFill()
        path.fill()
        self._border_color.setStroke()
        path.setLineWidth_(0.75)
        path.stroke()


class _PillButton(NSView):
    """Lightweight pill-shaped button drawn with NSBezierPath."""

    _title = ""
    _normal_color = None
    _hover_color = None
    _text_color = None
    _hovered = False
    _action = None
    _target = None

    def initWithFrame_title_normalColor_hoverColor_textColor_(
        self, frame, title, normal_color, hover_color, text_color
    ):
        self = objc.super(_PillButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self._title = title
        self._normal_color = normal_color
        self._hover_color = hover_color
        self._text_color = text_color
        return self

    def awakeFromNib(self):
        self._setup_tracking()

    def viewDidMoveToWindow(self):
        self._setup_tracking()

    def _setup_tracking(self):
        for ta in self.trackingAreas():
            self.removeTrackingArea_(ta)
        ta = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(),
            NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways,
            self, None,
        )
        self.addTrackingArea_(ta)

    def isOpaque(self):
        return False

    def acceptsFirstMouse_(self, event):
        return True

    def resetCursorRects(self):
        self.addCursorRect_cursor_(self.bounds(), NSCursor.pointingHandCursor())

    def mouseEntered_(self, event):
        self._hovered = True
        self.setNeedsDisplay_(True)

    def mouseExited_(self, event):
        self._hovered = False
        self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        if self._action and self._target:
            getattr(self._target, self._action)(self)

    def setTitle_(self, title):
        self._title = title
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        b = self.bounds()
        color = self._hover_color if self._hovered else self._normal_color
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(b, 6, 6)
        color.setFill()
        path.fill()

        font = NSFont.systemFontOfSize_(11)
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: self._text_color,
        }
        s = NSAttributedString.alloc().initWithString_attributes_(self._title, attrs)
        sw = s.size().width
        sh = s.size().height
        s.drawInRect_(NSMakeRect(
            (b.size.width - sw) / 2,
            (b.size.height - sh) / 2,
            sw, sh,
        ))


class _CopyAction(NSObject):
    def doCopy_(self, sender):
        cb.set_clipboard(_translated_text)
        sender.setTitle_("已复制")
        logger.debug("Translation copied.")


class _PinAction(NSObject):
    def doPin_(self, sender):
        global _is_pinned, _popup_timer
        _is_pinned = not _is_pinned
        sender.setTitle_("取消" if _is_pinned else "固定")
        if _is_pinned and _popup_timer:
            _popup_timer.invalidate()
            _popup_timer = None
        logger.debug("Popup %s", "pinned" if _is_pinned else "unpinned")


def show(translated: str, x: float, y: float, config: SimpleNamespace) -> None:
    """Show a floating popup with translated text."""
    global _popup_window, _popup_timer, _is_pinned, _translated_text
    dismiss()
    _is_pinned = False
    _translated_text = translated

    is_dark = _is_dark_mode()

    font = NSFont.systemFontOfSize_(config.font_size)
    padding = 20
    max_w = 460
    content_w = max_w - padding * 2
    btn_h = 26
    btn_bar_h = btn_h + 14

    if is_dark:
        bg_color      = NSColor.colorWithRed_green_blue_alpha_(0.13, 0.13, 0.15, 0.96)
        border_color  = NSColor.colorWithRed_green_blue_alpha_(1.0,  1.0,  1.0,  0.10)
        text_color    = NSColor.colorWithRed_green_blue_alpha_(0.92, 0.92, 0.92, 1.0)
        btn_normal    = NSColor.colorWithRed_green_blue_alpha_(0.26, 0.26, 0.30, 1.0)
        btn_hover     = NSColor.colorWithRed_green_blue_alpha_(0.36, 0.36, 0.42, 1.0)
        btn_text      = NSColor.colorWithRed_green_blue_alpha_(0.78, 0.78, 0.78, 1.0)
    else:
        bg_color      = NSColor.colorWithRed_green_blue_alpha_(0.98, 0.98, 1.00, 0.96)
        border_color  = NSColor.colorWithRed_green_blue_alpha_(0.0,  0.0,  0.0,  0.09)
        text_color    = NSColor.colorWithRed_green_blue_alpha_(0.12, 0.12, 0.14, 1.0)
        btn_normal    = NSColor.colorWithRed_green_blue_alpha_(0.88, 0.88, 0.92, 1.0)
        btn_hover     = NSColor.colorWithRed_green_blue_alpha_(0.78, 0.78, 0.86, 1.0)
        btn_text      = NSColor.colorWithRed_green_blue_alpha_(0.30, 0.30, 0.36, 1.0)

    # Line spacing
    para_style = NSMutableParagraphStyle.alloc().init()
    para_style.setLineHeightMultiple_(1.35)
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: text_color,
        NSParagraphStyleAttributeName: para_style,
    }
    attr_str = NSAttributedString.alloc().initWithString_attributes_(translated, attrs)

    text_w, text_h = _measure(translated, font, content_w)
    text_h = text_h * 1.35

    win_w = text_w + padding * 2 + 4
    # Clamp between a min width and max
    win_w = max(200, min(max_w, win_w))
    win_h = text_h + padding * 2 + btn_bar_h

    # Position near mouse
    screen = NSScreen.mainScreen()
    if screen:
        scr_h = screen.frame().size.height
        scr_w = screen.frame().size.width
        win_x = x + 14
        win_y = scr_h - y - win_h - 10
        if win_x + win_w > scr_w:
            win_x = x - win_w - 14
        if win_y < 0:
            win_y = scr_h - y + 14
    else:
        win_x, win_y = x + 14, y + 14

    frame = NSMakeRect(win_x, win_y, win_w, win_h)
    _popup_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _popup_window.setLevel_(NSFloatingWindowLevel)
    _popup_window.setOpaque_(False)
    _popup_window.setBackgroundColor_(NSColor.clearColor())
    _popup_window.setHasShadow_(True)
    _popup_window.setMovableByWindowBackground_(True)

    # Custom drawn background
    bg_view = _PopupBackground.alloc().initWithFrame_bgColor_borderColor_(
        NSMakeRect(0, 0, win_w, win_h), bg_color, border_color
    )
    _popup_window.setContentView_(bg_view)

    # Text
    tv = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, padding + btn_bar_h, win_w - padding * 2, text_h + 4)
    )
    tv.textStorage().setAttributedString_(attr_str)
    tv.setEditable_(False)
    tv.setSelectable_(True)
    tv.setDrawsBackground_(False)
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    bg_view.addSubview_(tv)

    # Copy button
    copy_action = _CopyAction.alloc().init()
    copy_btn = _PillButton.alloc().initWithFrame_title_normalColor_hoverColor_textColor_(
        NSMakeRect(padding, padding, 60, btn_h), "复制", btn_normal, btn_hover, btn_text
    )
    copy_btn._action = "doCopy_"
    copy_btn._target = copy_action
    bg_view.addSubview_(copy_btn)

    # Pin button
    pin_action = _PinAction.alloc().init()
    pin_btn = _PillButton.alloc().initWithFrame_title_normalColor_hoverColor_textColor_(
        NSMakeRect(padding + 68, padding, 60, btn_h), "固定", btn_normal, btn_hover, btn_text
    )
    pin_btn._action = "doPin_"
    pin_btn._target = pin_action
    bg_view.addSubview_(pin_btn)

    _popup_window.orderFrontRegardless()

    duration = max(5.0, config.popup_duration * 0.5 + len(translated) / 50.0)
    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        duration,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )
    logger.debug("Popup shown at (%d, %d)", int(x), int(y))


def show_error(message: str, x: float, y: float, config: SimpleNamespace) -> None:
    """Show a floating error popup."""
    global _popup_window, _popup_timer, _is_pinned
    dismiss()
    _is_pinned = False

    font = NSFont.systemFontOfSize_(config.font_size - 2)
    padding = 16
    text_w, text_h = _measure(message, font, 320)
    win_w = min(360, text_w + padding * 2 + 4)
    win_h = text_h + padding * 2

    screen = NSScreen.mainScreen()
    if screen:
        scr_h = screen.frame().size.height
        scr_w = screen.frame().size.width
        win_x = x + 14
        win_y = scr_h - y - win_h - 10
        if win_x + win_w > scr_w:
            win_x = x - win_w - 14
        if win_y < 0:
            win_y = scr_h - y + 14
    else:
        win_x, win_y = x + 14, y + 14

    frame = NSMakeRect(win_x, win_y, win_w, win_h)
    _popup_window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False,
    )
    _popup_window.setLevel_(NSFloatingWindowLevel)
    _popup_window.setOpaque_(False)
    _popup_window.setBackgroundColor_(NSColor.clearColor())
    _popup_window.setHasShadow_(True)
    _popup_window.setMovableByWindowBackground_(True)

    bg_color     = NSColor.colorWithRed_green_blue_alpha_(1.0, 0.94, 0.94, 0.97)
    border_color = NSColor.colorWithRed_green_blue_alpha_(0.85, 0.2, 0.2, 0.25)
    bg_view = _PopupBackground.alloc().initWithFrame_bgColor_borderColor_(
        NSMakeRect(0, 0, win_w, win_h), bg_color, border_color
    )
    _popup_window.setContentView_(bg_view)

    tv = NSTextView.alloc().initWithFrame_(
        NSMakeRect(padding, padding, win_w - padding * 2, text_h + 4)
    )
    tv.setString_(message)
    tv.setFont_(font)
    tv.setEditable_(False)
    tv.setSelectable_(False)
    tv.setDrawsBackground_(False)
    tv.setTextColor_(NSColor.colorWithRed_green_blue_alpha_(0.72, 0.08, 0.08, 1.0))
    tv.setTextContainerInset_((0, 0))
    tv.textContainer().setLineFragmentPadding_(0)
    bg_view.addSubview_(tv)

    _popup_window.orderFrontRegardless()
    _popup_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        4.0,
        NSApplication.sharedApplication().delegate(),
        "dismissPopup:", None, False,
    )
    logger.debug("Error popup shown: %s", message)


def is_visible() -> bool:
    """Return True if popup is currently shown."""
    return _popup_window is not None


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
