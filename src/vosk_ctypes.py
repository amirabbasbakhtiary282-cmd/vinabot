# -*- coding: utf-8 -*-
"""
اتصال مستقیم به libvosk.so از طریق ctypes (بدون cffi)

چرا این فایل به‌جای پکیج رسمی ``vosk`` پایتون؟
--------------------------------------------------------------------------
پکیج pip رسمی Vosk به **cffi** وابسته است و در زمان import، هدر C را با
کامپایلر پردازش می‌کند. این روی python-for-android شکننده است (به کامپایلر
در زمان اجرا روی گوشی نیاز دارد که وجود ندارد). اما خودِ ``libvosk.so`` یک
C ABI کاملاً ساده و پایدار دارد که ctypes بدون هیچ کامپایلی می‌تواند از آن
استفاده کند - دقیقاً همان کاری که برای llama.cpp هم انجام دادیم.

این ماژول همان چند تابعی را که واقعاً لازم داریم پوشش می‌دهد:
    vosk_model_new / vosk_model_free
    vosk_recognizer_new / vosk_recognizer_free
    vosk_recognizer_accept_waveform
    vosk_recognizer_result / partial_result / final_result
    vosk_set_log_level
"""

import ctypes
import os
import threading

_LIB_NAMES = ('libvosk.so', 'libvosk.so.1', 'vosk.dll', 'libvosk.dylib')

_lib = None
_lib_lock = threading.Lock()
_load_error = None


def _candidate_dirs():
    dirs = [os.environ.get('VINA_VOSK_LIB_DIR', '')]
    # روی اندروید p4a کتابخانه‌ها را در پوشه‌ی lib اپ نصب می‌کند و loader
    # سیستم خودش پیدایشان می‌کند، پس نام خالی هم امتحان می‌شود.
    dirs.append('')
    dirs.append(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'native', 'build'))
    return [d for d in dirs if d is not None]


def load_libvosk():
    """بارگذاری libvosk.so. بازگشت (lib یا None، پیام خطا یا None)."""
    global _lib, _load_error
    with _lib_lock:
        if _lib is not None:
            return _lib, None
        if _load_error is not None:
            return None, _load_error

        errors = []
        for directory in _candidate_dirs():
            for name in _LIB_NAMES:
                path = os.path.join(directory, name) if directory else name
                if directory and not os.path.exists(path):
                    continue
                try:
                    lib = ctypes.CDLL(path)
                    _setup_signatures(lib)
                    _lib = lib
                    return _lib, None
                except OSError as exc:
                    errors.append(str(exc))

        _load_error = ('کتابخانه‌ی تشخیص گفتار آفلاین (libvosk) پیدا نشد. '
                       'جزئیات: ' + ('; '.join(errors[-2:]) if errors else 'نامشخص'))
        return None, _load_error


def _setup_signatures(lib):
    lib.vosk_model_new.restype = ctypes.c_void_p
    lib.vosk_model_new.argtypes = [ctypes.c_char_p]
    lib.vosk_model_free.argtypes = [ctypes.c_void_p]

    lib.vosk_recognizer_new.restype = ctypes.c_void_p
    lib.vosk_recognizer_new.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.vosk_recognizer_free.argtypes = [ctypes.c_void_p]

    lib.vosk_recognizer_accept_waveform.restype = ctypes.c_int
    lib.vosk_recognizer_accept_waveform.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]

    for fn in ('vosk_recognizer_result', 'vosk_recognizer_partial_result',
               'vosk_recognizer_final_result'):
        getattr(lib, fn).restype = ctypes.c_char_p
        getattr(lib, fn).argtypes = [ctypes.c_void_p]

    lib.vosk_recognizer_reset.argtypes = [ctypes.c_void_p]

    try:
        lib.vosk_set_log_level.argtypes = [ctypes.c_int]
    except AttributeError:
        pass


def is_available():
    lib, _ = load_libvosk()
    return lib is not None


def set_log_level(level=-1):
    lib, _ = load_libvosk()
    if lib is None:
        return
    try:
        lib.vosk_set_log_level(level)
    except Exception:
        pass


class Model:
    """مدل زبانی Vosk (سنگین - یک بار بارگذاری و بارها استفاده شود)."""

    def __init__(self, model_path):
        lib, err = load_libvosk()
        if lib is None:
            raise RuntimeError(err)
        self._lib = lib
        handle = lib.vosk_model_new(model_path.encode('utf-8'))
        if not handle:
            raise RuntimeError(f'بارگذاری مدل آفلاین ناموفق بود: {model_path}')
        self._handle = ctypes.c_void_p(handle)

    def free(self):
        if getattr(self, '_handle', None):
            self._lib.vosk_model_free(self._handle)
            self._handle = None

    def __del__(self):
        try:
            self.free()
        except Exception:
            pass


class KaldiRecognizer:
    """تشخیص‌دهنده‌ی جریانی؛ API سازگار با پکیج رسمی vosk."""

    def __init__(self, model, sample_rate):
        if not isinstance(model, Model):
            raise TypeError('model باید نمونه‌ای از Model باشد')
        self._lib = model._lib
        handle = self._lib.vosk_recognizer_new(model._handle,
                                               ctypes.c_float(float(sample_rate)))
        if not handle:
            raise RuntimeError('ساخت تشخیص‌دهنده‌ی گفتار ناموفق بود')
        self._handle = ctypes.c_void_p(handle)

    def SetWords(self, enabled):  # noqa: N802 - سازگاری با API رسمی
        try:
            self._lib.vosk_recognizer_set_words(self._handle, 1 if enabled else 0)
        except AttributeError:
            pass

    def AcceptWaveform(self, data):  # noqa: N802
        """``True`` یعنی یک جمله کامل شد و نتیجه آماده است."""
        if not self._handle:
            return False
        return bool(self._lib.vosk_recognizer_accept_waveform(
            self._handle, data, len(data)))

    def _decode(self, raw):
        return raw.decode('utf-8', errors='replace') if raw else '{}'

    def Result(self):  # noqa: N802
        return self._decode(self._lib.vosk_recognizer_result(self._handle))

    def PartialResult(self):  # noqa: N802
        return self._decode(self._lib.vosk_recognizer_partial_result(self._handle))

    def FinalResult(self):  # noqa: N802
        return self._decode(self._lib.vosk_recognizer_final_result(self._handle))

    def Reset(self):  # noqa: N802
        if self._handle:
            self._lib.vosk_recognizer_reset(self._handle)

    def free(self):
        if getattr(self, '_handle', None):
            self._lib.vosk_recognizer_free(self._handle)
            self._handle = None

    def __del__(self):
        try:
            self.free()
        except Exception:
            pass
