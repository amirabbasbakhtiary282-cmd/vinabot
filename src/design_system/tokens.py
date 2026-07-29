# -*- coding: utf-8 -*-
"""
توکن‌های طراحی (Design Tokens) وینا

این ماژول تنها یک لایه‌ی نازک روی موتور تم (``src.theme.theme``) است که
مقادیر ثابت اضافی (اندازه‌ی آیکون‌ها، ارتفاع دکمه‌ها، عرض استاندارد صفحه و
غیره) را نیز به آن اضافه می‌کند. هدف این است که **هیچ عددی به‌صورت مستقیم
در کدهای صفحات نوشته نشود** - همه از اینجا یا از ``theme`` خوانده شود.

نکته‌ی مهم درباره‌ی ``dp()``: مقدار dp به DPI پنجره‌ی فعال وابسته است.
محاسبه‌ی آن در زمان تعریف کلاس (import-time) می‌تواند شکننده باشد اگر
پنجره‌ی Kivy هنوز آماده نشده باشد. برای همین این مقادیر به‌صورت
``classmethod``/``property`` تنبل (lazy) پیاده‌سازی شده‌اند - در واقع فقط
زمانی که واقعاً استفاده شوند (یعنی داخل ساخت یک ویجت) محاسبه می‌شوند.
"""


class _LazyDp:
    """توصیف‌گر (descriptor) کوچک که مقدار dp را فقط در لحظه‌ی دسترسی محاسبه می‌کند"""

    def __init__(self, value):
        self._value = value

    def __get__(self, obj, objtype=None):
        from kivy.metrics import dp
        return dp(self._value)


class _ThemeProxyDp:
    """توصیف‌گر تنبل که در لحظه‌ی دسترسی، مقدار متناظر را از ``theme`` (بر حسب dp)
    می‌خواند. برای مقادیری استفاده می‌شود که در آینده ممکن است کاربر از طریق
    تنظیمات مقیاس‌شان را تغییر دهد (مثل فاصله‌گذاری‌ها) ولی الان روی ``theme``
    به‌صورت عدد خام (نه dp) ذخیره شده‌اند."""

    def __init__(self, theme_attr):
        self._attr = theme_attr

    def __get__(self, obj, objtype=None):
        from kivy.metrics import dp
        from src.theme import theme
        return dp(getattr(theme, self._attr))


class IconSize:
    """اندازه‌ی استاندارد آیکون‌ها (بر حسب dp) - محاسبه‌ی تنبل"""
    XS = _LazyDp(14)
    SM = _LazyDp(18)
    MD = _LazyDp(24)
    LG = _LazyDp(32)
    XL = _LazyDp(48)
    XXL = _LazyDp(72)


class ButtonHeight:
    """ارتفاع استاندارد انواع دکمه (بر حسب dp) - محاسبه‌ی تنبل"""
    SM = _LazyDp(36)
    MD = _LazyDp(48)
    LG = _LazyDp(56)
    FAB = _LazyDp(58)


class Elevation:
    """میزان سایه/بلور برای سطوح مختلف (شبیه‌سازی elevation متریال)"""
    LEVEL_0 = {'blur_radius': 0, 'offset': (0, 0)}
    LEVEL_1 = {'blur_radius': 12, 'offset': (0, -2)}
    LEVEL_2 = {'blur_radius': 20, 'offset': (0, -4)}
    LEVEL_3 = {'blur_radius': 32, 'offset': (0, -8)}


class ScreenLayout:
    """فاصله‌گذاری استاندارد صفحات (padding بیرونی صفحه، عرض حداکثر و...) - محاسبه‌ی تنبل"""
    SCREEN_PADDING_H = _LazyDp(16)
    SCREEN_PADDING_V = _LazyDp(12)
    SECTION_SPACING = _LazyDp(20)
    CARD_SPACING = _LazyDp(12)
    MAX_CONTENT_WIDTH = _LazyDp(480)


class Spacing:
    """فاصله‌گذاری استاندارد سراسری (Small/Medium/Large + XS/XL) - همیشه از
    ``theme`` خوانده می‌شود تا اگر در آینده کاربر مقیاس فاصله‌گذاری را از
    تنظیمات تغییر دهد، همه‌جا هماهنگ باقی بماند. **هیچ فایلی نباید عدد
    فاصله‌گذاری را مستقیم بنویسد؛ همیشه از اینجا (یا از ``theme.space_*``)
    استفاده شود.**
    """
    XS = _ThemeProxyDp('space_xs')
    SM = _ThemeProxyDp('space_sm')
    MD = _ThemeProxyDp('space_md')
    LG = _ThemeProxyDp('space_lg')
    XL = _ThemeProxyDp('space_xl')


class Radius:
    """شعاع گردی گوشه‌ها - سطح‌های استاندارد (کوچک/متوسط/بزرگ/کارت/دکمه‌ی گرد)"""
    SM = _ThemeProxyDp('radius_sm')
    MD = _ThemeProxyDp('radius_md')
    LG = _ThemeProxyDp('radius_lg')
    CARD = _ThemeProxyDp('radius_lg')
    PILL = _ThemeProxyDp('radius_pill')
