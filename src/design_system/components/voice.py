# -*- coding: utf-8 -*-
"""
کامپوننت‌های اختصاصی حالت صوتی (Voice Mode) سیستم طراحی وینا

این ماژول ویجت‌های مخصوص تجربه‌ی گفت‌وگوی صوتی را فراهم می‌کند تا صفحه‌ی
صدا حس یک دستیار هوشمند فوتوریستیک داشته باشد:

- AnimatedMicrophone: دکمه‌ی میکروفون بزرگ با حلقه‌های پالسی هنگام ضبط
- VoiceWaveform: نام مستعار سطح بالاتر روی SoundWaveWidget موجود
- ListeningIndicator / SpeakingIndicator: برچسب‌های وضعیت با نقطه‌ی پالسی
- VoiceStatusCard: کارت خلاصه‌ی وضعیت صوتی (مدل، زبان، وضعیت فعلی)
- AIAvatar: نام مستعار برای AiOrb در زمینه‌ی مکالمه‌ی صوتی

توجه: ``AiOrb`` و ``SoundWaveWidget`` قبلاً در سایر بخش‌های design_system
پیاده‌سازی شده‌اند؛ این ماژول به‌جای بازنویسی آن‌ها، رویشان لایه‌ی
معنایی/تخصصی مخصوص صدا اضافه می‌کند تا کدی تکراری نشود.
"""

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line

from src.design_system.base import ThemedWidgetMixin, theme
from src.design_system.components.buttons import IconButton
from src.design_system.components.cards import GlassCard


class AnimatedMicrophone(IconButton):
    """دکمه‌ی میکروفون بزرگ با حلقه‌های پالسی متحرک هنگام ضبط صدا"""

    is_recording = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault('text', '🎤')
        kwargs.setdefault('font_size', '34sp')
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (dp(84), dp(84)))
        super().__init__(**kwargs)
        self._t = 0.0
        self._ring_event = None
        with self.canvas.before:
            self._ring_color = Color(*theme.accent[:3], 0.0)
        self.canvas.before.insert(0, self._ring_color)
        self.bind(is_recording=self._on_recording_changed)
        self.bind(pos=self._redraw_rings, size=self._redraw_rings)
        self.bind_theme()

    def on_theme_changed(self):
        super().on_theme_changed()
        self._ring_color.rgba = (*theme.accent[:3], self._ring_color.a)

    def _on_recording_changed(self, instance, value):
        if value:
            self._start_pulse_rings()
        else:
            self._stop_pulse_rings()

    def _start_pulse_rings(self):
        if self._ring_event is not None:
            return
        self._t = 0.0
        self._ring_event = Clock.schedule_interval(self._animate_rings, 1.0 / 30)

    def _stop_pulse_rings(self):
        if self._ring_event is not None:
            self._ring_event.cancel()
            self._ring_event = None
        self.canvas.after.clear()

    def _animate_rings(self, dt):
        self._t += dt
        self.canvas.after.clear()
        with self.canvas.after:
            for i in range(3):
                phase = (self._t * 0.9 + i / 3) % 1.0
                radius = (self.width / 2) * (1.0 + phase * 1.4)
                alpha = max(0.0, 0.5 * (1.0 - phase))
                Color(*theme.accent[:3], alpha)
                Line(circle=(self.center_x, self.center_y, radius), width=dp(2))

    def _redraw_rings(self, *args):
        pass


class VoiceWaveform:
    """پوششی تخصصی صدا روی SoundWaveWidget موجود.

    به‌صورت تابع/فکتوری پیاده‌سازی شده (نه زیرکلاس مستقیم) تا وابستگی
    چرخه‌ای با design_system/__init__.py (جایی که SoundWaveWidget تعریف
    شده) ایجاد نشود؛ import به‌صورت تنبل و فقط در لحظه‌ی نیاز انجام می‌شود.
    """

    def __new__(cls, **kwargs):
        from src.design_system import SoundWaveWidget
        return SoundWaveWidget(**kwargs)


class ListeningIndicator(BoxLayout, ThemedWidgetMixin):
    """برچسب وضعیت «در حال گوش دادن» با نقطه‌ی پالسی قرمز/اکسنت"""

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('spacing', dp(8))
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('height', dp(24))
        super().__init__(**kwargs)

        self._dot = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
        with self._dot.canvas:
            self._dot_color = Color(*theme.accent)
            self._dot_ellipse = Ellipse(pos=self._dot.pos, size=self._dot.size)
        self._dot.bind(pos=self._update_dot, size=self._update_dot)
        self.add_widget(self._dot)

        self._label = Label(
            text='', font_name=theme.font_name, font_size='12.5sp',
            color=theme.text_secondary, size_hint_x=None,
        )
        self._label.bind(texture_size=lambda inst, val: setattr(inst, 'width', val[0]))
        self.add_widget(self._label)

        self.width = dp(140)
        self._pulse_anim = None
        self.bind_theme()

    def on_theme_changed(self):
        self._dot_color.rgba = theme.accent
        self._label.color = theme.text_secondary

    def _update_dot(self, instance, *args):
        self._dot_ellipse.pos = instance.pos
        self._dot_ellipse.size = instance.size

    def set_text(self, text):
        self._label.text = text

    def start(self):
        if self._pulse_anim is not None:
            return
        anim = (
            Animation(a=1.0, duration=theme.get_anim_duration(0.5))
            + Animation(a=0.3, duration=theme.get_anim_duration(0.5))
        )
        anim.repeat = True
        anim.start(self._dot_color)
        self._pulse_anim = anim

    def stop(self):
        if self._pulse_anim is not None:
            Animation.cancel_all(self._dot_color)
            self._dot_color.a = 1.0
            self._pulse_anim = None


class SpeakingIndicator(ListeningIndicator):
    """برچسب وضعیت «در حال صحبت کردن» - همان ساختار ListeningIndicator با متن پیش‌فرض متفاوت"""
    pass


class VoiceStatusCard(GlassCard):
    """کارت خلاصه‌ی وضعیت صوتی: مدل زبانی فعال، زبان تشخیص گفتار، وضعیت لحظه‌ای"""

    status_text = StringProperty('')
    model_text = StringProperty('')
    language_text = StringProperty('')

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(90))
        kwargs.setdefault('padding', [dp(16), dp(12), dp(16), dp(12)])
        kwargs.setdefault('spacing', dp(4))
        kwargs.setdefault('radius', theme.radius_lg)
        super().__init__(**kwargs)

        self._status_label = Label(
            text=self.status_text, font_name=theme.font_name, bold=True,
            font_size='13.5sp', color=theme.text_primary, halign='right',
        )
        self._status_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.add_widget(self._status_label)

        self._detail_label = Label(
            text=self._detail_text(), font_name=theme.font_name, font_size='11sp',
            color=theme.text_secondary, halign='right',
        )
        self._detail_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.add_widget(self._detail_label)

        self.bind(status_text=self._sync, model_text=self._sync, language_text=self._sync)

    def _detail_text(self):
        parts = [p for p in (self.model_text, self.language_text) if p]
        return ' • '.join(parts)

    def _sync(self, *args):
        self._status_label.text = self.status_text
        self._detail_label.text = self._detail_text()

    def on_theme_changed(self):
        super().on_theme_changed()
        self._status_label.color = theme.text_primary
        self._detail_label.color = theme.text_secondary


def AIAvatar(**kwargs):
    """نام مستعار برای AiOrb در بافت مکالمه‌ی صوتی (تابع سازنده، نه کلاس،
    تا وابستگی چرخه‌ای با ماژول loaders ایجاد نشود)"""
    from src.design_system.components.loaders import AiOrb
    return AiOrb(**kwargs)
