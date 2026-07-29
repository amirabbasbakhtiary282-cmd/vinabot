# -*- coding: utf-8 -*-
"""
صفحه‌ی خانه (Home) - نقطه‌ی ورود اصلی پس از لاگین

شامل: کارت خوش‌آمدگویی، وضعیت مدل هوش مصنوعی، آمار سریع (تعداد مکالمات،
حافظه)، اکشن‌های سریع (چت جدید، حالت صوتی، تنظیمات) و لیست مکالمات اخیر.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from src.design_system import (
    theme, AiOrb, ParticleSystem, GlassCard, FeatureCard, ModelCard,
    StatisticsCard, ConversationCard, EmptyState, PageHeader,
)
from src.design_system.animations import stagger, slide_in_up
from src.screens.base import MainTabScreen
from src.text_utils import fix_rtl


class HomeScreen(MainTabScreen):
    """صفحه‌ی اصلی خانه"""

    tab_name = 'home'

    def build_content(self, container):
        with container.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(*theme.bg_primary)
            self._bg_rect = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._redraw_bg, size=self._redraw_bg)

        container.add_widget(ParticleSystem(size_hint=(None, None)))

        header = PageHeader(title_text=fix_rtl('خانه'))
        container.add_widget(header)
        self._header = header

        scroll = ScrollView(do_scroll_x=False, bar_color=theme.accent, bar_width=dp(3))
        self.body = BoxLayout(
            orientation='vertical', size_hint_y=None, padding=[dp(16), dp(8), dp(16), dp(24)],
            spacing=dp(16),
        )
        self.body.bind(minimum_height=self.body.setter('height'))
        scroll.add_widget(self.body)
        container.add_widget(scroll)

        self._build_welcome_card()
        self._build_model_card()
        self._build_stats_row()
        self._build_quick_actions()
        self._build_recent_conversations()

    def _redraw_bg(self, instance, *args):
        self._bg_color.rgba = theme.bg_primary
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._refresh_dynamic_content()

    def _build_welcome_card(self):
        app = App.get_running_app()
        card = GlassCard(
            orientation='horizontal', size_hint_y=None, height=dp(90),
            padding=[dp(18), dp(14), dp(18), dp(14)], spacing=dp(14), radius=theme.radius_lg,
        )
        orb = AiOrb(size_hint=(None, None), size=(dp(56), dp(56)))
        card.add_widget(orb)

        text_col = BoxLayout(orientation='vertical', spacing=dp(4))
        name = app.current_user or fix_rtl('دوست من')
        text_col.add_widget(Label(
            text=fix_rtl(f'سلام {name} 👋'), font_name=theme.font_name, bold=True,
            font_size='16sp', color=theme.text_primary, halign='right',
            text_size=(dp(220), None),
        ))
        text_col.add_widget(Label(
            text=fix_rtl('امروز چطور می‌تونم کمکت کنم؟'), font_name=theme.font_name,
            font_size='12sp', color=theme.text_secondary, halign='right',
            text_size=(dp(220), None),
        ))
        card.add_widget(text_col)
        self.body.add_widget(card)
        slide_in_up(card)

    def _build_model_card(self):
        app = App.get_running_app()
        info = app.brain.get_model_info()
        self._model_card = ModelCard(
            model_name=fix_rtl(info['model_name']) if info['model_name'] else fix_rtl('مدلی بارگذاری نشده'),
            status_text=fix_rtl(app.model_status),
            is_ready=info['loaded'],
        )
        self.body.add_widget(self._model_card)

    def _build_stats_row(self):
        app = App.get_running_app()
        summary = app.memory.get_memory_summary()
        row = GridLayout(cols=3, size_hint_y=None, height=dp(96), spacing=dp(10))
        self._stat_conversations = StatisticsCard(
            icon='💬', value_text=str(summary['conversations_count']),
            label_text=fix_rtl('مکالمه'),
        )
        self._stat_notes = StatisticsCard(
            icon='📝', value_text=str(summary['notes_count']), label_text=fix_rtl('یادداشت'),
        )
        self._stat_storage = StatisticsCard(
            icon='💾', value_text=f"{summary['db_size_kb']:.0f}KB", label_text=fix_rtl('حافظه'),
        )
        row.add_widget(self._stat_conversations)
        row.add_widget(self._stat_notes)
        row.add_widget(self._stat_storage)
        self.body.add_widget(row)

    def _build_quick_actions(self):
        label = Label(
            text=fix_rtl('اکشن‌های سریع'), font_name=theme.font_name, bold=True,
            font_size='14sp', color=theme.text_primary, size_hint_y=None, height=dp(24),
            halign='right',
        )
        label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.body.add_widget(label)

        row = GridLayout(cols=3, size_hint_y=None, height=dp(100), spacing=dp(10))
        app = App.get_running_app()

        cards = [
            FeatureCard(icon='➕', label_text=fix_rtl('چت جدید'),
                        on_release=lambda: app.switch_tab('chat')),
            FeatureCard(icon='🎙', label_text=fix_rtl('حالت صوتی'),
                        on_release=lambda: app.switch_tab('voice')),
            FeatureCard(icon='⚙', label_text=fix_rtl('تنظیمات'),
                        on_release=lambda: app.switch_tab('settings')),
        ]
        for card in cards:
            row.add_widget(card)
        self.body.add_widget(row)
        stagger(cards, slide_in_up)

    def _build_recent_conversations(self):
        label = Label(
            text=fix_rtl('مکالمات اخیر'), font_name=theme.font_name, bold=True,
            font_size='14sp', color=theme.text_primary, size_hint_y=None, height=dp(24),
            halign='right',
        )
        label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.body.add_widget(label)

        self._recent_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8))
        self._recent_container.bind(minimum_height=self._recent_container.setter('height'))
        self.body.add_widget(self._recent_container)
        self._refresh_recent_conversations()

    def _refresh_recent_conversations(self):
        self._recent_container.clear_widgets()
        app = App.get_running_app()
        recent = app.memory.get_recent_conversations(limit=6)

        if not recent:
            self._recent_container.add_widget(EmptyState(
                icon='💬', title=fix_rtl('هنوز مکالمه‌ای نیست'),
                description=fix_rtl('یک پیام در تب چت بفرستید تا اینجا نمایش داده شود.'),
            ))
            return

        # گروه‌بندی ساده: هر پیام کاربر را به‌عنوان شروع یک مکالمه در نظر می‌گیریم
        user_messages = [m for m in recent if m['role'] == 'user']
        for msg in reversed(user_messages[-5:]):
            preview = msg['message'][:40] + ('…' if len(msg['message']) > 40 else '')
            card = ConversationCard(
                title_text=fix_rtl(preview[:20] or 'مکالمه'),
                preview_text=fix_rtl(preview),
                time_text=msg['time'][-5:] if msg.get('time') else '',
                on_release=lambda: App.get_running_app().switch_tab('chat'),
            )
            self._recent_container.add_widget(card)

    def _refresh_dynamic_content(self):
        app = App.get_running_app()
        info = app.brain.get_model_info()
        self._model_card.model_name = (
            fix_rtl(info['model_name']) if info['model_name'] else fix_rtl('مدلی بارگذاری نشده')
        )
        self._model_card.status_text = fix_rtl(app.model_status)
        self._model_card.is_ready = info['loaded']

        summary = app.memory.get_memory_summary()
        self._stat_conversations.value_text = str(summary['conversations_count'])
        self._stat_notes.value_text = str(summary['notes_count'])
        self._stat_storage.value_text = f"{summary['db_size_kb']:.0f}KB"

        self._refresh_recent_conversations()
