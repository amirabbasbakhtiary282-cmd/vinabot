# -*- coding: utf-8 -*-
"""
لایه‌ی سازگاری با کد قدیمی (Backward-compatibility shim)

تمام کامپوننت‌های بصری واقعی وینا اکنون در ``src/design_system`` قرار
دارند (معماری تمیزتر: tokens/typography/animations/components جدا).
این فایل صرفاً برای این نگه‌داشته شده که فایل‌های موجود (main.py و vina.kv)
که قبلاً ``from src.ui import X`` یا ``import src.ui`` می‌نوشتند، بدون
تغییر ادامه به کار کنند. کد جدید باید مستقیماً از ``src.design_system``
یا ``src.theme`` استفاده کند.
"""

from src.design_system import *  # noqa: F401,F403
from src.design_system import theme  # noqa: F401
