# -*- coding: utf-8 -*-
"""
ابزارهای پایه‌ی مشترک سیستم طراحی: اتصال به تم و توابع کمکی رنگ
"""

from src.theme import theme

__all__ = ['theme', 'ThemedWidgetMixin', 'rgba_to_hex']


def rgba_to_hex(rgba):
    r, g, b = rgba[0], rgba[1], rgba[2]
    return f"{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


class ThemedWidgetMixin:
    """Mixin پایه برای اتصال خودکار به رویدادهای تغییر ``theme``.

    زیرکلاس باید متد ``on_theme_changed`` را پیاده‌سازی کند. این mixin
    پایه‌ی تمام کامپوننت‌های سیستم طراحی وینا است تا با تغییر تم (حتی در
    زمان اجرا و بدون ری‌استارت) رنگ‌ها بلافاصله به‌روزرسانی شوند.
    """

    _theme_bound_keys = (
        'bg_primary', 'bg_secondary', 'bg_surface', 'bg_surface_alt', 'bg_elevated',
        'accent', 'accent_secondary', 'success', 'warning', 'error',
        'text_primary', 'text_secondary', 'text_disabled', 'text_on_accent',
        'divider', 'glass_fill', 'glass_border', 'shadow',
        'bubble_user', 'bubble_user_text', 'bubble_bot', 'bubble_bot_text',
        'corner_radius_scale', 'animation_speed_scale', 'font_scale', 'font_name',
    )

    def bind_theme(self):
        for key in self._theme_bound_keys:
            theme.bind(**{key: self._on_theme_prop_changed})

    def unbind_theme(self):
        for key in self._theme_bound_keys:
            try:
                theme.unbind(**{key: self._on_theme_prop_changed})
            except Exception:
                pass

    def _on_theme_prop_changed(self, *args):
        self.on_theme_changed()

    def on_theme_changed(self):
        pass
