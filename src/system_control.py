# -*- coding: utf-8 -*-
"""
ماژول کنترل سیستم گوشی

این نسخه از ماژول تمام دستورات را از طریق APIهای رسمی و مجاز اندروید
(با pyjnius) یا کتابخانه‌ی استاندارد plyer اجرا می‌کند - نه با اجرای
دستورات شل مثل ``svc wifi enable`` که روی گوشی‌های معمولی و بدون روت
(یعنی تقریباً همه‌ی کاربران) با خطای دسترسی مواجه می‌شوند و بی‌صدا
شکست می‌خورند.
"""

import re
from datetime import datetime

from src.android_bridge import AndroidBridge, is_android

APP_PACKAGE_MAP = {
    'دوربین': 'com.android.camera2',
    'camera': 'com.android.camera2',
    'ماشین حساب': 'com.google.android.calculator',
    'calculator': 'com.google.android.calculator',
    'گالری': 'com.google.android.apps.photos',
    'gallery': 'com.google.android.apps.photos',
    'تنظیمات': 'com.android.settings',
    'settings': 'com.android.settings',
    'مرورگر': 'com.android.chrome',
    'chrome': 'com.android.chrome',
    'گوگل': 'com.google.android.googlequicksearchbox',
    'یوتیوب': 'com.google.android.youtube',
    'youtube': 'com.google.android.youtube',
    'whatsapp': 'com.whatsapp',
    'واتساپ': 'com.whatsapp',
    'تلگرام': 'org.telegram.messenger',
    'telegram': 'org.telegram.messenger',
    'اینستاگرام': 'com.instagram.android',
    'instagram': 'com.instagram.android',
    'ساعت': 'com.google.android.deskclock',
    'زنگ': 'com.google.android.deskclock',
    'نقشه': 'com.google.android.apps.maps',
    'maps': 'com.google.android.apps.maps',
    'فروشگاه': 'com.android.vending',
    'پلی استور': 'com.android.vending',
    'گوگل پلی': 'com.android.vending',
    'تماس': 'com.google.android.dialer',
}


class VinaSystemControl:
    """کلاس کنترل سیستم - فقط با APIهای واقعی و مجاز اندروید"""

    def __init__(self):
        self.is_android = is_android()
        self.bridge = AndroidBridge()

    def handle_command(self, text):
        """پردازش دستورات سیستمی؛ در صورت عدم تطبیق None برمی‌گرداند"""
        text_lower = text.lower().strip()

        if any(kw in text_lower for kw in ['باز کن', 'اپلیکیشن', 'برنامه رو باز', 'اجرا کن']):
            app_name = self._extract_app_name(text_lower)
            if app_name:
                return self.open_app(app_name)

        if any(kw in text_lower for kw in ['وای‌فای', 'وای فای', 'wifi']):
            return self._handle_wifi(text_lower)

        if any(kw in text_lower for kw in ['بلوتوث', 'bluetooth']):
            return self._handle_bluetooth(text_lower)

        if any(kw in text_lower for kw in ['روشنایی', 'نور صفحه', 'brightness']):
            return self._handle_brightness(text_lower)

        if any(kw in text_lower for kw in ['زنگ', 'alarm', 'آلارم']):
            return self._handle_alarm(text_lower)

        if any(kw in text_lower for kw in ['ساعت', 'تاریخ', 'زمان']):
            return self._handle_time()

        if any(kw in text_lower for kw in ['باتری', 'شارژ', 'battery']):
            return self._handle_battery()

        if any(kw in text_lower for kw in ['اسکرین‌شات', 'اسکرین شات', 'عکس صفحه']):
            return self._take_screenshot()

        return None

    def _extract_app_name(self, text):
        prefixes = ['باز کن', 'اپلیکیشن', 'برنامه', 'اجرا کن', 'رو باز کن']
        for prefix in prefixes:
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                name = text[idx:].strip()
                if name:
                    return name
        return None

    def open_app(self, app_name):
        app_lower = app_name.lower().strip()
        package = APP_PACKAGE_MAP.get(app_lower)

        if not package:
            for key, pkg in APP_PACKAGE_MAP.items():
                if key in app_lower or app_lower in key:
                    package = pkg
                    break

        if not package:
            return f"برنامه «{app_name}» شناخته‌شده نیست. لطفاً نام دقیق‌تری بگویید."

        if not self.is_android:
            return f"باز کردن {package} (فقط روی اندروید اجرا می‌شود)."

        success, error = self.bridge.launch_app_by_package(package)
        if success:
            return f"در حال باز کردن {app_name}..."
        return f"باز کردن {app_name} ممکن نشد: {error}"

    def _handle_wifi(self, text):
        if not self.is_android:
            return "کنترل وای‌فای فقط روی اندروید در دسترس است."
        status = self.bridge.is_wifi_enabled()
        self.bridge.open_wifi_settings()
        status_text = ""
        if status is True:
            status_text = " (در حال حاضر روشن است)"
        elif status is False:
            status_text = " (در حال حاضر خاموش است)"
        return f"صفحه‌ی تنظیمات وای‌فای را برایتان باز کردم{status_text}. لطفاً از آنجا تغییر دهید."

    def _handle_bluetooth(self, text):
        if not self.is_android:
            return "کنترل بلوتوث فقط روی اندروید در دسترس است."
        status = self.bridge.is_bluetooth_enabled()
        self.bridge.open_bluetooth_settings()
        status_text = ""
        if status is True:
            status_text = " (در حال حاضر روشن است)"
        elif status is False:
            status_text = " (در حال حاضر خاموش است)"
        return f"صفحه‌ی تنظیمات بلوتوث را برایتان باز کردم{status_text}. لطفاً از آنجا تغییر دهید."

    def _handle_brightness(self, text):
        numbers = re.findall(r'\d+', text)
        if not numbers:
            return "سطح روشنایی را به‌صورت درصد مشخص کنید (مثال: روشنایی رو ۷۰ درصد کن)."

        percent = max(0, min(100, int(numbers[0])))
        if not self.is_android:
            return f"روشنایی روی {percent}% تنظیم شد (فقط روی اندروید اجرا می‌شود)."

        success, message = self.bridge.set_brightness_percent(percent)
        if success:
            return f"روشنایی روی {percent}% تنظیم شد."
        return message or "تنظیم روشنایی ممکن نشد."

    def _handle_alarm(self, text):
        time_match = re.search(r'(\d{1,2})[:\s](\d{2})', text)
        if not time_match:
            return "ساعت آلارم را مشخص کنید (مثال: ساعت ۸:۰۰ صبح آلارم بذار)."

        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            return "ساعت وارد شده معتبر نیست."

        if not self.is_android:
            return f"آلارم برای ساعت {hour:02d}:{minute:02d} تنظیم شد (فقط روی اندروید اجرا می‌شود)."

        success, error = self.bridge.set_alarm(hour, minute)
        if success:
            return f"صفحه‌ی تنظیم آلارم برای ساعت {hour:02d}:{minute:02d} باز شد."
        return f"تنظیم آلارم ممکن نشد: {error}"

    def _handle_time(self):
        now = datetime.now()
        return f"الان ساعت {now.strftime('%H:%M')} و تاریخ {now.strftime('%Y/%m/%d')} هست."

    def _handle_battery(self):
        status = self.bridge.get_battery_status()
        if not status:
            return "اطلاعات باتری در دسترس نیست."

        percentage = status.get('percentage')
        is_charging = status.get('isCharging')
        if percentage is None:
            return "اطلاعات باتری در دسترس نیست."

        charge_text = "در حال شارژ" if is_charging else "در حال استفاده"
        return f"سطح باتری: {percentage:.0f}% - {charge_text}"

    def _take_screenshot(self):
        import tempfile
        import os as _os

        path = _os.path.join(tempfile.gettempdir(), "vina_screenshot")
        success, error = self.bridge.take_app_screenshot(path)
        if success:
            return "اسکرین‌شات از صفحه‌ی وینا گرفته شد."
        return f"گرفتن اسکرین‌شات ممکن نشد: {error}"

    def get_device_info(self):
        info = {
            'is_android': self.is_android,
        }
        battery = self.bridge.get_battery_status()
        if battery:
            info['battery'] = battery
        return info
