# -*- coding: utf-8 -*-
"""
کامپوننت‌های ورودی سیستم طراحی وینا

- ModernTextField: فیلد متنی گرد با پس‌زمینه‌ی سطح و حاشیه‌ی فوکوس متحرک
- SearchField: نسخه‌ی مخصوص جستجو با آیکون ذره‌بین
- PasswordField: نسخه‌ی مخفی‌سازی رمز عبور
- ChatInput: ورودی چند خطی مخصوص نوار پیام (با دکمه‌ی ارسال داخلی نیست؛
  دکمه‌ها در کنار آن در صفحه‌ی چت قرار می‌گیرند)
"""

from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Line, RoundedRectangle

from src.design_system.base import ThemedWidgetMixin, theme


class ModernTextField(TextInput, ThemedWidgetMixin):
    """فیلد ورودی متنی گرد با حاشیه‌ی فوکوس متحرک، هماهنگ با تم"""

    is_focused_visual = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.field_radius = dp(14)
        kwargs.setdefault('multiline', False)
        kwargs.setdefault('padding', [dp(16), dp(14), dp(16), dp(14)])
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('border', (0, 0, 0, 0))
        super().__init__(**kwargs)
        self.font_name = theme.font_name
        self.foreground_color = theme.text_primary
        self.hint_text_color = theme.text_disabled
        self.cursor_color = theme.accent

        with self.canvas.before:
            self._bg_color_instr = Color(*theme.bg_surface_alt)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.field_radius])
            self._border_color_instr = Color(0, 0, 0, 0)
            self._border_line = Line(
                rounded_rectangle=(*self.pos, *self.size, self.field_radius), width=1.4)

        self.bind(pos=self._redraw, size=self._redraw, focus=self._on_focus)
        self.bind_theme()

    def on_theme_changed(self):
        self.font_name = theme.font_name
        self.foreground_color = theme.text_primary
        self.hint_text_color = theme.text_disabled
        self.cursor_color = theme.accent
        self._redraw()

    def _redraw(self, *args):
        self._bg_color_instr.rgba = theme.bg_surface_alt
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [self.field_radius]
        self._border_line.rounded_rectangle = (*self.pos, *self.size, self.field_radius)

    def _on_focus(self, instance, value):
        target = theme.accent if value else (0, 0, 0, 0)
        Animation(rgba=target, duration=theme.get_anim_duration(theme.anim_fast)).start(
            self._border_color_instr)


class SearchField(ModernTextField):
    """فیلد جستجو (همان ModernTextField با hint پیش‌فرض جستجو)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('hint_text', 'جستجو...')
        super().__init__(**kwargs)


class PasswordField(ModernTextField):
    """فیلد رمز عبور (password=True پیش‌فرض)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('password', True)
        super().__init__(**kwargs)


class ChatInput(ModernTextField):
    """ورودی نوار پیام در صفحه‌ی چت - ارتفاع پویا بر اساس تعداد خطوط"""

    def __init__(self, **kwargs):
        self.max_height = dp(120)
        kwargs.setdefault('multiline', True)
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(44))
        super().__init__(**kwargs)
        self.bind(minimum_height=self._on_min_height)

    def _on_min_height(self, instance, value):
        self.height = min(self.max_height, max(dp(44), value))
