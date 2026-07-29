# -*- coding: utf-8 -*-
"""
کامپوننت‌های ناوبری سیستم طراحی وینا

- PageHeader: هدر استاندارد صفحات (دکمه‌ی بازگشت + عنوان + اکشن اختیاری)
- ModernBottomNavigation: نوار ناوبری پایین صفحه (خانه/چت/صدا/تنظیمات)
- TabButton: یک آیتم داخل نوار ناوبری
"""

from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

from src.design_system.base import ThemedWidgetMixin, theme
from src.design_system.components.buttons import IconButton


class PageHeader(BoxLayout, ThemedWidgetMixin):
    """هدر استاندارد صفحات داخلی (تنظیمات، مدل، حافظه و...)"""

    title_text = StringProperty('')

    def __init__(self, on_back=None, action_icon='', on_action=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(56))
        kwargs.setdefault('padding', [dp(8), dp(6), dp(8), dp(6)])
        kwargs.setdefault('spacing', dp(8))
        super().__init__(**kwargs)

        if on_back:
            back_btn = IconButton(text='→', font_size='18sp', size_hint=(None, None),
                                   size=(dp(40), dp(40)))
            back_btn.bind(on_release=lambda *a: on_back())
            self.add_widget(back_btn)

        self._title_label = Label(
            text=self.title_text, font_name=theme.font_name, bold=True,
            font_size='18sp', color=theme.text_primary,
        )
        self.add_widget(self._title_label)
        self.bind(title_text=lambda *a: setattr(self._title_label, 'text', self.title_text))

        if action_icon:
            action_btn = IconButton(text=action_icon, font_size='16sp', size_hint=(None, None),
                                     size=(dp(40), dp(40)))
            if callable(on_action):
                action_btn.bind(on_release=lambda *a: on_action())
            self.add_widget(action_btn)

    def on_theme_changed(self):
        self._title_label.color = theme.text_primary


class TabButton(Button, ThemedWidgetMixin):
    """یک آیتم داخل نوار ناوبری پایین (آیکون + برچسب کوچک)"""

    icon = StringProperty('')
    label_text = StringProperty('')
    is_selected = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = theme.font_name
        self.markup = True
        self._sync_text()
        self.bind_theme()

    def _sync_text(self):
        color_hex = self._color_hex()
        self.text = f"[color={color_hex}]{self.icon}\n[size=10]{self.label_text}[/size][/color]"

    def _color_hex(self):
        from src.design_system.base import rgba_to_hex
        return rgba_to_hex(theme.accent if self.is_selected else theme.text_disabled)

    def set_selected(self, selected):
        self.is_selected = selected
        self._sync_text()

    def on_theme_changed(self):
        self._sync_text()


class ModernBottomNavigation(BoxLayout, ThemedWidgetMixin):
    """نوار ناوبری پایین صفحه با ۴ مقصد اصلی: خانه، چت، صدا، تنظیمات"""

    def __init__(self, items=None, on_select=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(64))
        kwargs.setdefault('padding', [dp(8), dp(6), dp(8), dp(6)])
        super().__init__(**kwargs)
        self._on_select = on_select
        self._tabs = []

        with self.canvas.before:
            self._bg_color_instr = Color(*theme.bg_surface)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[0, 0, 0, 0])
            self._divider_color = Color(*theme.divider)
            from kivy.graphics import Line
            self._divider_line = Line(points=[self.x, self.top, self.right, self.top], width=1)
        self.bind(pos=self._redraw, size=self._redraw)

        for i, item in enumerate(items or []):
            tab = TabButton(icon=item.get('icon', ''), label_text=item.get('label', ''))
            tab.bind(on_release=lambda inst, idx=i: self._select(idx))
            self._tabs.append(tab)
            self.add_widget(tab)

        if self._tabs:
            self._tabs[0].set_selected(True)

        self.bind_theme()

    def on_theme_changed(self):
        self._redraw()

    def _redraw(self, *args):
        self._bg_color_instr.rgba = theme.bg_surface
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._divider_color.rgba = theme.divider
        self._divider_line.points = [self.x, self.top, self.right, self.top]

    def _select(self, index):
        for i, tab in enumerate(self._tabs):
            tab.set_selected(i == index)
        if callable(self._on_select):
            self._on_select(index)

    def select_index(self, index):
        self._select(index)
