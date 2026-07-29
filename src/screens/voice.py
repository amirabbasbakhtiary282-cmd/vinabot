# -*- coding: utf-8 -*-
"""
صفحه‌ی حالت صوتی (Voice Mode) - تجربه‌ی گفت‌وگوی صوتی تمام‌صفحه

شامل: ارب بزرگ متحرک هوش مصنوعی، نشانگر موج صدا، دکمه‌ی میکروفون بزرگ با
انیمیشن پالس، نمایش متن تشخیص داده‌شده و پاسخ فعلی.
"""

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from src.design_system import theme, AiOrb, SoundWaveWidget, PageHeader
from src.design_system.components.buttons import IconButton
from src.design_system.animations import pulse
from src.screens.base import MainTabScreen
from src.text_utils import fix_rtl


class VoiceScreen(MainTabScreen):
    """صفحه‌ی اختصاصی گفت‌وگوی صوتی؛ شبیه دستیارهای هوشمند مدرن"""

    tab_name = 'voice'

    def build_content(self, container):
        with container.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(*theme.bg_primary)
            self._bg_rect = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._redraw_bg, size=self._redraw_bg)

        header = PageHeader(title_text=fix_rtl('حالت صوتی'))
        container.add_widget(header)

        body = BoxLayout(orientation='vertical', padding=[dp(24), dp(20), dp(24), dp(30)],
                          spacing=dp(20))

        body.add_widget(BoxLayout(size_hint_y=0.08))

        self.orb = AiOrb(size_hint=(None, None), size=(dp(180), dp(180)),
                          pos_hint={'center_x': 0.5})
        orb_wrap = BoxLayout(size_hint_y=0.35)
        orb_wrap.add_widget(self.orb)
        body.add_widget(orb_wrap)

        self.status_label = Label(
            text=fix_rtl('برای شروع، دکمه‌ی میکروفون را لمس کنید'),
            font_name=theme.font_name, font_size='14sp', color=theme.text_secondary,
            size_hint_y=0.08,
        )
        body.add_widget(self.status_label)

        self.transcript_label = Label(
            text='', font_name=theme.font_name, font_size='15sp', bold=True,
            color=theme.text_primary, halign='center', valign='middle',
            size_hint_y=0.16,
        )
        self.transcript_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        body.add_widget(self.transcript_label)

        self.wave = SoundWaveWidget(size_hint_y=0.1)
        body.add_widget(self.wave)

        body.add_widget(BoxLayout(size_hint_y=0.05))

        mic_wrap = BoxLayout(size_hint_y=0.18)
        self.mic_btn = IconButton(text='🎤', font_size='34sp', size_hint=(None, None),
                                   size=(dp(84), dp(84)), pos_hint={'center_x': 0.5})
        self.mic_btn.bind(on_release=lambda *a: self._toggle_voice_mode())
        mic_wrap.add_widget(self.mic_btn)
        body.add_widget(mic_wrap)

        container.add_widget(body)

    def _redraw_bg(self, instance, *args):
        self._bg_color.rgba = theme.bg_primary
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._sync_state()

    def _sync_state(self):
        app = App.get_running_app()
        self.orb.is_active = app.is_listening
        self.orb.is_thinking = app.is_speaking
        self.wave.is_active = app.is_listening or app.is_speaking

        if app.is_listening:
            self.status_label.text = fix_rtl('در حال گوش دادن...')
        elif app.is_speaking:
            self.status_label.text = fix_rtl('در حال صحبت کردن...')
        else:
            self.status_label.text = fix_rtl('برای شروع، دکمه‌ی میکروفون را لمس کنید')

    def _toggle_voice_mode(self):
        app = App.get_running_app()
        if app.is_listening:
            return
        pulse(self.mic_btn, scale_prop='opacity', low=0.6, high=1.0, duration=0.35)
        app.start_listening(on_transcript=self._on_transcript)
        Clock.schedule_interval(self._poll_state, 0.2)

    def _on_transcript(self, text):
        self.transcript_label.text = fix_rtl(text)

    def _poll_state(self, dt):
        self._sync_state()
        app = App.get_running_app()
        if not app.is_listening and not app.is_speaking:
            Animation.cancel_all(self.mic_btn)
            self.mic_btn.opacity = 1
            return False
        return True
