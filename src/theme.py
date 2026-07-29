# -*- coding: utf-8 -*-
"""
موتور تم (Theme Engine) وینا

این ماژول قلب سیستم طراحی برنامه است. هیچ رنگ، فاصله یا شعاعی نباید در
جایی از برنامه به‌صورت hardcode نوشته شود؛ همه‌چیز باید از طریق شیء
سراسری ``theme`` (نمونه‌ی singleton از ``ThemeEngine``) خوانده شود.

چون ``ThemeEngine`` یک ``EventDispatcher`` واقعی کیوی است و تمام مقادیر
آن Kivy Property هستند (ColorProperty/NumericProperty/...)، هر باینـدینگ
KV یا Python که به ``theme.xxx`` وصل شود، به‌محض تغییر مقدار (مثلاً با
انتخاب یک تم جدید) بلافاصله و بدون نیاز به بازسازی صفحه یا ری‌استارت
برنامه به‌روزرسانی می‌شود. این یعنی سوییچ تم واقعاً realtime است.
"""

from kivy.event import EventDispatcher
from kivy.properties import ColorProperty, NumericProperty, StringProperty, BooleanProperty
from kivy.utils import get_color_from_hex as _c


def _mix(c1, c2, t):
    """درون‌یابی خطی بین دو رنگ RGBA"""
    return [c1[i] + (c2[i] - c1[i]) * t for i in range(4)]


# ==========================================================================
# تعریف پالت‌های کامل برای هر تم توکار
# ==========================================================================
def _base_dark_palette(accent_hex, accent2_hex):
    """پالت پایه‌ی تیره؛ فقط رنگ اکسنت بین تم‌های مختلف عوض می‌شود"""
    return {
        'bg_primary': _c('#000000'),
        'bg_secondary': _c('#0F1115'),
        'bg_surface': _c('#181A20'),
        'bg_surface_alt': _c('#1F222A'),
        'bg_elevated': _c('#20232C'),

        'accent': _c(accent_hex),
        'accent_secondary': _c(accent2_hex),

        'success': _c('#4CAF50'),
        'warning': _c('#FF9800'),
        'error': _c('#F44336'),

        'text_primary': _c('#FFFFFF'),
        'text_secondary': _c('#B8BCC8'),
        'text_disabled': _c('#6B6E78'),
        'text_on_accent': _c('#04140C'),

        'divider': (1, 1, 1, 0.08),
        'glass_fill': (1, 1, 1, 0.05),
        'glass_border': (1, 1, 1, 0.10),
        'shadow': (0, 0, 0, 0.45),
        'is_dark': True,
        'is_amoled': False,
    }


THEMES = {
    'emerald': _base_dark_palette('#00E676', '#00C853'),  # پیش‌فرض: مشکی + سبز زمردی
    'blue': _base_dark_palette('#2979FF', '#2962FF'),
    'purple': _base_dark_palette('#B388FF', '#7C4DFF'),
    'red': _base_dark_palette('#FF5252', '#E53935'),
    'orange': _base_dark_palette('#FFAB40', '#FF9100'),
    'cyan': _base_dark_palette('#18FFFF', '#00E5FF'),
}

# تم آمولد خالص - پس‌زمینه‌ی کاملاً مشکی برای صرفه‌جویی باتری روی صفحه‌های OLED
THEMES['amoled'] = dict(THEMES['emerald'])
THEMES['amoled'].update({
    'bg_primary': _c('#000000'),
    'bg_secondary': _c('#000000'),
    'bg_surface': _c('#0A0A0A'),
    'bg_surface_alt': _c('#121212'),
    'bg_elevated': _c('#141414'),
    'is_amoled': True,
})

# تم روشن
THEMES['light'] = {
    'bg_primary': _c('#FFFFFF'),
    'bg_secondary': _c('#F4F5F7'),
    'bg_surface': _c('#FFFFFF'),
    'bg_surface_alt': _c('#EEF0F3'),
    'bg_elevated': _c('#FFFFFF'),

    'accent': _c('#00B060'),
    'accent_secondary': _c('#00964F'),

    'success': _c('#2E7D32'),
    'warning': _c('#E65100'),
    'error': _c('#C62828'),

    'text_primary': _c('#12141A'),
    'text_secondary': _c('#51545E'),
    'text_disabled': _c('#9599A6'),
    'text_on_accent': _c('#FFFFFF'),

    'divider': (0, 0, 0, 0.08),
    'glass_fill': (0, 0, 0, 0.035),
    'glass_border': (0, 0, 0, 0.08),
    'shadow': (0, 0, 0, 0.14),
    'is_dark': False,
    'is_amoled': False,
}

THEME_LABELS = {
    'emerald': 'مشکی + سبز زمردی',
    'blue': 'مشکی + آبی',
    'purple': 'مشکی + بنفش',
    'red': 'مشکی + قرمز',
    'orange': 'مشکی + نارنجی',
    'cyan': 'مشکی + فیروزه‌ای',
    'amoled': 'آمولد خالص',
    'light': 'روشن',
}


class ThemeEngine(EventDispatcher):
    """موتور تم زنده‌ی برنامه (singleton سراسری: ``theme``)"""

    # --- نام تم فعال ---
    theme_name = StringProperty('emerald')
    follow_system = BooleanProperty(False)

    # --- رنگ‌های پس‌زمینه ---
    bg_primary = ColorProperty(_c('#000000'))
    bg_secondary = ColorProperty(_c('#0F1115'))
    bg_surface = ColorProperty(_c('#181A20'))
    bg_surface_alt = ColorProperty(_c('#1F222A'))
    bg_elevated = ColorProperty(_c('#20232C'))

    # --- رنگ‌های برند/اکسنت ---
    accent = ColorProperty(_c('#00E676'))
    accent_secondary = ColorProperty(_c('#00C853'))

    # --- وضعیت‌ها ---
    success = ColorProperty(_c('#4CAF50'))
    warning = ColorProperty(_c('#FF9800'))
    error = ColorProperty(_c('#F44336'))

    # --- متن ---
    text_primary = ColorProperty(_c('#FFFFFF'))
    text_secondary = ColorProperty(_c('#B8BCC8'))
    text_disabled = ColorProperty(_c('#6B6E78'))
    text_on_accent = ColorProperty(_c('#04140C'))

    # --- خطوط جداکننده / شیشه‌ای / سایه ---
    divider = ColorProperty((1, 1, 1, 0.08))
    glass_fill = ColorProperty((1, 1, 1, 0.05))
    glass_border = ColorProperty((1, 1, 1, 0.10))
    shadow = ColorProperty((0, 0, 0, 0.45))

    is_dark = BooleanProperty(True)
    is_amoled = BooleanProperty(False)

    # --- حباب‌های چت (مشتق از accent/surface اما جداگانه قابل تنظیم) ---
    bubble_user = ColorProperty(_c('#00E676'))
    bubble_user_text = ColorProperty(_c('#04140C'))
    bubble_bot = ColorProperty(_c('#181A20'))
    bubble_bot_text = ColorProperty(_c('#FFFFFF'))

    # --- فاصله‌گذاری قابل‌تنظیم (بر حسب dp) ---
    space_xs = NumericProperty(4)
    space_sm = NumericProperty(8)
    space_md = NumericProperty(16)
    space_lg = NumericProperty(24)
    space_xl = NumericProperty(32)

    # --- شعاع گردی گوشه‌ها (قابل تنظیم توسط کاربر) ---
    radius_sm = NumericProperty(10)
    radius_md = NumericProperty(16)
    radius_lg = NumericProperty(22)
    radius_pill = NumericProperty(999)
    corner_radius_scale = NumericProperty(1.0)  # ضریب سراسری (تنظیمات ظاهری)

    # --- شفافیت/بلور (تنظیمات ظاهری) ---
    transparency = NumericProperty(1.0)   # 0..1، برای کارت‌های شیشه‌ای
    blur_strength = NumericProperty(0.5)  # 0..1 (شبیه‌سازی شده با لایه‌های نیمه‌شفاف)

    # --- سرعت انیمیشن (ضریب سراسری؛ کاربر می‌تواند کند/سریع‌تر کند) ---
    animation_speed_scale = NumericProperty(1.0)  # 1.0 = عادی، 0.5 = دو برابر سریع‌تر
    anim_fast = NumericProperty(0.12)
    anim_normal = NumericProperty(0.22)
    anim_slow = NumericProperty(0.4)

    # --- تایپوگرافی ---
    font_name = StringProperty('Vazir')
    font_scale = NumericProperty(1.0)  # اندازه‌ی فونت سراسری

    # --- چت ---
    bubble_radius_scale = NumericProperty(1.0)
    message_density_scale = NumericProperty(1.0)  # فاصله‌ی عمودی بین پیام‌ها
    chat_width_scale = NumericProperty(1.0)  # عرض حباب چت نسبت به صفحه
    show_avatars = BooleanProperty(True)
    show_timestamps = BooleanProperty(True)

    def get_anim_duration(self, base):
        """مدت انیمیشن را با در نظر گرفتن تنظیم سرعت کاربر برمی‌گرداند"""
        return max(0.03, base * self.animation_speed_scale)

    def radius(self, base):
        """شعاع گردی را با ضریب کاربر برمی‌گرداند"""
        return base * self.corner_radius_scale

    def apply_palette(self, name):
        """اعمال یک پالت توکار با نام مشخص"""
        if name not in THEMES:
            name = 'emerald'
        palette = THEMES[name]
        self.theme_name = name
        for key, value in palette.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # حباب‌های چت را از پالت مشتق کن (مگر کاربر جداگانه override کرده باشد)
        self.bubble_user = self.accent
        self.bubble_user_text = palette.get('text_on_accent', self.text_on_accent)
        self.bubble_bot = self.bg_surface
        self.bubble_bot_text = self.text_primary

    def set_custom_accent(self, hex_color):
        """تنظیم رنگ اکسنت اختصاصی (بدون نیاز به تعریف تم کامل جدید)"""
        try:
            color = _c(hex_color)
        except Exception:
            return False
        self.accent = color
        self.bubble_user = color
        return True

    def available_themes(self):
        """لیست (نام_داخلی، برچسب_فارسی) برای نمایش در تنظیمات"""
        return [(key, THEME_LABELS.get(key, key)) for key in THEMES.keys()]


# نمونه‌ی سراسری - تنها شیء ThemeEngine در کل برنامه
theme = ThemeEngine()
theme.apply_palette('emerald')
