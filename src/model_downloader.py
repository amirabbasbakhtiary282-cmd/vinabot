# -*- coding: utf-8 -*-
"""
دانلودکننده مدل‌های هوش مصنوعی وینا

نکته‌ی مهم: نسخه‌ی قبلی این فایل به‌صورت پیش‌فرض مدل Gemma-2-9B با حجم
حدود ۴.۵ گیگابایت را پیشنهاد می‌داد که روی اکثر گوشی‌های موبایل (چه از نظر
فضای ذخیره‌سازی، چه از نظر RAM برای بارگذاری، و چه از نظر سرعت استنتاج)
عملاً غیرقابل استفاده است. این نسخه چند مدل سبک و واقعاً مناسب برای اجرای
آفلاین روی گوشی را پیشنهاد می‌دهد؛ اما همان‌طور که در src/brain.py هم آمده،
موتور وینا با *هر* فایل GGUF معتبری که در پوشه‌ی models/ قرار بگیرد کار
می‌کند - محدود به این لیست نیست.

هم‌چنین ماژول Vosk (تشخیص گفتار آفلاین) از این‌جا حذف شده، چون STT اکنون
از طریق android.speech.SpeechRecognizer داخلی سیستم‌عامل انجام می‌شود که
نیازی به دانلود هیچ مدلی ندارد (به src/voice.py و src/android_bridge.py
مراجعه کنید).
"""

import os
import threading


class ModelDownloader:
    """کلاس دانلود مدل‌های زبانی سبک (GGUF)"""

    # مدل‌های پیشنهادی: همگی سبک، کوانتایز و مناسب اجرای CPU-only روی گوشی.
    # اندازه‌ها تقریبی‌اند و به‌عنوان راهنما برای کاربر نمایش داده می‌شوند.
    RECOMMENDED_MODELS = {
        'qwen2.5-0.5b-instruct-q4_k_m.gguf': {
            'url': 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf',
            'size': 400 * 1024 * 1024,
            'description': 'Qwen2.5-0.5B-Instruct (سبک‌ترین، مناسب گوشی‌های ضعیف)',
        },
        'qwen2.5-1.5b-instruct-q4_k_m.gguf': {
            'url': 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf',
            'size': 1024 * 1024 * 1024,
            'description': 'Qwen2.5-1.5B-Instruct (تعادل خوب بین کیفیت و سرعت)',
        },
        'phi-3-mini-4k-instruct-q4.gguf': {
            'url': 'https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf',
            'size': 2 * 1024 * 1024 * 1024,
            'description': 'Phi-3-mini-4k-Instruct (کیفیت بالاتر، نیاز به گوشی قوی‌تر)',
        },
    }

    def __init__(self):
        self.models_dir = self._get_models_dir()
        self.progress_callback = None
        self.status_callback = None
        self._cancel_event = threading.Event()

    def _get_models_dir(self):
        """مسیر پوشه‌ی مدل‌ها"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models'),
            '/data/data/org.vinabot/files/models',
            os.path.expanduser('~/.vina/models'),
        ]
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except Exception:
                continue
        return possible_paths[0]

    def list_installed_models(self):
        """لیست تمام فایل‌های GGUF موجود در پوشه‌ی مدل‌ها"""
        if not os.path.isdir(self.models_dir):
            return []
        return sorted(
            f for f in os.listdir(self.models_dir) if f.lower().endswith('.gguf')
        )

    def has_any_model(self):
        return len(self.list_installed_models()) > 0

    def cancel(self):
        """درخواست لغو دانلود در حال انجام"""
        self._cancel_event.set()

    def download_model(self, model_key):
        """دانلود یک مدل از لیست پیشنهادی"""
        if model_key not in self.RECOMMENDED_MODELS:
            if self.status_callback:
                self.status_callback(f"مدل ناشناخته: {model_key}")
            return False

        info = self.RECOMMENDED_MODELS[model_key]
        path = os.path.join(self.models_dir, model_key)

        if os.path.exists(path):
            if self.status_callback:
                self.status_callback(f"{info['description']} از قبل نصب شده است.")
            return True

        self._cancel_event.clear()
        temp_path = path + '.downloading'

        try:
            import requests

            if self.status_callback:
                self.status_callback(f"در حال دانلود {info['description']}...")

            response = requests.get(info['url'], stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', info['size']))
            downloaded = 0

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if self._cancel_event.is_set():
                        raise InterruptedError("دانلود توسط کاربر لغو شد")
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.progress_callback and total_size:
                            progress = (downloaded / total_size) * 100
                            self.progress_callback(model_key, progress)

            os.rename(temp_path, path)

            if self.status_callback:
                self.status_callback(f"دانلود {info['description']} تکمیل شد.")
            return True

        except Exception as exc:
            if self.status_callback:
                self.status_callback(f"خطا در دانلود: {str(exc)[:100]}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            return False

    def get_recommended_list(self):
        """اطلاعات مدل‌های پیشنهادی برای نمایش در رابط کاربری"""
        installed = set(self.list_installed_models())
        result = []
        for key, info in self.RECOMMENDED_MODELS.items():
            result.append({
                'key': key,
                'description': info['description'],
                'size_mb': round(info['size'] / (1024 * 1024)),
                'installed': key in installed,
            })
        return result
