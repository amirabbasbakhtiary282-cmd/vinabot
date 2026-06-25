# -*- coding: utf-8 -*-
"""
ماژول کنترل سیستم گوشی
باز کردن برنامه‌ها، وای‌فای، بلوتوث، روشنایی، آلارم
"""

import os
import sys
import subprocess
import json
from datetime import datetime


class VinaSystemControl:
    """کلاس کنترل سیستم"""

    def __init__(self):
        self.is_android = self._check_android()
        self.platform = sys.platform

    def _check_android(self):
        """بررسی اجرا روی اندروید"""
        return os.path.exists('/system/build.prop') or os.path.exists('/data/data/com.termux')

    def handle_command(self, text):
        """پردازش دستورات سیستمی"""
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
        """استخراج نام برنامه"""
        prefixes = ['باز کن', 'اپلیکیشن', 'برنامه', 'اجرا کن', 'رو باز کن']
        for prefix in prefixes:
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                name = text[idx:].strip()
                if name:
                    return name
        return None

    def open_app(self, app_name):
        """باز کردن برنامه"""
        app_map = {
            'دوربین': 'android.intent.action.MAIN',
            'calculator': 'com.android.calculator2',
            'ماشین حساب': 'com.android.calculator2',
            'گالری': 'com.android.gallery3d',
            'تنظیمات': 'com.android.settings',
            'settings': 'com.android.settings',
            'مرورگر': 'com.android.browser',
            'گوگل': 'com.google.android.googlequicksearchbox',
            'یوتیوب': 'com.google.android.youtube',
            'whatsapp': 'com.whatsapp',
            'واتساپ': 'com.whatsapp',
            'تلگرام': 'org.telegram.messenger',
            'اینستاگرام': 'com.instagram.android',
            'فایل منیجر': 'com.android.filemanager',
            'ساعت': 'com.android.deskclock',
            'زنگ': 'com.android.deskclock',
            'نقشه': 'com.google.android.apps.maps',
            'فروشگاه': 'com.android.vending',
            'پلی استور': 'com.android.vending',
            'گوگل پلی': 'com.android.vending',
            'یادداشت': 'com.google.android.apps.keep',
            'تماس': 'com.android.contacts',
        }

        app_lower = app_name.lower().strip()
        package = app_map.get(app_lower)

        if package:
            return self._launch_package(package)

        for key, pkg in app_map.items():
            if key in app_lower or app_lower in key:
                return self._launch_package(pkg)

        return f"برنامه «{app_name}» پیدا نشد. لطفاً نام دقیق‌تری بگویید."

    def _launch_package(self, package):
        """اجرای پکیج"""
        if self.is_android:
            try:
                subprocess.Popen(
                    ['am', 'start', '-n', f'{package}/.MainActivity'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"برنامه باز شد: {package}"
            except Exception:
                pass

        return f"باز کردن {package} (فقط روی اندروید)"

    def _handle_wifi(self, text):
        """کنترل وای‌فای"""
        if 'روشن' in text or 'فعال' in text or 'on' in text:
            return self.set_wifi(True)
        elif 'خاموش' in text or 'غیرفعال' in text or 'off' in text:
            return self.set_wifi(False)
        return "آیا می‌خواهید وای‌فای را روشن یا خاموش کنید؟"

    def set_wifi(self, enable):
        """تنظیم وای‌فای"""
        if self.is_android:
            try:
                state = 'enable' if enable else 'disable'
                subprocess.run(
                    ['svc', 'wifi', state],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                status = "روشن" if enable else "خاموش"
                return f"وای‌فای {status} شد."
            except Exception:
                pass

        status = "روشن" if enable else "خاموش"
        return f"وای‌فای {status} شد (فقط روی اندروید اجرا می‌شود)."

    def _handle_bluetooth(self, text):
        """کنترل بلوتوث"""
        if 'روشن' in text or 'فعال' in text or 'on' in text:
            return self.set_bluetooth(True)
        elif 'خاموش' in text or 'غیرفعال' in text or 'off' in text:
            return self.set_bluetooth(False)
        return "آیا می‌خواهید بلوتوث را روشن یا خاموش کنید؟"

    def set_bluetooth(self, enable):
        """تنظیم بلوتوث"""
        if self.is_android:
            try:
                state = 'enable' if enable else 'disable'
                subprocess.run(
                    ['svc', 'bluetooth', state],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                status = "روشن" if enable else "خاموش"
                return f"بلوتوث {status} شد."
            except Exception:
                pass

        status = "روشن" if enable else "خاموش"
        return f"بلوتوث {status} شد (فقط روی اندروید اجرا می‌شود)."

    def _handle_brightness(self, text):
        """کنترل روشنایی"""
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            level = min(255, max(0, int(numbers[0])))
            if 'درصد' in text:
                level = int(level * 255 / 100)
            return self.set_brightness(level)
        return "سطح روشنایی را مشخص کنید (0 تا 255 یا درصد)."

    def set_brightness(self, level):
        """تنظیم روشنایی"""
        if self.is_android:
            try:
                with open('/sys/class/backlight/panel0-backlight/brightness', 'w') as f:
                    f.write(str(level))
                return f"روشنایی روی {level} تنظیم شد."
            except Exception:
                pass

        percentage = int(level * 100 / 255)
        return f"روشنایی روی {percentage}% تنظیم شد (فقط روی اندروید اجرا می‌شود)."

    def _handle_alarm(self, text):
        """تنظیم آلارم"""
        import re
        time_match = re.search(r'(\d{1,2})[:\s](\d{2})', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            return self.set_alarm(hour, minute)
        return "ساعت آلارم را مشخص کنید (مثال: ساعت 8 صبح)."

    def set_alarm(self, hour, minute):
        """تنظیم آلارم"""
        if self.is_android:
            try:
                from datetime import datetime as dt
                now = dt.now()
                alarm_time = dt(now.year, now.month, now.day, hour, minute)
                if alarm_time <= now:
                    from datetime import timedelta
                    alarm_time += timedelta(days=1)

                intent = (
                    f'am start -a android.intent.action.SET_ALARM '
                    f'--ei android.intent.extra.alarm.HOUR {hour} '
                    f'--ei android.intent.extra.alarm.MINUTES {minute} '
                    f'--ez android.intent.extra.alarm.SKIP_UI true'
                )
                subprocess.Popen(intent.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"آلارم برای ساعت {hour:02d}:{minute:02d} تنظیم شد."
            except Exception:
                pass

        return f"آلارم برای ساعت {hour:02d}:{minute:02d} تنظیم شد (فقط روی اندروید اجرا می‌شود)."

    def _handle_time(self):
        """نمایش ساعت و تاریخ"""
        now = datetime.now()
        persian_months = [
            'ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن',
            'ژوئیه', 'اوت', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر'
        ]
        return f"الان ساعت {now.strftime('%H:%M')} و تاریخ {now.strftime('%Y/%m/%d')} هست."

    def _handle_battery(self):
        """وضعیت باتری"""
        if self.is_android:
            try:
                with open('/sys/class/power_supply/battery/capacity', 'r') as f:
                    level = f.read().strip()
                with open('/sys/class/power_supply/battery/status', 'r') as f:
                    status = f.read().strip()

                status_fa = "در حال شارژ" if status == "Charging" else "در حال استفاده"
                return f"سطح باتری: {level}% - {status_fa}"
            except Exception:
                pass

        return "اطلاعات باتری فقط روی اندروید قابل دریافت است."

    def _take_screenshot(self):
        """گرفتن اسکرین‌شات"""
        if self.is_android:
            try:
                subprocess.Popen(
                    ['screencap', '-p', '/sdcard/screenshot.png'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return "اسکرین‌شات گرفته شد."
            except Exception:
                pass

        return "گرفتن اسکرین‌شات فقط روی اندروید امکان‌پذیر است."

    def get_device_info(self):
        """اطلاعات دستگاه"""
        info = {
            'platform': sys.platform,
            'is_android': self.is_android,
        }

        if self.is_android:
            try:
                with open('/sys/class/power_supply/battery/capacity', 'r') as f:
                    info['battery'] = f.read().strip()
            except Exception:
                pass

        return info
