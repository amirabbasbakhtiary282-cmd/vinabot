# -*- coding: utf-8 -*-
"""
دانلودکننده مدل‌های هوش مصنوعی وینا
دانلود خودکار مدل‌ها پس از نصب برنامه
"""

import os
import sys
import json
import hashlib
import threading
import time


class ModelDownloader:
    """کلاس دانلود مدل‌ها"""

    MODELS = {
        'gemma-2-9b-q4_k_m.gguf': {
            'url': 'https://huggingface.co/google/gemma-2-9b-it-GGUF/resolve/main/gemma-2-9b-it-Q4_K_M.gguf',
            'size': 4.5 * 1024 * 1024 * 1024,
            'sha256': '',
            'description': 'مدل زبانی Gemma-2-9B کوانتایز ۴ بیتی',
            'required': True,
        },
        'vosk-model-small-fa': {
            'url': 'https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip',
            'size': 50 * 1024 * 1024,
            'sha256': '',
            'description': 'مدل تشخیص گفتار فارسی Vosk',
            'required': True,
            'zip': True,
        },
        'vosk-model-small-fa.zip': {
            'url': 'https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip',
            'size': 50 * 1024 * 1024,
            'sha256': '',
            'description': 'مدل تشخیص گفتار فارسی Vosk (فایل فشرده)',
            'required': True,
        }
    }

    def __init__(self):
        self.models_dir = self._get_models_dir()
        self.progress_callback = None
        self.status_callback = None

    def _get_models_dir(self):
        """مسیر پوشه مدل‌ها"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'),
            '/data/data/org.vinabot/files/models',
            os.path.expanduser('~/.vin/models'),
        ]
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except Exception:
                continue
        return possible_paths[0]

    def check_models(self):
        """بررسی مدل‌های موجود"""
        status = {}
        for name, info in self.MODELS.items():
            if name.endswith('.zip'):
                continue
            path = os.path.join(self.models_dir, name)
            status[name] = {
                'exists': os.path.exists(path),
                'size': os.path.getsize(path) if os.path.exists(path) else 0,
                'required': info['required'],
                'description': info['description']
            }
        return status

    def download_all(self):
        """دانلود تمام مدل‌ها"""
        threads = []
        for name, info in self.MODELS.items():
            if name.endswith('.zip'):
                continue
            path = os.path.join(self.models_dir, name)
            if not os.path.exists(path):
                t = threading.Thread(
                    target=self.download_model,
                    args=(name,),
                    daemon=True
                )
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

    def download_model(self, name):
        """دانلود یک مدل"""
        if name not in self.MODELS:
            return False

        info = self.MODELS[name]
        path = os.path.join(self.models_dir, name)

        if os.path.exists(path):
            return True

        try:
            import requests

            if self.status_callback:
                self.status_callback(f"در حال دانلود {info['description']}...")

            response = requests.get(info['url'], stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', info['size']))
            downloaded = 0

            temp_path = path + '.downloading'

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if self.progress_callback:
                            progress = (downloaded / total_size) * 100
                            self.progress_callback(name, progress)

            os.rename(temp_path, path)

            if self.status_callback:
                self.status_callback(f"دانلود {info['description']} تکمیل شد.")

            return True

        except Exception as e:
            if self.status_callback:
                self.status_callback(f"خطا در دانلود {name}: {str(e)[:50]}")

            temp_path = path + '.downloading'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            return False

    def download_vosk_model(self):
        """دانلود مدل Vosk با استخراج"""
        vosk_dir = os.path.join(self.models_dir, 'vosk-model-small-fa')
        if os.path.exists(vosk_dir):
            return True

        zip_path = os.path.join(self.models_dir, 'vosk-model-small-fa.zip')

        if not os.path.exists(zip_path):
            success = self.download_model('vosk-model-small-fa')
            if not success:
                return False

        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.models_dir)

            extracted = os.path.join(self.models_dir, 'vosk-model-small-fa-0.5')
            if os.path.exists(extracted):
                os.rename(extracted, vosk_dir)

            return True
        except Exception:
            return False

    def get_total_size(self):
        """محاسبه حجم کل مدل‌ها"""
        total = 0
        for name, info in self.MODELS.items():
            if not name.endswith('.zip'):
                total += info['size']
        return total

    def get_downloaded_size(self):
        """محاسبه حجم دانلود شده"""
        total = 0
        for name in self.MODELS:
            if name.endswith('.zip'):
                continue
            path = os.path.join(self.models_dir, name)
            if os.path.exists(path):
                total += os.path.getsize(path)
        return total


def download_models_gui():
    """رابط گرافیکی ساده برای دانلود مدل‌ها"""
    downloader = ModelDownloader()

    def on_progress(name, progress):
        print(f"  {name}: {progress:.1f}%")

    def on_status(status):
        print(f"  [وضعیت] {status}")

    downloader.progress_callback = on_progress
    downloader.status_callback = on_status

    status = downloader.check_models()
    print("\nوضعیت مدل‌ها:")
    for name, info in status.items():
        status_text = "✓ موجود" if info['exists'] else "✗ نیاز به دانلود"
        print(f"  {info['description']}: {status_text}")

    missing = [n for n, s in status.items() if not s['exists'] and s['required']]
    if missing:
        print(f"\nمدل‌های مورد نیاز: {len(missing)}")
        print(f"حجم کل دانلود: {downloader.get_total_size() / (1024**3):.1f} GB")

        confirm = input("\nآیا می‌خواهید مدل‌ها را دانلود کنید؟ (y/n): ")
        if confirm.lower() == 'y':
            downloader.download_all()
            print("دانلود تکمیل شد!")
    else:
        print("\nهمه مدل‌ها موجود هستند.")


if __name__ == '__main__':
    download_models_gui()
