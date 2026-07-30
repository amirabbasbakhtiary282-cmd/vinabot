# -*- coding: utf-8 -*-
"""
ماژول صدای وینا: تشخیص گفتار (STT)، گویش متن (TTS) و گفتگوی زنده

معماری (Phase A):

- **TTS**: android.speech.tts.TextToSpeech (داخلی سیستم‌عامل، آفلاین روی
  اکثر گوشی‌ها اگر داده‌ی زبان نصب باشد).
- **STT**: دو موتور قابل انتخاب (src/stt_engine.py)
    * ``vosk``   - پیش‌فرض، کاملاً آفلاین، صدا از گوشی خارج نمی‌شود.
    * ``android``- اختیاری، دقیق‌تر، اما معمولاً آنلاین (سرور گوگل).
- **گفتگوی زنده**: src/voice_conversation.py که VAD + STT + LLM + TTS را
  با پشتیبانی از «قطع کردن وسط صحبت» به هم وصل می‌کند.

این کلاس سازگاری با APIهای قبلی (speak/listen/stop_speaking) را حفظ می‌کند
تا صفحه‌های موجود بدون تغییر کار کنند.
"""

import queue

from src.android_bridge import AndroidBridge, is_android


class VinaVoice:
    """کلاس مدیریت صدا برای وینا"""

    def __init__(self, prefer_offline_stt=True, language='fa'):
        self.is_android = is_android()
        self.bridge = AndroidBridge()
        self.isListening = False
        self._audio_levels = [0] * 30
        self.language = language
        self.prefer_offline_stt = prefer_offline_stt
        self.stt_note = None
        self._conversation = None

        if self.is_android:
            # مهم: نسخه‌ی *غیرمسدودکننده*. نسخه‌ی قبلی
            # ``set_tts_language_fa()`` را مستقیم صدا می‌زد و چون این
            # سازنده داخل ``VinaApp.build()`` روی ترد اصلی اجرا می‌شود،
            # تا ۵ ثانیه رابط کاربری قفل می‌شد و اندروید برنامه را
            # می‌کشت (کرش چند لحظه بعد از نمایش صفحه‌ی بارگذاری).
            self.bridge.set_tts_language_fa_async()

    # ------------------------------------------------------------------
    # گویش (TTS)
    # ------------------------------------------------------------------
    def speak(self, text, queue_mode=False):
        """گویش متن با موتور TTS.

        ``queue_mode=True`` جمله را پشت جمله‌های قبلی صف می‌کند (برای گفتار
        جریانی در گفتگوی زنده).
        """
        if not text:
            return False
        return self.bridge.speak(text, queue=queue_mode)

    def speak_queued(self, text):
        return self.speak(text, queue_mode=True)

    def stop_speaking(self):
        self.bridge.stop_speaking()

    def is_speaking(self):
        return self.bridge.is_speaking()

    def set_speech_rate(self, rate):
        return self.bridge.set_speech_rate(rate)

    def set_pitch(self, pitch):
        return self.bridge.set_pitch(pitch)

    def shutdown(self):
        self.stop_conversation()
        self.bridge.shutdown_tts()

    # ------------------------------------------------------------------
    # تشخیص گفتار یک‌باره (سازگاری با کد قبلی)
    # ------------------------------------------------------------------
    def listen(self, timeout=10, on_partial=None):
        """گوش می‌دهد و متن تشخیص داده‌شده را به صورت synchronous برمی‌گرداند.

        این متد باید در یک ترد جداگانه (نه ترد UI) فراخوانی شود.
        """
        if not self.is_android:
            return self._listen_text_fallback()

        result_queue = queue.Queue()

        def on_result(text):
            result_queue.put(('ok', text))

        def on_error(message):
            result_queue.put(('error', message))

        self.isListening = True
        self.bridge.listen_once(on_result, on_error, language=f'{self.language}-IR',
                                timeout_sec=timeout, on_partial=on_partial)

        try:
            status, payload = result_queue.get(timeout=timeout + 5)
        except queue.Empty:
            self.isListening = False
            return None

        self.isListening = False
        if status == 'ok':
            return payload
        print(f"خطای تشخیص گفتار: {payload}")
        return None

    def stop_listening(self):
        self.isListening = False
        self.bridge.stop_listening()

    def _listen_text_fallback(self):
        """ورودی متنی جایگزین (فقط برای اجرای دسکتاپ/توسعه)"""
        try:
            text = input("پیام خود را بنویسید: ")
            return text.strip() if text.strip() else None
        except (EOFError, KeyboardInterrupt):
            return None

    # ------------------------------------------------------------------
    # گفتگوی صوتی زنده و دوطرفه
    # ------------------------------------------------------------------
    def create_conversation(self, llm_generate, wake_word_enabled=False,
                            barge_in_enabled=True):
        """یک جلسه‌ی گفتگوی صوتی زنده می‌سازد (هنوز شروع نشده).

        ``llm_generate(text, on_token)`` باید پاسخ مدل را تولید کند و هر
        قطعه را به ``on_token`` بدهد؛ اگر ``on_token`` مقدار ``False``
        برگرداند باید تولید متوقف شود (برای قطع کردن وسط صحبت).
        """
        from src.audio_recorder import create_recorder
        from src.stt_engine import create_stt
        from src.voice_conversation import VoiceConversation

        stt, note = create_stt(prefer_offline=self.prefer_offline_stt,
                               lang=self.language, bridge=self.bridge)
        self.stt_note = note

        self._conversation = VoiceConversation(
            stt=stt,
            tts_speak=self.speak_queued,   # صف‌کردن، نه قطع‌کردن
            tts_stop=self.stop_speaking,
            llm_generate=llm_generate,
            recorder=create_recorder(),
            wake_word_enabled=wake_word_enabled,
            barge_in_enabled=barge_in_enabled,
        )
        return self._conversation

    @property
    def conversation(self):
        return self._conversation

    def stop_conversation(self):
        if self._conversation is not None:
            try:
                self._conversation.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def stt_engine_info(self):
        """اطلاعات موتور فعلی STT برای نمایش در رابط کاربری."""
        from src.stt_engine import VOSK_MODELS, find_vosk_model

        offline_ready = find_vosk_model(self.language) is not None
        if self.prefer_offline_stt and offline_ready:
            return {'name': 'vosk', 'offline': True,
                    'label': 'آفلاین (Vosk) - صدا از گوشی خارج نمی‌شود'}
        if self.prefer_offline_stt and not offline_ready:
            info = VOSK_MODELS.get(self.language, {})
            size_mb = int(info.get('size', 0) / (1024 * 1024))
            return {'name': 'none', 'offline': True, 'needs_download': True,
                    'label': f'مدل آفلاین دانلود نشده (~{size_mb} مگابایت)'}
        return {'name': 'android', 'offline': False,
                'label': 'آنلاین (گوگل) - صدا به سرور فرستاده می‌شود'}

    def listen_for_wake_word(self, wake_word="هی وینا"):
        """سازگاری با کد قبلی.

        تشخیص کلمه‌ی فعال‌سازی حالا از طریق گفتگوی زنده انجام می‌شود:
        VAD یک قطعه‌ی گفتار را جدا می‌کند، STT آفلاین آن را متن می‌کند و
        ``WakeWordMatcher`` بررسی می‌کند که کلمه‌ی فعال‌سازی در آن هست یا نه
        (به ``create_conversation(wake_word_enabled=True)`` مراجعه کنید).
        """
        conv = self._conversation
        return bool(conv and conv.wake_word_enabled and conv.is_running)

    def get_audio_levels(self):
        return self._audio_levels
