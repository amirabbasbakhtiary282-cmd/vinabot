# -*- coding: utf-8 -*-
"""
کامپوننت‌های دکمه‌ی سیستم طراحی وینا

- AnimatedButton: پایه‌ی مشترک همه‌ی دکمه‌ها (پس‌زمینه‌ی گرد + افکت Ripple)
- PrimaryButton / SecondaryButton / DangerButton: نسخه‌های معنایی
- IconButton: دکمه‌ی دایره‌ای برای آیکون‌ها (هدر، نوار ورودی)
- FloatingActionButton: دکمه‌ی شناور گرد (FAB) برای اکشن اصلی صفحه
"""

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, RoundedRectangle, BoxShadow
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, OptionProperty
from kivy.uix.button import Button

from src.design_system.base import ThemedWidgetMixin, theme
from src.design_system.tokens import ButtonHeight


class AnimatedButton(Button, ThemedWidgetMixin):
    """دکمه‌ی پایه با پس‌زمینه‌ی گرد، افکت موج (ripple) و انیمیشن فشردن نرم"""

    radius = NumericProperty(999)
    variant = OptionProperty('accent', options=['accent', 'surface', 'error', 'outline'])
    bg_color = ListProperty([0, 0, 0, 0])  # خالی = از variant گرفته می‌شود

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bold = True
        self.font_name = theme.font_name

        with self.canvas.before:
            self._bg_color_instr = Color(*self._resolve_bg())
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
            self._ripple_color = Color(1, 1, 1, 0)
            self._ripple_ellipse = Ellipse(pos=self.pos, size=(0, 0))

        if 'color' not in kwargs:
            self.color = self._resolve_text_color()

        self.bind(pos=self._redraw, size=self._redraw, bg_color=self._redraw,
                  variant=self._redraw, radius=self._redraw)
        self.bind(on_press=self._on_press)
        self.bind_theme()

    def _resolve_bg(self):
        if any(self.bg_color):
            return self.bg_color
        return {
            'accent': theme.accent,
            'surface': theme.bg_surface_alt,
            'error': theme.error,
            'outline': (0, 0, 0, 0),
        }[self.variant]

    def _resolve_text_color(self):
        if self.variant == 'accent':
            return theme.text_on_accent
        if self.variant == 'error':
            return theme.text_on_accent
        return theme.text_primary

    def on_theme_changed(self):
        self._redraw()
        self.color = self._resolve_text_color()
        self.font_name = theme.font_name

    def _redraw(self, *args):
        self._bg_color_instr.rgba = self._resolve_bg()
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [self.radius]

    def _on_press(self, instance):
        cx, cy = self.center
        max_dim = max(self.width, self.height) * 1.6
        self._ripple_ellipse.pos = (cx, cy)
        self._ripple_ellipse.size = (0, 0)
        self._ripple_color.rgba = (1, 1, 1, 0.22)

        duration = theme.get_anim_duration(theme.anim_slow)

        def update_ripple(dt, elapsed=[0.0]):
            elapsed[0] += dt
            t = min(1.0, elapsed[0] / duration)
            size = max_dim * t
            self._ripple_ellipse.pos = (cx - size / 2, cy - size / 2)
            self._ripple_ellipse.size = (size, size)
            self._ripple_color.a = 0.22 * (1 - t)
            return t < 1.0

        Clock.schedule_interval(update_ripple, 1 / 60)


class PrimaryButton(AnimatedButton):
    """دکمه‌ی اصلی (اکسنت) - برای اکشن‌های مهم مثل ورود/ارسال/تایید"""

    def __init__(self, **kwargs):
        kwargs.setdefault('variant', 'accent')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', ButtonHeight.MD)
        super().__init__(**kwargs)


class SecondaryButton(AnimatedButton):
    """دکمه‌ی ثانویه (خنثی) - برای اکشن‌های کم‌اهمیت‌تر"""

    def __init__(self, **kwargs):
        kwargs.setdefault('variant', 'surface')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', ButtonHeight.MD)
        super().__init__(**kwargs)


class DangerButton(AnimatedButton):
    """دکمه‌ی خطر (قرمز) - برای حذف/پاک کردن داده"""

    def __init__(self, **kwargs):
        kwargs.setdefault('variant', 'error')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', ButtonHeight.MD)
        super().__init__(**kwargs)


class IconButton(Button, ThemedWidgetMixin):
    """دکمه‌ی دایره‌ای کوچک با پس‌زمینه‌ی شیشه‌ای، برای آیکون‌های هدر"""

    bg_color = ListProperty([0, 0, 0, 0])  # خالی = glass_fill

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.font_name = theme.font_name
        if 'color' not in kwargs:
            self.color = theme.text_primary

        with self.canvas.before:
            self._bg_color_instr = Color(*self._resolve_bg())
            self._bg_ellipse = Ellipse(pos=self.pos, size=self.size)

        self.bind(pos=self._redraw, size=self._redraw, bg_color=self._redraw)
        self.bind(on_press=self._on_press, on_release=self._on_release)
        self.bind_theme()

    def _resolve_bg(self):
        return self.bg_color if any(self.bg_color) else theme.glass_fill

    def on_theme_changed(self):
        self._redraw()
        self.color = theme.text_primary

    def _redraw(self, *args):
        self._bg_color_instr.rgba = self._resolve_bg()
        self._bg_ellipse.pos = self.pos
        self._bg_ellipse.size = self.size

    def _on_press(self, instance):
        Animation.cancel_all(instance, 'bg_color')
        base = self._resolve_bg()
        brighter = [min(1, c + 0.08) for c in base[:3]] + [min(1, base[3] + 0.1)]
        Animation(bg_color=brighter, duration=theme.get_anim_duration(theme.anim_fast)).start(instance)

    def _on_release(self, instance):
        Animation.cancel_all(instance, 'bg_color')
        Animation(bg_color=list(self._resolve_bg()),
                  duration=theme.get_anim_duration(theme.anim_normal)).start(instance)


class FloatingActionButton(IconButton):
    """دکمه‌ی شناور گرد (FAB) برای اکشن اصلی یک صفحه (مثل شروع مکالمه‌ی جدید)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (dp(58), dp(58)))
        kwargs.setdefault('font_size', '22sp')
        super().__init__(**kwargs)
        with self.canvas.before:
            pass
        self._shadow_color = Color(*theme.shadow)
        self._shadow = BoxShadow(
            pos=self.pos, size=self.size, offset=(0, -3),
            blur_radius=18, spread_radius=(-2, -2), border_radius=(999, 999, 999, 999),
        )
        self.canvas.before.insert(0, self._shadow)
        self.canvas.before.insert(0, self._shadow_color)
        self.bind(pos=self._update_shadow, size=self._update_shadow)

    def _update_shadow(self, *args):
        self._shadow.pos = (self.x, self.y - 2)
        self._shadow.size = self.size

    def _resolve_bg(self):
        return theme.accent

    def on_theme_changed(self):
        super().on_theme_changed()
        self._shadow_color.rgba = theme.shadow
        self.color = theme.text_on_accent
