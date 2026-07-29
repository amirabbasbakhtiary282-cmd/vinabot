# -*- coding: utf-8 -*-
"""
سیستم تایپوگرافی وینا

یک مجموعه‌ی استاندارد از سبک‌های متنی (Large Title تا Caption) که همه‌ی
صفحات باید از آن‌ها استفاده کنند تا سلسله‌مراتب بصری متن در کل برنامه
یکدست باشد. اندازه‌ی فونت‌ها به ``theme.font_scale`` گوش می‌دهند تا اگر
کاربر از تنظیمات اندازه‌ی فونت را تغییر دهد، همه‌جا اعمال شود.
"""

from src.theme import theme


class TypeStyle:
    """یک سبک تایپوگرافی: اندازه‌ی پایه + وزن + رفتار خط"""

    def __init__(self, base_size, bold=False, letter_spacing_note=''):
        self.base_size = base_size
        self.bold = bold

    @property
    def font_size(self):
        return f"{self.base_size * theme.font_scale}sp"


# --- مقیاس تایپوگرافی (Type Scale) ---
TYPE_LARGE_TITLE = TypeStyle(28, bold=True)     # عنوان صفحات اصلی (خوش‌آمدگویی، ورود)
TYPE_TITLE = TypeStyle(22, bold=True)           # عنوان صفحه (هدر Chat/Settings)
TYPE_SECTION_TITLE = TypeStyle(16, bold=True)   # عنوان بخش (کارت‌های تنظیمات)
TYPE_BODY = TypeStyle(14.5, bold=False)         # متن اصلی پیام‌ها و محتوا
TYPE_BODY_STRONG = TypeStyle(14.5, bold=True)
TYPE_CAPTION = TypeStyle(11.5, bold=False)      # زمان، توضیحات کوتاه
TYPE_BUTTON = TypeStyle(15, bold=True)          # متن دکمه‌ها
TYPE_CODE = TypeStyle(12.5, bold=False)         # متن داخل بلوک کد


def font_name():
    """نام فونت جاری (واکنش‌گرا به تغییر تم/زبان در آینده)"""
    return theme.font_name
