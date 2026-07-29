# -*- coding: utf-8 -*-
"""
صفحه‌ی جزئیات یک بخش تنظیمات (Settings Detail)

این صفحه عمومی است: محتوای هر بخش (ظاهر، مدل، صدا، چت، حافظه، فضای
ذخیره‌سازی، حریم خصوصی، اعلان‌ها، درباره) توسط توابع سازنده در
``src/screens/settings_sections.py`` ساخته و اینجا نمایش داده می‌شود.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from src.design_system import theme, PageHeader
from src.text_utils import fix_rtl


class SettingsDetailScreen(Screen):
    """صفحه‌ی عمومی نمایش جزئیات یک بخش تنظیمات"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_section_key = None
        self.current_section_title = ''
        self._root = BoxLayout(orientation='vertical')
        self.add_widget(self._root)

        with self._root.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(*theme.bg_primary)
            self._bg_rect = Rectangle(pos=self._root.pos, size=self._root.size)
        self._root.bind(pos=self._redraw_bg, size=self._redraw_bg)

        self.header = PageHeader(title_text='', on_back=self._go_back)
        self._root.add_widget(self.header)

        self.scroll = ScrollView(do_scroll_x=False, bar_color=theme.accent, bar_width=dp(3))
        self._root.add_widget(self.scroll)

        self.body = BoxLayout(orientation='vertical', size_hint_y=None,
                               padding=[dp(16), dp(8), dp(16), dp(28)], spacing=dp(14))
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)

    def _redraw_bg(self, instance, *args):
        self._bg_color.rgba = theme.bg_primary
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def _go_back(self):
        App.get_running_app().close_settings_section()

    def load_section(self, section_key, title):
        from src.screens import settings_sections as ss
        self.current_section_key = section_key
        # عنوان را نگه می‌داریم تا بتوان همین بخش را بدون دانستن عنوان
        # دوباره ساخت (مثلاً بعد از افزوده شدن یک مدل جدید).
        self.current_section_title = title
        self.header.title_text = fix_rtl(title)
        self.body.clear_widgets()

        builder = ss.SECTION_BUILDERS.get(section_key)
        if builder:
            builder(self.body)
        else:
            from src.design_system import EmptyState
            self.body.add_widget(EmptyState(icon='🚧', title=fix_rtl('این بخش هنوز آماده نیست')))
