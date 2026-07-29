# -*- coding: utf-8 -*-
"""
سیستم انیمیشن قابل استفاده‌ی مجدد وینا

توابع این ماژول انیمیشن‌های استاندارد برنامه را می‌سازند تا در همه‌جا
یکسان و هماهنگ با تنظیم «سرعت انیمیشن» کاربر (``theme.animation_speed_scale``)
باشند. به‌جای نوشتن ``Animation(...)`` پراکنده در هر فایل، همه از این
توابع استفاده می‌کنند.
"""

from kivy.animation import Animation
from kivy.clock import Clock

from src.theme import theme


def fade_in(widget, duration=None, on_complete=None):
    """محو شدن به داخل (opacity: 0 -> 1)"""
    widget.opacity = 0
    d = duration if duration is not None else theme.get_anim_duration(theme.anim_normal)
    anim = Animation(opacity=1, duration=d, t='out_quad')
    if on_complete:
        anim.bind(on_complete=lambda *a: on_complete())
    anim.start(widget)
    return anim


def fade_out(widget, duration=None, on_complete=None):
    d = duration if duration is not None else theme.get_anim_duration(theme.anim_normal)
    anim = Animation(opacity=0, duration=d, t='in_quad')
    if on_complete:
        anim.bind(on_complete=lambda *a: on_complete())
    anim.start(widget)
    return anim


def slide_in_up(widget, distance=30, duration=None):
    """اسلاید از پایین به بالا همراه با محو شدن به داخل (برای ظاهر شدن کارت‌ها)"""
    d = duration if duration is not None else theme.get_anim_duration(theme.anim_normal)
    original_y = widget.y
    widget.y = original_y - distance
    widget.opacity = 0
    anim = Animation(y=original_y, opacity=1, duration=d, t='out_cubic')
    anim.start(widget)
    return anim


def scale_in(widget, duration=None):
    """بزرگ شدن ملایم از حالت کوچک (برای دیالوگ‌ها/پاپ‌آپ‌ها)"""
    d = duration if duration is not None else theme.get_anim_duration(theme.anim_normal)
    widget.opacity = 0
    anim = Animation(opacity=1, duration=d)
    anim.start(widget)
    return anim


def pulse(widget, scale_prop='opacity', low=0.5, high=1.0, duration=None):
    """پالس بی‌نهایت (برای نشانگرهای وضعیت زنده مثل ضبط صدا)"""
    d = duration if duration is not None else theme.get_anim_duration(0.6)
    anim = (
        Animation(**{scale_prop: high}, duration=d, t='in_out_sine')
        + Animation(**{scale_prop: low}, duration=d, t='in_out_sine')
    )
    anim.repeat = True
    anim.start(widget)
    return anim


def bounce_press(widget, factor=0.94, duration=None):
    """افکت فشرده‌شدن ملایم هنگام لمس (بدون نیاز به تغییر اندازه‌ی واقعی ویجت)"""
    d = duration if duration is not None else theme.get_anim_duration(theme.anim_fast)
    anim = Animation(opacity=factor, duration=d) + Animation(opacity=1, duration=d)
    anim.start(widget)
    return anim


def stagger(widgets, animator, delay_step=0.06):
    """اجرای یک تابع انیمیشن روی چند ویجت پشت‌سرهم با تأخیر کوتاه بین هرکدام
    (برای ظاهر شدن تدریجی لیست کارت‌ها، مثل صفحه‌ی خانه)"""
    for i, widget in enumerate(widgets):
        Clock.schedule_once(lambda dt, w=widget: animator(w), i * delay_step)
