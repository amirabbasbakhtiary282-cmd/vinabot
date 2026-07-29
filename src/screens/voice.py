# -*- coding: utf-8 -*-
"""
صفحه‌ی حالت صوتی (Voice Mode) - تجربه‌ی گفت‌وگوی صوتی تمام‌صفحه

شامل: ارب بزرگ متحرک هوش مصنوعی (AIAvatar)، موج صدای اختصاصی
(VoiceWaveform)، میکروفون انیمیشنی با حلقه‌های پالسی (AnimatedMicrophone)،
نشانگرهای وضعیت گوش‌دادن/صحبت‌کردن و کارت وضعیت صوتی.
"""

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from src.design_system import theme, PageHeader
from src.design_system.components.voice import (
    AnimatedMicrophone, VoiceWaveform, ListeningIndicator, SpeakingIndicator,
    VoiceStatusCard, AIAvatar,
)
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

        body = BoxLayout(orientation='vertical', padding=[dp(24), dp(16), dp(24), dp(24)],
                          spacing=dp(14))

        self.status_card = VoiceStatusCard(
            status_text=fix_rtl('آماده'),
            model_text='', language_text=fix_rtl('فارسی'),
            size_hint_y=None, height=dp(72),
        )
        body.add_widget(self.status_card)

        self.orb = AIAvatar(size_hint=(None, None), size=(dp(170), dp(170)),
                             pos_hint={'center_x': 0.5})
        orb_wrap = BoxLayout(size_hint_y=0.33)
        orb_wrap.add_widget(self.orb)
        body.add_widget(orb_wrap)

        indicator_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(26),
                                   spacing=dp(8))
        indicator_row.add_widget(BoxLayout())
        self.listening_indicator = ListeningIndicator()
        self.listening_indicator.set_text(fix_rtl('در حال گوش دادن'))
        indicator_row.add_widget(self.listening_indicator)
        self.speaking_indicator = SpeakingIndicator()
        self.speaking_indicator.set_text(fix_rtl('در حال صحبت کردن'))
        self.speaking_indicator.opacity = 0
        indicator_row.add_widget(self.speaking_indicator)
        indicator_row.add_widget(BoxLayout())
        body.add_widget(indicator_row)

        self.status_label = Label(
            text=fix_rtl('برای شروع، دکمه‌ی میکروفون را لمس کنید'),
            font_name=theme.font_name, font_size='13.5sp', color=theme.text_secondary,
            size_hint_y=None, height=dp(24),
        )
        body.add_widget(self.status_label)

        self.transcript_label = Label(
            text='', font_name=theme.font_name, font_size='15sp', bold=True,
            color=theme.text_primary, halign='center', valign='middle',
            size_hint_y=None, height=dp(70),
        )
        self.transcript_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        body.add_widget(self.transcript_label)

        self.wave = VoiceWaveform(size_hint_y=None, height=dp(50))
        body.add_widget(self.wave)

        body.add_widget(BoxLayout(size_hint_y=None, height=dp(8)))

        mic_wrap = BoxLayout(size_hint_y=None, height=dp(100))
        self.mic_btn = AnimatedMicrophone(pos_hint={'center_x': 0.5})
        self.mic_btn.bind(on_release=lambda *a: self._toggle_voice_mode())
        mic_wrap.add_widget(self.mic_btn)
        body.add_widget(mic_wrap)

        body.add_widget(BoxLayout())

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
        info = app.brain.get_model_info()
        self.status_card.model_text = (
            fix_rtl(info['model_name']) if info['model_name'] else fix_rtl('بدون مدل')
        )

        self.orb.is_active = app.is_listening
        self.orb.is_thinking = (app.voice_state == 'thinking') or app.is_speaking
        self.wave.is_active = app.is_listening or app.is_speaking
        self.mic_btn.is_recording = app.is_listening

        if app.is_listening:
            self.status_label.text = fix_rtl('در حال گوش دادن...')
            self.status_card.status_text = fix_rtl('گوش می‌دهم')
            self._show_indicator(self.listening_indicator, self.speaking_indicator)
        elif app.is_speaking:
            self.status_label.text = fix_rtl('در حال صحبت کردن...')
            self.status_card.status_text = fix_rtl('در حال پاسخ')
            self._show_indicator(self.speaking_indicator, self.listening_indicator)
        elif app.voice_state == 'thinking':
            self.status_label.text = fix_rtl('در حال فکر کردن...')
            self.status_card.status_text = fix_rtl('در حال پردازش')
            self._show_indicator(self.speaking_indicator, self.listening_indicator)
        else:
            self.status_label.text = fix_rtl('برای شروع، دکمه‌ی میکروفون را لمس کنید')
            self.status_card.status_text = fix_rtl('آماده')
            self._hide_all_indicators()

    def _show_indicator(self, active_indicator, other_indicator):
        active_indicator.opacity = 1
        active_indicator.start()
        other_indicator.opacity = 0
        other_indicator.stop()

    def _hide_all_indicators(self):
        self.listening_indicator.opacity = 0
        self.listening_indicator.stop()
        self.speaking_indicator.opacity = 0
        self.speaking_indicator.stop()

    def _toggle_voice_mode(self):
        """شروع/پایان گفتگوی صوتی زنده و پیوسته.

        برخلاف نسخه‌ی قبلی (که هر بار فقط یک جمله می‌شنید)، اینجا یک جلسه‌ی
        گفتگوی دوطرفه شروع می‌شود: وینا گوش می‌دهد، پاسخ می‌دهد، دوباره
        گوش می‌دهد و کاربر می‌تواند وسط حرفش قطعش کند.
        """
        app = App.get_running_app()
        conv = app.voice.conversation

        if conv is not None and conv.is_running:
            app.stop_voice_conversation()
            self.transcript_label.text = fix_rtl('گفتگو پایان یافت')
            return

        def _begin(granted=True):
            if not granted:
                self.transcript_label.text = fix_rtl(
                    'برای گفتگوی صوتی، اجازه‌ی دسترسی به میکروفون لازم است')
                return
            pulse(self.mic_btn, scale_prop='opacity', low=0.6, high=1.0, duration=0.35)
            if app.start_voice_conversation():
                self.transcript_label.text = fix_rtl('گوش می‌دهم... صحبت کنید')
                Clock.schedule_interval(self._poll_state, 0.2)

        app.ensure_microphone_permission(_begin)

    def _on_transcript(self, text):
        self.transcript_label.text = fix_rtl(text)

    def _poll_state(self, dt):
        self._sync_state()
        app = App.get_running_app()
        # متن زنده (چه گفته‌ی کاربر، چه پاسخ در حال تولید وینا)
        if app.live_transcript:
            self.transcript_label.text = fix_rtl(app.live_transcript)

        conv = app.voice.conversation
        if conv is None or not conv.is_running:
            Animation.cancel_all(self.mic_btn)
            self.mic_btn.opacity = 1
            return False
        return True
