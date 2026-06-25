# -*- coding: utf-8 -*-
# فایل تنظیمات Buildozer برای ساخت APK وینا
# این فایل را در پوشه اصلی پروژه قرار دهید

[app]

# اطلاعات برنامه
title = Vina AI
package.name = vinabot
package.domain = org
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json,db,gguf,so
version = 1.0.0

# نام کامل برنامه
package.full_name = Vina AI Assistant
package.author = Vina Team
package.author_email = vina@vinabot.org
package.license = MIT

# معماری هدف (ARM64 برای گوشی‌های جدید)
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk = 28c
# android.sdk_path = /home/amirabbas/.buildozer/android/platform/android-sdk

# مجوزها
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,ACCESS_WIFI_STATE,ACCESS_NETWORK_STATE,WAKE_LOCK,VIBRATE,FOREGROUND_SERVICE,READ_CONTACTS,READ_CALENDAR,SET_ALARM,RECEIVE_BOOT_COMPLETED,MODIFY_AUDIO_SETTINGS

# تنظیمات کامپایلر
android.accept_sdk_license = True
android.release_artifact = apk
android.debug_artifact = apk

# کتابخانه‌ها وابستگی‌ها
# python3 = python3.11+
# kivy = kivy 2.3.0+
# python-for-android (p4a)

android.enable_r8 = False

# منابع (فایل‌های اضافی)
source.include_patterns = assets/*,models/*.gguf,models/vosk*,memory/*

# تنظیمات P4A - از نسخه پایدار استفاده کنید
p4a.branch = master
p4a.bootstrap = sdl2

# فایل‌های Python اضافی
# NOTE: llama-cpp-python و vosk نیاز به cross-compile دارند، حذف شدند.
# کاربر می‌تواند Vosk model رو به صورت runtime دانلود کند.
# مدل LLM (Gemma-2-9B) به دلیل حجم بالا (5GB) روی گوشی اجرا نمی‌شود.
# برنامه با fallback text-mode و بدون صدا کار می‌کند.
requirements = python3,kivy,openssl,requests,beautifulsoup4,numpy,sqlite3,cryptography,pillow,pyjnius

# تنظیمات Gradle
android.gradle_dependencies =

# فایل AndroidManifest.xml سفارشی (غیرفعال - buildozer خودش می‌سازد)
# android.manifest = AndroidManifest.xml

android.log_level = 2
android.compile_sdk_version = 33
android.build_tools_version = 33.0.2



# ساخت release
# buildozer -v android release

# ساخت debug
# buildozer -v android debug

# اجرا روی گوشی
# buildozer -v android debug deploy run

android.gradle_version = 8.5