# -*- coding: utf-8 -*-
"""
ماژول مدیریت فضای ذخیره‌سازی وینا

اطلاعات مربوط به حجم پوشه‌ی مدل‌ها، حافظه‌ی مکالمات و کش، به‌همراه
عملیات پاک‌سازی کش و خروجی/ورودی گرفتن از مکالمات - برای صفحه‌ی
«تنظیمات > فضای ذخیره‌سازی».
"""

import os
import shutil
import tempfile


def _dir_size_bytes(path):
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def _human_size(num_bytes):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


class StorageManager:
    """مدیریت اطلاعات و عملیات فضای ذخیره‌سازی برنامه"""

    def __init__(self, memory=None):
        self.memory = memory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, 'models')
        self.memory_dir = os.path.join(self.base_dir, 'memory')
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'vina_cache')

    def get_storage_report(self):
        """گزارش کامل فضای اشغال‌شده توسط بخش‌های مختلف برنامه"""
        models_size = _dir_size_bytes(self.models_dir)
        memory_size = _dir_size_bytes(self.memory_dir)
        cache_size = _dir_size_bytes(self.cache_dir)

        return {
            'models_dir': self.models_dir,
            'models_size_bytes': models_size,
            'models_size_human': _human_size(models_size),
            'memory_size_bytes': memory_size,
            'memory_size_human': _human_size(memory_size),
            'cache_size_bytes': cache_size,
            'cache_size_human': _human_size(cache_size),
            'total_size_human': _human_size(models_size + memory_size + cache_size),
        }

    def clear_cache(self):
        """پاک کردن کامل پوشه‌ی کش موقت"""
        try:
            if os.path.isdir(self.cache_dir):
                shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            return True
        except OSError:
            return False

    def delete_model(self, model_filename):
        """حذف یک فایل مدل مشخص از پوشه‌ی models (برای آزاد کردن فضا)"""
        path = os.path.join(self.models_dir, model_filename)
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except OSError:
            return False

    def export_all_chats(self, file_path, username=None):
        """خروجی‌گیری کامل از مکالمات برای پشتیبان‌گیری (delegation به VinaMemory)"""
        if not self.memory:
            return False
        return self.memory.export_memory_to_file(file_path, username)

    def import_all_chats(self, file_path, username=None):
        """وارد کردن مکالمات از فایل پشتیبان (delegation به VinaMemory)"""
        if not self.memory:
            return False
        return self.memory.import_memory_from_file(file_path, username)
