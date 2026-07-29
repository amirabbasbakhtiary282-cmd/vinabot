# -*- coding: utf-8 -*-
"""
موتور استنتاج زبانی وینا - بدون وابستگی به llama-cpp-python

این ماژول به‌جای llama-cpp-python (که برای اندروید/p4a قابل اعتماد نیست)
از یک لایه‌ی نازک C (native/vina_llm.cpp) روی سورس رسمی llama.cpp استفاده
می‌کند. آن لایه در زمان ساخت APK با NDK اندروید کامپایل و به‌صورت
``libvina_llm.so`` در کنار ``libllama.so`` و ``libggml*.so`` داخل APK
قرار می‌گیرد؛ این پایتون فقط از طریق ``ctypes`` با آن صحبت می‌کند.
"""

import ctypes
import os
import threading
import time


class LlmLoadError(Exception):
    pass


class LlmEngine:
    """پوششی نازک و ایمن روی libvina_llm.so"""

    def __init__(self):
        self._lib = None
        self._handle = None
        self._lock = threading.Lock()
        self._cancel_flag = ctypes.c_int(0)
        self.model_path = None
        self.loaded = False
        self.load_error = None
        self.last_tokens_per_sec = 0.0
        self.n_ctx = 0

    # ------------------------------------------------------------------
    def _find_lib_dir(self):
        """پیدا کردن پوشه‌ای که libvina_llm.so و وابستگی‌هایش در آن هستند.

        روی اندروید این فایل‌ها توسط python-for-android در کنار سایر
        کتابخانه‌های native برنامه نصب می‌شوند و از طریق مسیر پیش‌فرض
        بارگذاری کتابخانه‌های اندروید (lib dir اپ) در دسترس‌اند، بنابراین
        نیازی به مسیر دستی نیست. برای دسکتاپ (توسعه/تست) از یک پوشه‌ی
        مشخص در کنار پروژه استفاده می‌کنیم.
        """
        candidates = [
            os.environ.get('VINA_LLM_LIB_DIR', ''),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'native', 'build'),
        ]
        for c in candidates:
            if c and os.path.exists(os.path.join(c, 'libvina_llm.so')):
                return c
        return None

    def _load_native_lib(self):
        if self._lib is not None:
            return True

        lib_dir = self._find_lib_dir()
        if not lib_dir:
            # روی اندروید کتابخانه‌ها در مسیر جستجوی پیش‌فرض سیستم هستند
            # (p4a آن‌ها را در پوشه‌ی lib اپ نصب می‌کند)، پس مستقیم تلاش می‌کنیم.
            try:
                ctypes.CDLL('libggml-base.so', mode=ctypes.RTLD_GLOBAL)
                ctypes.CDLL('libggml-cpu.so', mode=ctypes.RTLD_GLOBAL)
                ctypes.CDLL('libggml.so', mode=ctypes.RTLD_GLOBAL)
                ctypes.CDLL('libllama.so', mode=ctypes.RTLD_GLOBAL)
                self._lib = ctypes.CDLL('libvina_llm.so')
            except OSError as exc:
                self.load_error = f"کتابخانه‌ی موتور هوش مصنوعی پیدا نشد: {exc}"
                return False
        else:
            try:
                for dep in ('libggml-base.so', 'libggml-cpu.so', 'libggml.so', 'libllama.so'):
                    path = os.path.join(lib_dir, dep)
                    if os.path.exists(path):
                        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                self._lib = ctypes.CDLL(os.path.join(lib_dir, 'libvina_llm.so'))
            except OSError as exc:
                self.load_error = f"کتابخانه‌ی موتور هوش مصنوعی پیدا نشد: {exc}"
                return False

        self._setup_signatures()
        self._lib.vina_llm_backend_init()
        try:
            self._lib.vina_llm_set_verbose(0)
        except AttributeError:
            pass
        return True

    def _setup_signatures(self):
        lib = self._lib
        lib.vina_llm_load.restype = ctypes.c_void_p
        lib.vina_llm_load.argtypes = [
            ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        lib.vina_llm_free.argtypes = [ctypes.c_void_p]
        lib.vina_llm_n_ctx.restype = ctypes.c_int
        lib.vina_llm_n_ctx.argtypes = [ctypes.c_void_p]
        lib.vina_llm_reset_context.argtypes = [ctypes.c_void_p]
        lib.vina_llm_count_tokens.restype = ctypes.c_int
        lib.vina_llm_count_tokens.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.vina_llm_generate.restype = ctypes.c_int
        lib.vina_llm_generate.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_float,
            ctypes.c_float, ctypes.c_int, ctypes.c_float, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
        ]
        lib.vina_llm_last_error.restype = ctypes.c_char_p
        lib.vina_llm_last_error.argtypes = [ctypes.c_void_p]
        lib.vina_llm_set_verbose.argtypes = [ctypes.c_int]

    # ------------------------------------------------------------------
    def load(self, model_path, n_ctx=2048, n_threads=4):
        """بارگذاری مدل GGUF. بازگشت True/False."""
        with self._lock:
            if not os.path.exists(model_path):
                self.load_error = f"فایل مدل پیدا نشد: {model_path}"
                self.loaded = False
                return False

            if not self._load_native_lib():
                self.loaded = False
                return False

            err_buf = ctypes.create_string_buffer(512)
            handle = self._lib.vina_llm_load(
                model_path.encode('utf-8'), n_ctx, n_threads, err_buf, 512
            )
            if not handle:
                self.load_error = err_buf.value.decode('utf-8', errors='replace')
                self.loaded = False
                return False

            self._handle = handle
            self.model_path = model_path
            self.loaded = True
            self.load_error = None
            self.n_ctx = self._lib.vina_llm_n_ctx(handle)
            return True

    def unload(self):
        with self._lock:
            if self._handle and self._lib:
                self._lib.vina_llm_free(self._handle)
            self._handle = None
            self.loaded = False

    def reset_context(self):
        """پاک کردن حافظه‌ی مکالمه‌ی مدل (KV cache) - مثلاً هنگام شروع چت جدید"""
        if self._handle and self._lib:
            self._lib.vina_llm_reset_context(self._handle)

    def count_tokens(self, text):
        if not self._handle:
            return -1
        return self._lib.vina_llm_count_tokens(self._handle, text.encode('utf-8'))

    def cancel(self):
        """درخواست توقف تولید در حال انجام (thread-safe)"""
        self._cancel_flag.value = 1

    def generate(self, prompt, max_tokens=256, temperature=0.7, top_p=0.9,
                 top_k=40, repeat_penalty=1.1, stop=None, out_buf_size=8192):
        """تولید پاسخ برای prompt. Blocking - باید در ترد جداگانه فراخوانی شود."""
        if not self.loaded or not self._handle:
            raise LlmLoadError(self.load_error or "مدل بارگذاری نشده است")

        with self._lock:
            self._cancel_flag.value = 0
            out_buf = ctypes.create_string_buffer(out_buf_size)
            stop_bytes = stop.encode('utf-8') if stop else None

            start_time = time.monotonic()
            n = self._lib.vina_llm_generate(
                self._handle,
                prompt.encode('utf-8'),
                max_tokens,
                ctypes.c_float(temperature),
                ctypes.c_float(top_p),
                top_k,
                ctypes.c_float(repeat_penalty),
                stop_bytes,
                out_buf,
                out_buf_size,
                ctypes.byref(self._cancel_flag),
            )
            elapsed = max(1e-6, time.monotonic() - start_time)

            if n < 0:
                err = self._lib.vina_llm_last_error(self._handle)
                err_text = err.decode('utf-8', errors='replace') if err else "خطای ناشناخته"
                raise RuntimeError(f"خطا در تولید پاسخ (کد {n}): {err_text}")

            result_text = out_buf.value.decode('utf-8', errors='replace')
            approx_tokens = self.count_tokens(result_text)
            approx_tokens = approx_tokens if approx_tokens and approx_tokens > 0 else max(1, len(result_text) // 4)
            self.last_tokens_per_sec = approx_tokens / elapsed

            return result_text
