# -*- coding: utf-8 -*-
"""
موتور تشخیص گفتار (STT) وینا - دو پیاده‌سازی قابل انتخاب

۱) ``VoskSTT``   (پیش‌فرض): کاملاً آفلاین. مدل فشرده‌ی Vosk روی دستگاه اجرا
   می‌شود، هیچ بایتی از صدای کاربر از گوشی خارج نمی‌شود. مدل در اولین اجرا
   دانلود می‌شود (فارسی ~۴۰MB، انگلیسی ~۴۰MB) و بعد از آن نیازی به اینترنت
   نیست.

۲) ``AndroidSTT`` (اختیاری): از android.speech.SpeechRecognizer استفاده
   می‌کند. دقت بالاتر، اما روی اکثر گوشی‌ها صدا به سرور گوگل فرستاده می‌شود.
   به همین دلیل پیش‌فرض *نیست* و کاربر باید صریحاً از تنظیمات فعالش کند.

هر دو کلاس یک interface مشترک دارند تا بقیه‌ی برنامه نداند کدام فعال است:

    engine.is_available() -> bool
    engine.start(on_partial, on_final, on_error) -> bool
    engine.feed(pcm_bytes)      # فقط Vosk؛ برای Android بی‌اثر است
    engine.stop()
    engine.name / engine.is_offline
"""

import json
import os
import threading

# مدل‌های آفلاین Vosk. اینها مدل‌های «small» هستند که مخصوص موبایل ساخته
# شده‌اند (نسخه‌های بزرگ‌تر ۱.۵GB+ و برای گوشی نامناسب‌اند).
VOSK_MODELS = {
    'fa': {
        'name': 'vosk-model-small-fa-0.42',
        'url': 'https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip',
        'size': 47 * 1024 * 1024,
        'label': 'فارسی (آفلاین)',
    },
    'en': {
        'name': 'vosk-model-small-en-us-0.15',
        'url': 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
        'size': 40 * 1024 * 1024,
        'label': 'English (offline)',
    },
}

SAMPLE_RATE = 16000


def get_vosk_models_dir():
    """پوشه‌ی نگه‌داری مدل‌های Vosk (قابل نوشتن روی اندروید و دسکتاپ)."""
    candidates = []
    try:
        from android.storage import app_storage_path  # type: ignore
        candidates.append(os.path.join(app_storage_path(), 'vosk'))
    except Exception:
        pass
    candidates.append(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'models', 'vosk')
    )
    candidates.append(os.path.expanduser('~/.vina/vosk'))

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            if os.access(path, os.W_OK):
                return path
        except Exception:
            continue
    return candidates[-1]


def find_vosk_model(lang='fa'):
    """اگر مدل زبان مورد نظر دانلود شده باشد، مسیرش را برمی‌گرداند."""
    info = VOSK_MODELS.get(lang)
    if not info:
        return None
    path = os.path.join(get_vosk_models_dir(), info['name'])
    # یک مدل معتبر Vosk همیشه پوشه‌ی `am` یا `graph` دارد
    if os.path.isdir(path) and (
        os.path.isdir(os.path.join(path, 'am')) or
        os.path.isdir(os.path.join(path, 'graph'))
    ):
        return path
    return None


class BaseSTT:
    """رابط مشترک موتورهای تشخیص گفتار."""

    name = 'base'
    is_offline = True

    def is_available(self):
        raise NotImplementedError

    def start(self, on_partial=None, on_final=None, on_error=None):
        raise NotImplementedError

    def feed(self, pcm_bytes):
        return None

    def stop(self):
        pass

    def close(self):
        self.stop()


class VoskSTT(BaseSTT):
    """تشخیص گفتار کاملاً آفلاین با Vosk (پیش‌فرض وینا).

    نکته‌ی معماری: Vosk خودش صدا را ضبط نمی‌کند؛ ما بایت‌های PCM را از
    ضبط‌کننده (AudioRecorder) می‌گیریم و با ``feed()`` به آن می‌دهیم. همین
    باعث می‌شود *همان* جریان صوتی هم‌زمان به VAD برود و بتوانیم barge-in
    را بدون باز کردن دوباره‌ی میکروفون پیاده کنیم.
    """

    name = 'vosk'
    is_offline = True

    def __init__(self, lang='fa'):
        self.lang = lang
        self._model = None
        self._recognizer = None
        self._lock = threading.Lock()
        self._on_partial = None
        self._on_final = None
        self._on_error = None
        self._last_partial = ''
        self.load_error = None

    # ------------------------------------------------------------------
    @staticmethod
    def _backend():
        """ماژول Vosk قابل استفاده را برمی‌گرداند (ctypes یا پکیج رسمی).

        اولویت با اتصال ctypes خودمان است (روی اندروید کار می‌کند)؛ روی
        دسکتاپ اگر پکیج رسمی pip نصب باشد از آن استفاده می‌شود.
        """
        from src import vosk_ctypes
        if vosk_ctypes.is_available():
            return vosk_ctypes
        try:
            import vosk
            return vosk
        except ImportError:
            return None

    def is_available(self):
        """آیا هم کتابخانه و هم مدل زبان حاضرند؟"""
        if find_vosk_model(self.lang) is None:
            self.load_error = 'مدل آفلاین دانلود نشده است'
            return False
        if self._backend() is None:
            self.load_error = 'کتابخانه‌ی تشخیص گفتار آفلاین در دسترس نیست'
            return False
        return True

    def load(self):
        """بارگذاری مدل در حافظه (کند است - در ترد پس‌زمینه صدا بزنید)."""
        with self._lock:
            if self._model is not None:
                return True
            model_path = find_vosk_model(self.lang)
            if not model_path:
                self.load_error = 'مدل آفلاین دانلود نشده است'
                return False
            backend = self._backend()
            if backend is None:
                self.load_error = 'کتابخانه‌ی تشخیص گفتار آفلاین در دسترس نیست'
                return False
            try:
                # خاموش کردن لاگ پرحجم Kaldi (نام تابع در دو پیاده‌سازی فرق دارد)
                for fn in ('SetLogLevel', 'set_log_level'):
                    if hasattr(backend, fn):
                        getattr(backend, fn)(-1)
                        break
                self._model = backend.Model(model_path)
                self._backend_mod = backend
                return True
            except Exception as exc:  # noqa: BLE001
                self.load_error = f'بارگذاری مدل آفلاین ناموفق بود: {exc}'
                self._model = None
                return False

    def start(self, on_partial=None, on_final=None, on_error=None):
        self._on_partial, self._on_final, self._on_error = on_partial, on_final, on_error
        self._last_partial = ''
        if not self.load():
            if on_error:
                on_error(self.load_error or 'موتور آفلاین در دسترس نیست')
            return False
        try:
            backend = getattr(self, '_backend_mod', None) or self._backend()
            self._recognizer = backend.KaldiRecognizer(self._model, SAMPLE_RATE)
            self._recognizer.SetWords(False)
            return True
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(f'شروع تشخیص گفتار ناموفق بود: {exc}')
            return False

    def feed(self, pcm_bytes):
        """یک قطعه PCM (16-bit mono @16kHz) را پردازش می‌کند.

        اگر جمله تمام شده باشد متن نهایی را برمی‌گرداند، وگرنه ``None``.
        """
        if not self._recognizer or not pcm_bytes:
            return None
        try:
            if self._recognizer.AcceptWaveform(pcm_bytes):
                text = json.loads(self._recognizer.Result()).get('text', '').strip()
                if text and self._on_final:
                    self._on_final(text)
                return text or None
            partial = json.loads(self._recognizer.PartialResult()).get('partial', '').strip()
            if partial and partial != self._last_partial:
                self._last_partial = partial
                if self._on_partial:
                    self._on_partial(partial)
        except Exception as exc:  # noqa: BLE001
            if self._on_error:
                self._on_error(f'خطا در پردازش صدا: {exc}')
        return None

    def final_result(self):
        """متن نهایی باقی‌مانده را بعد از پایان گفتار می‌گیرد."""
        if not self._recognizer:
            return ''
        try:
            text = json.loads(self._recognizer.FinalResult()).get('text', '').strip()
            if text and self._on_final:
                self._on_final(text)
            return text
        except Exception:
            return ''

    def stop(self):
        self._recognizer = None
        self._last_partial = ''

    def close(self):
        self.stop()
        with self._lock:
            self._model = None


class AndroidSTT(BaseSTT):
    """تشخیص گفتار با موتور داخلی اندروید (اختیاری - آنلاین).

    هشدار صادقانه: روی اکثر گوشی‌ها این API صدا را به سرور گوگل می‌فرستد.
    فقط وقتی استفاده می‌شود که کاربر آگاهانه در تنظیمات انتخابش کند.
    """

    name = 'android'
    is_offline = False

    def __init__(self, bridge=None, lang='fa-IR'):
        from src.android_bridge import AndroidBridge, is_android
        self.bridge = bridge or AndroidBridge()
        self._is_android = is_android()
        self.lang = lang
        self._active = False

    def is_available(self):
        return self._is_android

    def start(self, on_partial=None, on_final=None, on_error=None):
        if not self._is_android:
            if on_error:
                on_error('موتور آنلاین فقط روی اندروید در دسترس است')
            return False

        self._active = True

        def _result(text):
            self._active = False
            if on_final:
                on_final(text)

        def _error(msg):
            self._active = False
            if on_error:
                on_error(msg)

        self.bridge.listen_once(_result, _error, language=self.lang,
                                on_partial=on_partial)
        return True

    def stop(self):
        self._active = False
        try:
            self.bridge.stop_listening()
        except Exception:
            pass


def create_stt(prefer_offline=True, lang='fa', bridge=None):
    """موتور STT مناسب را می‌سازد، با بازگشت امن به گزینه‌ی دیگر.

    بازگشت: ``(engine, note)`` که ``note`` توضیح فارسی برای نمایش در UI است
    (مثلاً وقتی کاربر آفلاین خواسته اما مدل هنوز دانلود نشده).
    """
    if prefer_offline:
        engine = VoskSTT(lang=lang)
        if engine.is_available():
            return engine, None
        fallback = AndroidSTT(bridge=bridge, lang=f'{lang}-IR' if lang == 'fa' else 'en-US')
        if fallback.is_available():
            return fallback, ('حالت آفلاین در دسترس نیست ({}) - موقتاً از '
                              'موتور آنلاین استفاده می‌شود.'.format(engine.load_error))
        return engine, engine.load_error

    engine = AndroidSTT(bridge=bridge, lang=f'{lang}-IR' if lang == 'fa' else 'en-US')
    if engine.is_available():
        return engine, None
    offline = VoskSTT(lang=lang)
    if offline.is_available():
        return offline, 'موتور آنلاین در دسترس نیست - از حالت آفلاین استفاده می‌شود.'
    return engine, 'هیچ موتور تشخیص گفتاری در دسترس نیست'
