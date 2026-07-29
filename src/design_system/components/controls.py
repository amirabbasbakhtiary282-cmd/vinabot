# -*- coding: utf-8 -*-
"""
کامپوننت‌های کنترل سیستم طراحی وینا

- ModernSwitch: سوییچ روشن/خاموش انیمیشنی
- ModernSlider: اسلایدر افقی با دستگیره‌ی گرد
- Dropdown: منوی کشویی ساده برای انتخاب از چند گزینه
- SegmentedControl: کنترل چندگزینه‌ای افقی (شبیه iOS segmented control)
"""

from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle

from src.design_system.base import ThemedWidgetMixin, theme


class ModernSwitch(Widget, ThemedWidgetMixin):
    """سوییچ روشن/خاموش با انیمیشن نرم لغزش دایره (همان AnimatedSwitch در تنظیمات)"""

    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(48), dp(26))
        with self.canvas:
            self._track_color = Color(*self._track_bg())
            self._track = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(13)])
            self._knob_color = Color(1, 1, 1, 1)
            self._knob = Ellipse(pos=self.pos, size=(dp(20), dp(20)))
        self.bind(pos=self._redraw, size=self._redraw, active=self._on_active_changed)
        self.bind(on_touch_down=self._on_touch)
        self._redraw()
        self.bind_theme()

    def _track_bg(self):
        return theme.accent if self.active else theme.bg_surface_alt

    def on_theme_changed(self):
        self._redraw()

    def _on_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.active = not self.active
            return True
        return False

    def _on_active_changed(self, *args):
        self._track_color.rgba = self._track_bg()
        target_x = self.x + self.width - dp(23) if self.active else self.x + dp(3)
        Animation(x=target_x, duration=theme.get_anim_duration(theme.anim_normal),
                  t='out_quad').start(_KnobProxy(self))

    def _redraw(self, *args):
        self._track.pos = self.pos
        self._track.size = self.size
        self._track_color.rgba = self._track_bg()
        knob_x = self.x + self.width - dp(23) if self.active else self.x + dp(3)
        self._knob.pos = (knob_x, self.y + dp(3))
        self._knob.size = (dp(20), dp(20))


class _KnobProxy:
    """پروکسی کوچک برای انیمیت کردن موقعیت دایره‌ی سوییچ با kivy.animation"""

    def __init__(self, switch):
        self._switch = switch

    @property
    def x(self):
        return self._switch._knob.pos[0]

    @x.setter
    def x(self, value):
        self._switch._knob.pos = (value, self._switch._knob.pos[1])


class ModernSlider(BoxLayout, ThemedWidgetMixin):
    """اسلایدر افقی ساده با ترک رنگی و دستگیره‌ی گرد، هماهنگ با تم"""

    value = NumericProperty(0.5)
    min_value = NumericProperty(0.0)
    max_value = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(32)
        self._dragging = False
        with self.canvas:
            self._track_bg_color = Color(*theme.bg_surface_alt)
            self._track_bg = RoundedRectangle(pos=self.pos, size=(self.width, dp(4)), radius=[dp(2)])
            self._track_fill_color = Color(*theme.accent)
            self._track_fill = RoundedRectangle(pos=self.pos, size=(0, dp(4)), radius=[dp(2)])
            self._knob_color = Color(*theme.accent)
            self._knob = Ellipse(pos=self.pos, size=(dp(18), dp(18)))
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw)
        self.bind_theme()

    def on_theme_changed(self):
        self._track_bg_color.rgba = theme.bg_surface_alt
        self._track_fill_color.rgba = theme.accent
        self._knob_color.rgba = theme.accent

    def _frac(self):
        span = (self.max_value - self.min_value) or 1
        return max(0.0, min(1.0, (self.value - self.min_value) / span))

    def _redraw(self, *args):
        track_y = self.center_y - dp(2)
        self._track_bg.pos = (self.x, track_y)
        self._track_bg.size = (self.width, dp(4))
        frac = self._frac()
        fill_w = self.width * frac
        self._track_fill.pos = (self.x, track_y)
        self._track_fill.size = (fill_w, dp(4))
        knob_x = self.x + fill_w - dp(9)
        self._knob.pos = (knob_x, self.center_y - dp(9))
        self._knob.size = (dp(18), dp(18))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._dragging = True
            self._update_value_from_touch(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._dragging:
            self._update_value_from_touch(touch)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._dragging:
            self._dragging = False
            return True
        return super().on_touch_up(touch)

    def _update_value_from_touch(self, touch):
        frac = max(0.0, min(1.0, (touch.x - self.x) / self.width))
        self.value = self.min_value + frac * (self.max_value - self.min_value)


class Dropdown(Button, ThemedWidgetMixin):
    """دکمه‌ای که با لمس، یک منوی کشویی از گزینه‌ها را باز می‌کند"""

    options = ListProperty([])
    selected = StringProperty('')

    def __init__(self, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = theme.font_name
        self.color = theme.text_primary
        self._on_select = on_select

        with self.canvas.before:
            self._bg_color_instr = Color(*theme.bg_surface_alt)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

        self.bind(pos=self._redraw, size=self._redraw)
        self.bind(on_release=self._open_dropdown)
        self._sync_text()
        self.bind_theme()

    def on_theme_changed(self):
        self._redraw()
        self.color = theme.text_primary

    def _redraw(self, *args):
        self._bg_color_instr.rgba = theme.bg_surface_alt
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _sync_text(self, *args):
        self.text = self.selected or (self.options[0] if self.options else '')

    def _open_dropdown(self, *args):
        dd = DropDown(auto_width=False, width=self.width)
        for option in self.options:
            btn = Button(
                text=option, size_hint_y=None, height=dp(42),
                background_normal='', background_color=theme.bg_surface_alt,
                color=theme.text_primary, font_name=theme.font_name,
            )
            btn.bind(on_release=lambda inst, opt=option: self._select(opt, dd))
            dd.add_widget(btn)
        dd.open(self)

    def _select(self, option, dropdown):
        self.selected = option
        self._sync_text()
        dropdown.dismiss()
        if callable(self._on_select):
            self._on_select(option)


class SegmentedControl(BoxLayout, ThemedWidgetMixin):
    """کنترل چندگزینه‌ای افقی (مثل iOS Segmented Control) - برای انتخاب سریع بین چند حالت"""

    options = ListProperty([])
    selected_index = NumericProperty(0)

    def __init__(self, on_change=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(40))
        kwargs.setdefault('spacing', dp(4))
        kwargs.setdefault('padding', [dp(4), dp(4), dp(4), dp(4)])
        super().__init__(**kwargs)
        self._on_change = on_change
        self._buttons = []

        with self.canvas.before:
            self._bg_color_instr = Color(*theme.bg_surface_alt)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._redraw_bg, size=self._redraw_bg)

        for i, option in enumerate(self.options):
            btn = Button(
                text=option, background_normal='', background_down='',
                background_color=(0, 0, 0, 0),
                color=theme.text_on_accent if i == self.selected_index else theme.text_secondary,
                font_name=theme.font_name, font_size='12.5sp', bold=(i == self.selected_index),
            )
            with btn.canvas.before:
                btn._seg_color = Color(*(theme.accent if i == self.selected_index else (0, 0, 0, 0)))
                btn._seg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            btn.bind(pos=self._make_seg_updater(btn), size=self._make_seg_updater(btn))
            btn.bind(on_release=lambda inst, idx=i: self._select(idx))
            self._buttons.append(btn)
            self.add_widget(btn)

        self.bind_theme()

    def on_theme_changed(self):
        self._redraw_bg()
        self._refresh_buttons()

    def _redraw_bg(self, *args):
        self._bg_color_instr.rgba = theme.bg_surface_alt
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _make_seg_updater(self, btn):
        def _update(*args):
            btn._seg_rect.pos = btn.pos
            btn._seg_rect.size = btn.size
        return _update

    def _select(self, index):
        self.selected_index = index
        self._refresh_buttons()
        if callable(self._on_change):
            self._on_change(index, self.options[index])

    def _refresh_buttons(self):
        for i, btn in enumerate(self._buttons):
            is_sel = (i == self.selected_index)
            btn._seg_color.rgba = theme.accent if is_sel else (0, 0, 0, 0)
            btn.color = theme.text_on_accent if is_sel else theme.text_secondary
            btn.bold = is_sel


# نام مستعار: طبق مستندات سیستم طراحی، سوییچ انیمیشنی «AnimatedSwitch» نامیده
# می‌شود؛ پیاده‌سازی واقعی همان ModernSwitch است (بدون تکرار کد).
AnimatedSwitch = ModernSwitch
