# -*- coding: utf-8 -*-
"""
کامپوننت‌های بازخورد (Feedback) سیستم طراحی وینا

- Snackbar: پیام کوتاه پایین صفحه با دکمه‌ی اختیاری (Undo و...)
- Toast: پیام بسیار کوتاه بدون دکمه که خودکار محو می‌شود
- LoadingOverlay: پوشش تمام‌صفحه با اسپینر برای عملیات طولانی
- EmptyState / ErrorState / SuccessState: حالت‌های نمایشی خالی/خطا/موفقیت
"""

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from src.design_system.base import theme
from src.design_system.components.cards import GlassCard
from src.design_system.components.loaders import LoadingSpinner


class Snackbar(GlassCard):
    """پیام کوتاه در پایین صفحه؛ با ``show()`` روی هر FloatLayout نمایش داده می‌شود"""

    def __init__(self, text='', action_text='', on_action=None, duration=3.0, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint', (0.92, None))
        kwargs.setdefault('height', dp(52))
        kwargs.setdefault('padding', [dp(16), dp(8), dp(10), dp(8)])
        kwargs.setdefault('radius', 14)
        kwargs.setdefault('surface', 'elevated')
        super().__init__(**kwargs)
        self._duration = duration

        label = Label(text=text, font_name=theme.font_name, font_size='13sp',
                      color=theme.text_primary, halign='right')
        label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.add_widget(label)

        if action_text:
            from src.design_system.components.buttons import SecondaryButton
            btn = SecondaryButton(text=action_text, size_hint_x=None, width=dp(80))
            if callable(on_action):
                btn.bind(on_release=lambda *a: on_action())
            self.add_widget(btn)

    def show(self, parent_float_layout, anchor_bottom=None):
        if anchor_bottom is None:
            anchor_bottom = dp(24)
        self.pos_hint = {'center_x': 0.5}
        self.y = -self.height
        parent_float_layout.add_widget(self)
        target_y = anchor_bottom
        anim = Animation(y=target_y, duration=theme.get_anim_duration(theme.anim_normal), t='out_cubic')
        anim.start(self)
        Clock.schedule_once(lambda dt: self._auto_dismiss(parent_float_layout), self._duration)

    def _auto_dismiss(self, parent_float_layout):
        anim = Animation(y=-self.height, duration=theme.get_anim_duration(theme.anim_normal), t='in_cubic')
        anim.bind(on_complete=lambda *a: parent_float_layout.remove_widget(self))
        anim.start(self)


class Toast(Label):
    """پیام بسیار کوتاه که خودش را بعد از مدتی محو و حذف می‌کند"""

    def __init__(self, text='', duration=1.6, **kwargs):
        kwargs.setdefault('font_name', theme.font_name)
        kwargs.setdefault('font_size', '12.5sp')
        kwargs.setdefault('color', theme.text_primary)
        kwargs.setdefault('size_hint', (None, None))
        super().__init__(text=text, **kwargs)
        self.texture_update()
        self.size = (self.texture_size[0] + dp(24), dp(36))
        with self.canvas.before:
            from kivy.graphics import RoundedRectangle
            Color(*theme.bg_elevated)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_bg, size=self._update_bg)
        self._duration = duration

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def show(self, parent_float_layout):
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.opacity = 0
        parent_float_layout.add_widget(self)
        Animation(opacity=1, duration=0.15).start(self)
        Clock.schedule_once(lambda dt: self._fade_out(parent_float_layout), self._duration)

    def _fade_out(self, parent_float_layout):
        anim = Animation(opacity=0, duration=0.25)
        anim.bind(on_complete=lambda *a: parent_float_layout.remove_widget(self))
        anim.start(self)


class LoadingOverlay(Widget):
    """پوشش تمام‌صفحه با اسپینر، برای عملیات طولانی (بارگذاری مدل، دانلود و...)"""

    def __init__(self, message='', **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(0, 0, 0, 0.55)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        self._spinner = LoadingSpinner(size_hint=(None, None), size=(dp(48), dp(48)))
        self.add_widget(self._spinner)

        if message:
            self._label = Label(
                text=message, font_name=theme.font_name, font_size='13sp',
                color=theme.text_primary, size_hint=(None, None),
            )
            self.add_widget(self._label)
        else:
            self._label = None

        self.bind(pos=self._layout_children, size=self._layout_children)

    def _redraw(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _layout_children(self, *args):
        self._spinner.center = (self.center_x, self.center_y + (dp(16) if self._label else 0))
        if self._label:
            self._label.texture_update()
            self._label.size = self._label.texture_size
            self._label.center = (self.center_x, self.center_y - dp(20))


class _StateBase(BoxLayout):
    """پایه‌ی مشترک EmptyState/ErrorState/SuccessState"""

    def __init__(self, icon='', title='', description='', action_widget=None, icon_color=None, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('spacing', dp(10))
        kwargs.setdefault('padding', [dp(24), dp(24), dp(24), dp(24)])
        super().__init__(**kwargs)

        self.add_widget(Widget(size_hint_y=0.15))

        self._icon_label = Label(
            text=icon, font_size='48sp', color=icon_color or theme.text_disabled,
            size_hint_y=None, height=dp(64),
        )
        self.add_widget(self._icon_label)

        self._title_label = Label(
            text=title, font_name=theme.font_name, bold=True, font_size='16sp',
            color=theme.text_primary, size_hint_y=None, height=dp(28),
        )
        self.add_widget(self._title_label)

        if description:
            self._desc_label = Label(
                text=description, font_name=theme.font_name, font_size='12.5sp',
                color=theme.text_secondary, halign='center', size_hint_y=None,
            )
            self._desc_label.bind(width=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
            self._desc_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            self.add_widget(self._desc_label)

        if action_widget:
            self.add_widget(Widget(size_hint_y=None, height=dp(12)))
            self.add_widget(action_widget)

        self.add_widget(Widget(size_hint_y=0.25))


class EmptyState(_StateBase):
    """حالت خالی (مثلاً: هنوز مکالمه‌ای وجود ندارد)"""

    def __init__(self, icon='💬', title='هنوز چیزی وجود ندارد', description='', **kwargs):
        super().__init__(icon=icon, title=title, description=description, **kwargs)


class ErrorState(_StateBase):
    """حالت خطا (مثلاً: بارگذاری مدل ناموفق بود)"""

    def __init__(self, icon='⚠', title='خطایی رخ داد', description='', **kwargs):
        super().__init__(icon=icon, title=title, description=description,
                          icon_color=theme.error, **kwargs)


class SuccessState(_StateBase):
    """حالت موفقیت (مثلاً: دانلود مدل با موفقیت تمام شد)"""

    def __init__(self, icon='✓', title='انجام شد', description='', **kwargs):
        super().__init__(icon=icon, title=title, description=description,
                          icon_color=theme.success, **kwargs)
