# -*- coding: utf-8 -*-
"""
ابزار مشترک صفحات اصلی برنامه (Home/Chat/Voice/Settings)

تمام این صفحات به‌صورت کاملاً Python (نه KV) ساخته می‌شوند چون محتوای
پویا و پیچیده‌ای دارند (لیست‌های داینامیک، تنظیمات با ساختار متغیر).
تمام رنگ‌ها و اندازه‌ها از ``src.design_system`` گرفته می‌شوند.
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from src.design_system import ModernBottomNavigation

TAB_ITEMS = [
    {'icon': '⌂', 'label': 'خانه', 'screen': 'home'},
    {'icon': '💬', 'label': 'چت', 'screen': 'chat'},
    {'icon': '🎙', 'label': 'صدا', 'screen': 'voice'},
    {'icon': '⚙', 'label': 'تنظیمات', 'screen': 'settings'},
]


class MainTabScreen(Screen):
    """پایه‌ی مشترک صفحاتی که نوار ناوبری پایین را نمایش می‌دهند"""

    tab_name = None  # زیرکلاس باید مقداردهی کند (یکی از مقادیر TAB_ITEMS[i]['screen'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._root_layout = BoxLayout(orientation='vertical')
        self.add_widget(self._root_layout)

        self.content_container = BoxLayout(orientation='vertical')
        self._root_layout.add_widget(self.content_container)

        self.bottom_nav = ModernBottomNavigation(
            items=TAB_ITEMS, on_select=self._on_tab_selected,
        )
        self._root_layout.add_widget(self.bottom_nav)

        self.build_content(self.content_container)
        self._sync_selected_tab()

    def build_content(self, container):
        """زیرکلاس باید محتوای اصلی صفحه را داخل container بسازد"""
        raise NotImplementedError

    def _sync_selected_tab(self):
        try:
            index = [t['screen'] for t in TAB_ITEMS].index(self.tab_name)
            self.bottom_nav.select_index(index)
        except (ValueError, AttributeError):
            pass

    def _on_tab_selected(self, index):
        target = TAB_ITEMS[index]['screen']
        if target == self.tab_name:
            return
        app = App.get_running_app()
        app.switch_tab(target)

    def on_pre_enter(self, *args):
        self._sync_selected_tab()
