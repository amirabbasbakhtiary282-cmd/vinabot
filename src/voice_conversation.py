# -*- coding: utf-8 -*-
"""
گفتگوی صوتی دوطرفه‌ی زنده (Phase A)

این کلاس همه‌ی قطعات را به هم وصل می‌کند:

    میکروفون ──> VAD ──> STT ──> LLM (جریانی) ──> تکه‌کننده‌ی جمله ──> TTS
                  │                                                     │
                  └──────────── قطع کردن وسط صحبت (barge-in) ◄──────────┘

نکات طراحی:
- همه‌چیز روی ترد پس‌زمینه اجرا می‌شود؛ اطلاع‌رسانی به رابط کاربری از طریق
  callbackهاست و مصرف‌کننده باید خودش آن‌ها را به ترد UI ببرد
  (در Kivy با ``Clock.schedule_once``).
- «قطع کردن وسط صحبت» یعنی وقتی وینا در حال حرف زدن است و کاربر شروع به
  صحبت می‌کند، VAD این را می‌فهمد، TTS بلافاصله قطع می‌شود و تولید مدل هم
  لغو می‌شود تا کاربر منتظر نماند.
- برای جلوگیری از قطع کاذب توسط *صدای خود وینا*، در حالت گفتن، آستانه‌ی VAD
  بالاتر گرفته می‌شود و یک بازه‌ی کوتاه بی‌توجهی (guard) بعد از شروع گفتن
  اعمال می‌شود.
"""

import threading
import time

from src.speech_pipeline import EnergyVAD, SentenceChunker, WakeWordMatcher

# حالت‌های ماشین وضعیت گفتگو
STATE_IDLE = 'idle'            # غیرفعال
STATE_LISTENING = 'listening'  # منتظر/در حال شنیدن کاربر
STATE_THINKING = 'thinking'    # مدل در حال تولید پاسخ
STATE_SPEAKING = 'speaking'    # وینا در حال حرف زدن

# بعد از شروع گفتن وینا، این مدت به VAD بی‌توجهی می‌شود تا اولین سیلاب‌های
# خود TTS باعث قطع فوری نشوند.
BARGE_IN_GUARD_SEC = 0.6

# در حالت گفتن، انرژی کاربر باید این‌قدر بیشتر از آستانه‌ی عادی باشد تا
# قطع کردن به‌حساب بیاید (جلوگیری از قطع با صدای بلندگوی خود گوشی).
BARGE_IN_SENSITIVITY = 2.0


class VoiceConversation:
    """مدیر گفتگوی صوتی زنده و دوطرفه."""

    def __init__(self, stt=None, tts_speak=None, tts_stop=None,
                 llm_generate=None, recorder=None,
                 wake_word_enabled=False, barge_in_enabled=True):
        """
        پارامترها همگی تزریق‌شونده‌اند تا این کلاس کاملاً قابل تست باشد:

        - ``stt``          : شیئی با interface موتور STT (src/stt_engine.py)
        - ``tts_speak``    : تابع ``speak(text) -> None`` (بلاک‌کننده یا نه)
        - ``tts_stop``     : تابع قطع فوری گفتار
        - ``llm_generate`` : ``generate(text, on_token) -> str``
        - ``recorder``     : ضبط‌کننده (src/audio_recorder.py)
        """
        self.stt = stt
        self.tts_speak = tts_speak or (lambda t: None)
        self.tts_stop = tts_stop or (lambda: None)
        self.llm_generate = llm_generate
        self.recorder = recorder

        self.vad = EnergyVAD()
        self.chunker = SentenceChunker()
        self.wake_matcher = WakeWordMatcher()
        self.wake_word_enabled = wake_word_enabled
        self.barge_in_enabled = barge_in_enabled

        self.state = STATE_IDLE
        self._lock = threading.RLock()
        self._interrupted = threading.Event()
        self._running = False
        self._speaking_since = 0.0
        self._turn_thread = None

        # callbackهای رابط کاربری (همه اختیاری)
        self.on_state_change = None
        self.on_partial_transcript = None
        self.on_final_transcript = None
        self.on_response_token = None
        self.on_response_done = None
        self.on_error = None
        self.on_level = None

    # ------------------------------------------------------------------
    # ابزار داخلی
    # ------------------------------------------------------------------
    def _set_state(self, state):
        with self._lock:
            if self.state == state:
                return
            self.state = state
        self._emit(self.on_state_change, state)

    @staticmethod
    def _emit(cb, *args):
        if cb is None:
            return
        try:
            cb(*args)
        except Exception as exc:  # noqa: BLE001
            print(f'خطا در callback رابط کاربری: {exc}')

    def _error(self, message):
        self._emit(self.on_error, message)

    # ------------------------------------------------------------------
    # شروع و پایان
    # ------------------------------------------------------------------
    def start(self):
        """شروع گوش دادن پیوسته."""
        with self._lock:
            if self._running:
                return True
            self._running = True

        self.vad.reset()
        self._interrupted.clear()

        if self.stt is not None:
            self.stt.start(
                on_partial=lambda t: self._emit(self.on_partial_transcript, t),
                on_final=None,   # نتیجه‌ی نهایی را خودمان در پایان گفتار می‌گیریم
                on_error=self._error,
            )

        if self.recorder is not None:
            ok = self.recorder.start(self._on_audio_frame, on_error=self._error)
            if not ok:
                with self._lock:
                    self._running = False
                return False

        self._set_state(STATE_LISTENING)
        return True

    def stop(self):
        """پایان کامل گفتگو و آزادسازی میکروفون."""
        with self._lock:
            self._running = False
        self._interrupted.set()
        try:
            self.tts_stop()
        except Exception:
            pass
        if self.recorder is not None:
            self.recorder.stop()
        if self.stt is not None:
            self.stt.stop()
        self._set_state(STATE_IDLE)

    @property
    def is_running(self):
        return self._running

    # ------------------------------------------------------------------
    # مسیر صدا
    # ------------------------------------------------------------------
    def _on_audio_frame(self, pcm_bytes):
        """برای هر فریم صوتی از میکروفون صدا زده می‌شود (ترد ضبط)."""
        if not self._running:
            return

        from src.audio_recorder import pcm16_to_float
        samples = pcm16_to_float(pcm_bytes)
        if not samples:
            return

        event = self.vad.process_frame(samples)
        self._emit(self.on_level, self.vad.last_rms)

        state = self.state

        # --- حالت گفتن وینا: بررسی قطع کردن توسط کاربر ---
        if state in (STATE_SPEAKING, STATE_THINKING):
            if self.barge_in_enabled and self._should_barge_in(samples):
                self._trigger_barge_in()
            return

        # --- حالت شنیدن: صدا را به STT بده ---
        if state == STATE_LISTENING and self.stt is not None:
            self.stt.feed(pcm_bytes)

        if event == 'speech_end' and state == STATE_LISTENING:
            self._finish_user_turn()

    def _should_barge_in(self, samples):
        """آیا کاربر واقعاً وسط حرف وینا صحبت کرده؟"""
        # بازه‌ی محافظ بعد از شروع گفتن (تا خود TTS باعث قطع نشود)
        if time.monotonic() - self._speaking_since < BARGE_IN_GUARD_SEC:
            return False
        level = self.vad.rms(samples)
        return level > self.vad.threshold * BARGE_IN_SENSITIVITY

    def _trigger_barge_in(self):
        """کاربر وسط حرف وینا صحبت کرد: فوراً ساکت شو و دوباره گوش بده."""
        self._interrupted.set()
        try:
            self.tts_stop()
        except Exception:
            pass
        self.chunker.reset()
        self.vad.reset()
        self._set_state(STATE_LISTENING)

    # ------------------------------------------------------------------
    # نوبت کاربر -> نوبت وینا
    # ------------------------------------------------------------------
    def _finish_user_turn(self):
        """کاربر حرفش تمام شد: متن نهایی را بگیر و پاسخ بساز."""
        text = ''
        if self.stt is not None:
            getter = getattr(self.stt, 'final_result', None)
            if callable(getter):
                text = getter() or ''

        text = (text or '').strip()
        if not text:
            self.vad.reset()
            return

        # اگر حالت کلمه‌ی فعال‌سازی روشن است، بدون آن پاسخ نده
        if self.wake_word_enabled:
            command = self.wake_matcher.match(text)
            if command is None:
                self.vad.reset()
                return
            if command == '':
                # فقط «هی وینا» گفته شد: منتظر دستور بمان
                self._emit(self.on_final_transcript, text)
                self.vad.reset()
                return
            text = command

        self._emit(self.on_final_transcript, text)
        self._start_response(text)

    def _start_response(self, user_text):
        """تولید و گفتن پاسخ در ترد جدا (تا ترد صدا بلاک نشود)."""
        self._interrupted.clear()
        self._set_state(STATE_THINKING)
        self._turn_thread = threading.Thread(
            target=self._respond, args=(user_text,), daemon=True,
            name='VinaResponse')
        self._turn_thread.start()

    def _respond(self, user_text):
        """LLM جریانی -> تکه‌کردن جمله -> TTS، با پشتیبانی از قطع شدن."""
        self.chunker.reset()
        spoken_any = False
        full_parts = []

        def on_token(piece):
            nonlocal spoken_any
            if self._interrupted.is_set() or not self._running:
                return False  # درخواست توقف تولید

            full_parts.append(piece)
            self._emit(self.on_response_token, piece)

            for sentence in self.chunker.feed(piece):
                if self._interrupted.is_set() or not self._running:
                    return False
                if not spoken_any:
                    spoken_any = True
                    self._speaking_since = time.monotonic()
                    self._set_state(STATE_SPEAKING)
                self._speak(sentence)
            return True

        try:
            if self.llm_generate is None:
                raise RuntimeError('موتور پاسخ‌گویی متصل نیست')
            self.llm_generate(user_text, on_token)
        except Exception as exc:  # noqa: BLE001
            self._error(f'خطا در تولید پاسخ: {exc}')
            self._set_state(STATE_LISTENING)
            return

        # جمله‌ی ناتمام باقی‌مانده را هم بگو
        if not self._interrupted.is_set() and self._running:
            for sentence in self.chunker.flush():
                if self._interrupted.is_set():
                    break
                if not spoken_any:
                    spoken_any = True
                    self._speaking_since = time.monotonic()
                    self._set_state(STATE_SPEAKING)
                self._speak(sentence)

        self._emit(self.on_response_done, ''.join(full_parts))

        # برگشت به حالت شنیدن برای نوبت بعدی گفتگو
        if self._running:
            self.vad.reset()
            if self.stt is not None:
                self.stt.stop()
                self.stt.start(
                    on_partial=lambda t: self._emit(self.on_partial_transcript, t),
                    on_final=None, on_error=self._error)
            self._set_state(STATE_LISTENING)

    def _speak(self, sentence):
        if self._interrupted.is_set() or not self._running:
            return
        try:
            self.tts_speak(sentence)
        except Exception as exc:  # noqa: BLE001
            self._error(f'خطا در گفتار: {exc}')

    # ------------------------------------------------------------------
    # حالت فشار-برای-صحبت (push to talk)
    # ------------------------------------------------------------------
    def push_to_talk_start(self):
        """کاربر دکمه را نگه داشت: هر چیزی در حال گفتن است قطع شود."""
        self._interrupted.set()
        try:
            self.tts_stop()
        except Exception:
            pass
        self.vad.reset()
        self.chunker.reset()
        if self.stt is not None:
            self.stt.stop()
            self.stt.start(
                on_partial=lambda t: self._emit(self.on_partial_transcript, t),
                on_final=None, on_error=self._error)
        self._set_state(STATE_LISTENING)

    def push_to_talk_stop(self):
        """کاربر دکمه را رها کرد: همین حالا پاسخ بده."""
        if self.state == STATE_LISTENING:
            self._finish_user_turn()
