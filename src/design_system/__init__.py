# -*- coding: utf-8 -*-
"""
سیستم طراحی (Design System) وینا

نقطه‌ی ورود واحد برای تمام توکن‌ها، تایپوگرافی، انیمیشن‌ها و کامپوننت‌های
بصری برنامه. تمام صفحات باید فقط از این پکیج import کنند، نه از رنگ‌های
hardcode یا ویجت‌های خام Kivy.

ساختار:
    src/design_system/
        tokens.py       - اندازه‌ها، فاصله‌ها، ارتفاع‌های استاندارد
        typography.py   - سبک‌های متنی استاندارد (Type Scale)
        animations.py   - توابع انیمیشن قابل‌استفاده‌ی مجدد
        base.py         - ThemedWidgetMixin و ابزارهای مشترک
        components/     - تمام ویجت‌های بصری (دکمه، کارت، ورودی، دیالوگ، ...)
"""

from kivy.factory import Factory

from src.theme import theme, THEMES, THEME_LABELS
from src.design_system.base import ThemedWidgetMixin, rgba_to_hex
from src.design_system.tokens import IconSize, ButtonHeight, Elevation, ScreenLayout
from src.design_system.typography import (
    TypeStyle, TYPE_LARGE_TITLE, TYPE_TITLE, TYPE_SECTION_TITLE,
    TYPE_BODY, TYPE_BODY_STRONG, TYPE_CAPTION, TYPE_BUTTON, TYPE_CODE, font_name,
)
from src.design_system import animations

# --- کامپوننت‌ها ---
from src.design_system.components.buttons import (
    AnimatedButton, PrimaryButton, SecondaryButton, DangerButton,
    IconButton, FloatingActionButton,
)
from src.design_system.components.cards import (
    GlassCard, SettingsCard, FeatureCard, ModelCard, StatisticsCard, MemoryCard,
)
from src.design_system.components.inputs import (
    ModernTextField, SearchField, PasswordField, ChatInput,
)
from src.design_system.components.dialogs import (
    ModernDialog, ConfirmationDialog, BottomSheet, ActionSheet, ActionSheetItem,
)
from src.design_system.components.feedback import (
    Snackbar, Toast, LoadingOverlay, EmptyState, ErrorState, SuccessState,
)
from src.design_system.components.loaders import LoadingSpinner, AiOrb, ParticleSystem
from src.design_system.components.controls import (
    ModernSwitch, ModernSlider, Dropdown, SegmentedControl,
)
from src.design_system.components.chat import (
    Avatar, CodeBlock, ChatBubble, TypingIndicator, ThinkingAnimation,
    MessageActions, ConversationCard,
)
from src.design_system.components.navigation import (
    PageHeader, ModernBottomNavigation, TabButton,
)

# نگه‌داری سازگاری با کد قدیمی: SoundWaveWidget قبلاً در src/ui.py بود
from kivy.clock import Clock as _Clock
from kivy.graphics import Color as _Color, RoundedRectangle as _RoundedRectangle
from kivy.properties import BooleanProperty as _BooleanProperty, NumericProperty as _NumericProperty
from kivy.uix.widget import Widget as _Widget
import random as _random


class SoundWaveWidget(_Widget, ThemedWidgetMixin):
    """نوار موج صدای مینیمال؛ برای نمایش سطح صدا در حالت گوش‌دادن/صحبت"""

    bar_count = _NumericProperty(24)
    is_active = _BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.levels = [0.0] * int(self.bar_count)
        self.target_levels = [0.0] * int(self.bar_count)
        self._update_event = _Clock.schedule_interval(self._update, 1.0 / 30)
        self.bind_theme()

    def on_theme_changed(self):
        pass

    def on_parent(self, widget, parent):
        if parent is None and self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        elif parent is not None and self._update_event is None:
            self._update_event = _Clock.schedule_interval(self._update, 1.0 / 30)

    def _update(self, dt):
        if not self.width:
            return

        bar_count = int(self.bar_count)
        bar_width = self.width / (bar_count * 1.8)
        gap = bar_width * 0.8
        total_width = bar_count * (bar_width + gap)
        start_x = self.x + (self.width - total_width) / 2

        accent = theme.accent
        muted = theme.text_disabled

        self.canvas.clear()
        with self.canvas:
            for i in range(bar_count):
                if self.is_active:
                    self.target_levels[i] = _random.uniform(0.15, 1.0)
                else:
                    self.target_levels[i] = 0.06

                self.levels[i] += (self.target_levels[i] - self.levels[i]) * 0.25

                bar_height = max(3, self.levels[i] * self.height * 0.85)
                x = start_x + i * (bar_width + gap)
                y = self.y + (self.height - bar_height) / 2

                color = accent if self.is_active else muted
                alpha = 0.9 if self.is_active else 0.5
                _Color(*color[:3], alpha)
                _RoundedRectangle(pos=(x, y), size=(bar_width, bar_height),
                                   radius=[bar_width / 2])

    def set_levels(self, levels):
        bar_count = int(self.bar_count)
        for i, level in enumerate(levels[:bar_count]):
            self.target_levels[i] = min(1.0, level / 32768.0 if level > 1 else level)


# ==========================================================================
# ثبت تمام کامپوننت‌های بصری در Factory تا KV بتواند مستقیماً استفاده کند
# ==========================================================================
_ALL_WIDGETS = (
    AnimatedButton, PrimaryButton, SecondaryButton, DangerButton,
    IconButton, FloatingActionButton,
    GlassCard, SettingsCard, FeatureCard, ModelCard, StatisticsCard, MemoryCard,
    ModernTextField, SearchField, PasswordField, ChatInput,
    ModernDialog, ConfirmationDialog, BottomSheet, ActionSheet, ActionSheetItem,
    Snackbar, Toast, LoadingOverlay, EmptyState, ErrorState, SuccessState,
    LoadingSpinner, AiOrb, ParticleSystem,
    ModernSwitch, ModernSlider, Dropdown, SegmentedControl,
    Avatar, CodeBlock, ChatBubble, TypingIndicator, MessageActions, ConversationCard,
    PageHeader, ModernBottomNavigation, TabButton,
    SoundWaveWidget,
)

for _widget_cls in _ALL_WIDGETS:
    Factory.register(_widget_cls.__name__, cls=_widget_cls)


__all__ = [
    'theme', 'THEMES', 'THEME_LABELS', 'ThemedWidgetMixin', 'rgba_to_hex',
    'IconSize', 'ButtonHeight', 'Elevation', 'ScreenLayout',
    'TypeStyle', 'TYPE_LARGE_TITLE', 'TYPE_TITLE', 'TYPE_SECTION_TITLE',
    'TYPE_BODY', 'TYPE_BODY_STRONG', 'TYPE_CAPTION', 'TYPE_BUTTON', 'TYPE_CODE', 'font_name',
    'animations',
    'AnimatedButton', 'PrimaryButton', 'SecondaryButton', 'DangerButton',
    'IconButton', 'FloatingActionButton',
    'GlassCard', 'SettingsCard', 'FeatureCard', 'ModelCard', 'StatisticsCard', 'MemoryCard',
    'ModernTextField', 'SearchField', 'PasswordField', 'ChatInput',
    'ModernDialog', 'ConfirmationDialog', 'BottomSheet', 'ActionSheet', 'ActionSheetItem',
    'Snackbar', 'Toast', 'LoadingOverlay', 'EmptyState', 'ErrorState', 'SuccessState',
    'LoadingSpinner', 'AiOrb', 'ParticleSystem',
    'ModernSwitch', 'ModernSlider', 'Dropdown', 'SegmentedControl',
    'Avatar', 'CodeBlock', 'ChatBubble', 'TypingIndicator', 'ThinkingAnimation',
    'MessageActions', 'ConversationCard',
    'PageHeader', 'ModernBottomNavigation', 'TabButton',
    'SoundWaveWidget',
]
