# -*- coding: utf-8 -*-
"""
ماژول صدای وینا: تشخیص گفتار (STT) و گویش متن (TTS)

پیاده‌سازی واقعی:
- روی اندروید: از android.speech.SpeechRecognizer و android.speech.tts.TextToSpeech
  (هر دو API رسمی و داخلی سیستم‌عامل) از طریق pyjnius استفاده می‌شود.
- خارج از اندروید (مثلاً هنگام توسعه روی دسکتاپ): از ورودی/خروجی متنی به
  عنوان جایگزین امن استفاده می‌شود تا برنامه کرش نکند.

توجه: کتابخانه‌ی Vosk به دلیل نیاز به کراس‌کامپایل پیچیده برای اندروید و
عدم پایداری در بیلدهای p4a از این پروژه حذف شده و به‌جای آن از موتور
تشخیص گفتار داخلی خود اندروید استفاده می‌شود که روی همه‌ی گوشی‌ها در
دسترس است و نیازی به دانلود مدل جداگانه ندارد.
"""

import queue

from src.android_bridge import AndroidBridge, is_android


class VinaVoice:
    """کلاس مدیریت صدا برای وینا"""

    def __init__(self):
        self.is_android = is_android()
        self.bridge = AndroidBridge()
        self.isListening = False
        self._audio_levels = [0] * 30

        if self.is_android:
            self.bridge.set_tts_language_fa()

    # ------------------------------------------------------------------
    def speak(self, text):
        """گویش متن با موتور TTS"""
        if not text:
            return False
        return self.bridge.speak(text)

    def stop_speaking(self):
        self.bridge.stop_speaking()

    def shutdown(self):
        self.bridge.shutdown_tts()

    # ------------------------------------------------------------------
    def listen(self, timeout=10, on_partial=None):
        """گوش می‌دهد و متن تشخیص داده‌شده را به صورت synchronous برمی‌گرداند.

        این متد باید در یک ترد جداگانه (نه ترد UI) فراخوانی شود چون منتظر
        نتیجه می‌ماند.
        """
        if not self.is_android:
            return self._listen_text_fallback()

        result_queue = queue.Queue()

        def on_result(text):
            result_queue.put(('ok', text))

        def on_error(message):
            result_queue.put(('error', message))

        self.isListening = True
        self.bridge.listen_once(on_result, on_error, language='fa-IR', timeout_sec=timeout)

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

    def _listen_text_fallback(self):
        """ورودی متنی جایگزین (فقط برای اجرای دسکتاپ/توسعه)"""
        try:
            text = input("پیام خود را بنویسید: ")
            return text.strip() if text.strip() else None
        except (EOFError, KeyboardInterrupt):
            return None

    def listen_for_wake_word(self, wake_word="هی وینا"):
        """تشخیص کلمه‌ی فعال‌سازی.

        توجه صادقانه: تشخیص مداوم کلمه‌ی فعال‌سازی (always-on wake word)
        نیازمند یک موتور تشخیص گفتار آفلاین سبک (مثل Porcupine یا مدل
        فشرده‌ی محلی) است که دائم در پس‌زمینه اجرا شود. android.speech.
        SpeechRecognizer داخلی برای این منظور طراحی نشده (هر بار به‌صورت
        یک‌باره کار می‌کند و پنجره‌ی محدودی دارد)، و اجرای مداوم آن باتری
        را به‌سرعت تخلیه می‌کند. به همین دلیل این قابلیت در این نسخه غیرفعال
        است تا رفتار نادرست یا گمراه‌کننده به کاربر نشان داده نشود.
        """
        return False

    def get_audio_levels(self):
        return self._audio_levels
