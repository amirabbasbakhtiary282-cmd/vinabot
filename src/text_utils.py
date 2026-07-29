# -*- coding: utf-8 -*-
"""
ابزار کمکی برای نمایش صحیح متن فارسی/عربی در Kivy

موتور رندر متن Kivy (SDL2/FreeType) به‌صورت پیش‌فرض شکل‌دهی (shaping) حروف
فارسی و عربی و ترتیب راست‌به‌چپ (bidi) را انجام نمی‌دهد؛ در نتیجه بدون این
پردازش، حروف به‌صورت جدا از هم (غیرمتصل) و به ترتیب اشتباه نمایش داده
می‌شوند. این ماژول متن را پیش از نمایش آماده می‌کند.
"""

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _RESHAPE_AVAILABLE = True
except Exception:
    _RESHAPE_AVAILABLE = False


def fix_rtl(text):
    """آماده‌سازی متن فارسی/عربی برای نمایش صحیح در ویجت‌های Kivy.

    اگر کتابخانه‌های لازم در دسترس نباشند، متن اصلی بدون تغییر برگردانده
    می‌شود (مثلاً حالت fallback در محیط‌هایی که این پکیج‌ها نصب نیستند).
    """
    if not text:
        return text
    if not _RESHAPE_AVAILABLE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text
