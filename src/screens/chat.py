# -*- coding: utf-8 -*-
"""
صفحه‌ی چت - مرکز اصلی تعامل با وینا

شامل: هدر با وضعیت مدل، لیست پیام‌ها (Markdown + کدبلاک + دکمه‌های عملیات)،
نشانگر «در حال نوشتن»، ورودی چندخطی و دکمه‌های ارسال/میکروفون.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from src.design_system import (
    theme, AiOrb, IconButton, ChatBubble, TypingIndicator, EmptyState,
)
from src.design_system.components.inputs import ChatInput
from src.screens.base import MainTabScreen
from src.text_utils import fix_rtl


class ChatScreen(MainTabScreen):
    """صفحه‌ی اصلی چت"""

    tab_name = 'chat'
    _typing_indicator = None

    def build_content(self, container):
        with container.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(*theme.bg_primary)
            self._bg_rect = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._redraw_bg, size=self._redraw_bg)

        self._build_header(container)
        self._build_message_list(container)
        self._build_input_bar(container)

    def _redraw_bg(self, instance, *args):
        self._bg_color.rgba = theme.bg_primary
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def _build_header(self, container):
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64),
                            padding=[dp(16), dp(8), dp(16), dp(8)], spacing=dp(10))
        with header.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._header_bg_color = Color(*theme.bg_surface)
            self._header_bg_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._redraw_header, size=self._redraw_header)

        self.header_orb = AiOrb(size_hint=(None, None), size=(dp(38), dp(38)))
        header.add_widget(self.header_orb)

        text_col = BoxLayout(orientation='vertical')
        title_label = Label(
            text=fix_rtl('وینا'), font_name=theme.font_name, bold=True, font_size='17sp',
            color=theme.text_primary, halign='right', size_hint_y=0.55,
        )
        title_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(title_label)

        self.model_status_label = Label(
            text='', font_name=theme.font_name, color=theme.text_secondary,
            font_size='10.5sp', halign='right', size_hint_y=0.45,
        )
        self.model_status_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(self.model_status_label)
        header.add_widget(text_col)

        settings_btn = IconButton(text='⚙', font_size='18sp', size_hint=(None, None),
                                   size=(dp(40), dp(40)))
        settings_btn.bind(on_release=lambda *a: App.get_running_app().switch_tab('settings'))
        header.add_widget(settings_btn)

        container.add_widget(header)

    def _redraw_header(self, instance, *args):
        self._header_bg_color.rgba = theme.bg_surface
        self._header_bg_rect.pos = instance.pos
        self._header_bg_rect.size = instance.size

    def _build_message_list(self, container):
        self.chat_scroll = ScrollView(do_scroll_x=False, bar_color=theme.accent,
                                       bar_inactive_color=theme.glass_border, bar_width=dp(3))
        self.chat_container = BoxLayout(
            orientation='vertical', size_hint_y=None,
            padding=[dp(12), dp(16), dp(12), dp(16)], spacing=dp(10),
        )
        self.chat_container.bind(minimum_height=self.chat_container.setter('height'))
        self.chat_scroll.add_widget(self.chat_container)
        container.add_widget(self.chat_scroll)

        self._empty_state = EmptyState(
            icon='💬', title=fix_rtl('مکالمه را شروع کنید'),
            description=fix_rtl('یک پیام بنویسید یا از دکمه‌ی میکروفون استفاده کنید.'),
        )

    def _build_input_bar(self, container):
        bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(72),
                         padding=[dp(12), dp(10), dp(12), dp(14)], spacing=dp(8))
        with bar.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bar_bg_color = Color(*theme.bg_surface)
            self._bar_bg_rect = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=self._redraw_bar, size=self._redraw_bar)

        self.message_input = ChatInput(hint_text=fix_rtl('پیام خود را بنویسید...'))
        self.message_input.bind(on_text_validate=lambda *a: self.send_message())
        bar.add_widget(self.message_input)

        self.mic_btn = IconButton(text='🎤', font_size='17sp', size_hint=(None, None),
                                   size=(dp(42), dp(42)))
        self.mic_btn.bind(on_release=lambda *a: self.toggle_listening())
        bar.add_widget(self.mic_btn)

        from src.design_system import FloatingActionButton
        self.send_btn = FloatingActionButton(text='➤', font_size='19sp',
                                              size=(dp(48), dp(48)))
        self.send_btn.bind(on_release=lambda *a: self.send_message())
        bar.add_widget(self.send_btn)

        container.add_widget(bar)

    def _redraw_bar(self, instance, *args):
        self._bar_bg_color.rgba = theme.bg_surface
        self._bar_bg_rect.pos = instance.pos
        self._bar_bg_rect.size = instance.size

    # ------------------------------------------------------------------
    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._render_history()
        self._refresh_header_status()

    def _refresh_header_status(self):
        app = App.get_running_app()
        self.model_status_label.text = fix_rtl(app.model_status)
        self.header_orb.is_thinking = app.is_speaking or app.is_listening

    def _render_history(self):
        app = App.get_running_app()
        self.chat_container.clear_widgets()
        if not app.chat_history:
            self.chat_container.add_widget(self._empty_state)
        else:
            for msg in app.chat_history:
                self._add_bubble(msg)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0)

    def _add_bubble(self, msg):
        if self._empty_state.parent:
            self.chat_container.remove_widget(self._empty_state)

        app = App.get_running_app()
        bubble = ChatBubble(
            message=fix_rtl(msg['text']),
            is_user=(msg['role'] == 'user'),
            time_str=msg.get('time', ''),
            show_actions=(msg['role'] != 'user'),
            on_regenerate=lambda: app.regenerate_last_response(),
            on_delete=lambda: self._delete_message(msg),
        )
        self.chat_container.add_widget(bubble)
        return bubble

    def _delete_message(self, msg):
        app = App.get_running_app()
        if msg in app.chat_history:
            app.chat_history.remove(msg)
        self._render_history()

    def _scroll_to_bottom(self):
        self.chat_scroll.scroll_y = 0

    def show_typing_indicator(self):
        if self._typing_indicator is not None:
            return
        self._typing_indicator = TypingIndicator()
        self.chat_container.add_widget(self._typing_indicator)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.05)

    def hide_typing_indicator(self):
        if self._typing_indicator is not None:
            self._typing_indicator.stop()
            try:
                self.chat_container.remove_widget(self._typing_indicator)
            except Exception:
                pass
            self._typing_indicator = None

    def send_message(self):
        app = App.get_running_app()
        text = self.message_input.text.strip()
        if not text:
            return
        self.message_input.text = ""
        app.send_message(text)

    def toggle_listening(self):
        app = App.get_running_app()
        if app.is_listening:
            return
        app.start_listening()

    def on_new_message(self, msg):
        self._add_bubble(msg)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.05)
        self._refresh_header_status()
