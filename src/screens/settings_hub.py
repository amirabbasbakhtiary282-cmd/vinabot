# -*- coding: utf-8 -*-
"""
صفحه‌ی اصلی تنظیمات (Settings Hub) - لیست بخش‌های تنظیمات به‌صورت کارت

هر کارت با لمس، کاربر را به صفحه‌ی جزئیات همان بخش (SettingsDetailScreen)
می‌برد. تمام بخش‌های خواسته‌شده پوشش داده شده‌اند: ظاهر، مدل هوش مصنوعی،
صدا، چت، حافظه، فضای ذخیره‌سازی، حریم خصوصی، اعلان‌ها، درباره.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

from src.design_system import theme, SettingsCard, PageHeader, ParticleSystem
from src.screens.base import MainTabScreen
from src.text_utils import fix_rtl

SETTINGS_SECTIONS = [
    {'key': 'appearance', 'icon': '🎨', 'title': 'ظاهر برنامه', 'desc': 'تم، رنگ، فونت، انیمیشن'},
    {'key': 'ai_model', 'icon': '🧠', 'title': 'مدل هوش مصنوعی', 'desc': 'بارگذاری، دما، حافظه‌ی مدل'},
    {'key': 'voice', 'icon': '🎙', 'title': 'صدا', 'desc': 'گفتار به متن، متن به گفتار'},
    {'key': 'chat', 'icon': '💬', 'title': 'چت', 'desc': 'حباب‌ها، تایپوگرافی، تراکم پیام'},
    {'key': 'memory', 'icon': '🗂', 'title': 'حافظه', 'desc': 'مشاهده، خروجی، پاک کردن'},
    {'key': 'storage', 'icon': '💾', 'title': 'فضای ذخیره‌سازی', 'desc': 'مدل‌ها، کش، پشتیبان‌گیری'},
    {'key': 'privacy', 'icon': '🔒', 'title': 'حریم خصوصی', 'desc': 'مجوزها و داده‌های شخصی'},
    {'key': 'notifications', 'icon': '🔔', 'title': 'اعلان‌ها', 'desc': 'یادآوری‌ها و هشدارها'},
    {'key': 'about', 'icon': 'ℹ', 'title': 'درباره‌ی وینا', 'desc': 'نسخه و اطلاعات برنامه'},
]


class SettingsHubScreen(MainTabScreen):
    """صفحه‌ی اصلی تنظیمات با لیست بخش‌ها"""

    tab_name = 'settings'

    def build_content(self, container):
        with container.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(*theme.bg_primary)
            self._bg_rect = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._redraw_bg, size=self._redraw_bg)

        container.add_widget(ParticleSystem(size_hint=(None, None), num_particles=14))

        header = PageHeader(title_text=fix_rtl('تنظیمات'))
        container.add_widget(header)

        scroll = ScrollView(do_scroll_x=False, bar_color=theme.accent, bar_width=dp(3))
        body = BoxLayout(orientation='vertical', size_hint_y=None,
                          padding=[dp(16), dp(8), dp(16), dp(24)], spacing=dp(10))
        body.bind(minimum_height=body.setter('height'))

        for section in SETTINGS_SECTIONS:
            card = SettingsCard(
                icon=section['icon'],
                title_text=fix_rtl(section['title']),
                description_text=fix_rtl(section['desc']),
                show_arrow=True,
                on_release=lambda key=section['key']: self._open_section(key),
            )
            body.add_widget(card)

        scroll.add_widget(body)
        container.add_widget(scroll)

    def _redraw_bg(self, instance, *args):
        self._bg_color.rgba = theme.bg_primary
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def _open_section(self, key):
        app = App.get_running_app()
        app.open_settings_section(key)
