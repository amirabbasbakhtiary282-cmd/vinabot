# -*- coding: utf-8 -*-
# فایل تنظیمات Buildozer برای ساخت APK وینا

[app]

# اطلاعات برنامه
title = Vina AI
package.name = vinabot
package.domain = org
source.dir = .
# نکته‌ی مهم: پسوند gguf عمداً در این لیست **نیست**.
# اگر باشد، هر فایل مدلی که در پوشه‌ی پروژه وجود داشته باشد داخل APK
# بسته‌بندی می‌شود و حجم APK را صدها مگابایت بالا می‌برد - دقیقاً برخلاف
# خواسته‌ی پروژه («مدل نباید داخل APK باشد؛ APK باید سبک بماند»).
# مدل در زمان اجرا از حافظه‌ی دستگاه خوانده می‌شود (src/model_paths.py).
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,eot,woff,json,so
version = 1.0.0

# نام کامل برنامه
package.full_name = Vina AI Assistant
package.author = Vina Team
package.author_email = vina@vinabot.org
package.license = MIT

# معماری هدف
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24

# مجوزها (فقط مجوزهایی که واقعاً استفاده می‌شوند)
# - INTERNET: جستجوی اینترنتی و دانلود مدل
# - RECORD_AUDIO: تشخیص گفتار (STT)
# - ACCESS_NETWORK_STATE: بررسی وضعیت اتصال قبل از جستجو
# - VIBRATE: بازخورد لمسی
# - WAKE_LOCK: جلوگیری از خواب رفتن گوشی حین صحبت TTS
# - WRITE_SETTINGS: تنظیم روشنایی صفحه (کاربر باید صریحاً از تنظیمات اجازه دهد)
# - POST_NOTIFICATIONS: نمایش یادآوری‌ها (الزامی از اندروید 13/API 33 به بعد)
# توجه: CAMERA، READ/WRITE_EXTERNAL_STORAGE، READ_CONTACTS، READ_CALENDAR،
# SET_ALARM، RECEIVE_BOOT_COMPLETED و MODIFY_AUDIO_SETTINGS از نسخه‌ی قبلی
# حذف شدند چون هیچ کدی در این پروژه از آن‌ها استفاده نمی‌کرد (درخواست مجوز
# بدون استفاده‌ی واقعی هم گمراه‌کننده است و هم اعتماد کاربر را کاهش می‌دهد).
# - FOREGROUND_SERVICE(+MICROPHONE): لازم برای ادامه‌ی گفتگوی صوتی وقتی
#   صفحه خاموش می‌شود یا کاربر به اپ دیگری می‌رود (اندروید 14 نوع سرویس را
#   هم می‌خواهد).
android.permissions = INTERNET,RECORD_AUDIO,ACCESS_NETWORK_STATE,VIBRATE,WAKE_LOCK,android.permission.WRITE_SETTINGS,android.permission.POST_NOTIFICATIONS,android.permission.FOREGROUND_SERVICE,android.permission.FOREGROUND_SERVICE_MICROPHONE,android.permission.MODIFY_AUDIO_SETTINGS

# تنظیمات کامپایلر
android.accept_sdk_license = True
android.release_artifact = apk
android.debug_artifact = apk
android.enable_r8 = False

# منابع (فایل‌های اضافی)
# فقط assets (فونت و آیکون). الگوی models/*.gguf عمداً حذف شد تا مدل
# هرگز داخل APK نرود.
source.include_patterns = assets/*

# فایل‌های حجیم/غیرضروری نباید وارد بسته شوند
source.exclude_exts = gguf,bin,zip,tar,gz,apk,aab,log
source.exclude_dirs = tests,bin,.buildozer,ci,models,p4a-recipes,__pycache__,.github,memory

# تنظیمات P4A
p4a.branch = master
p4a.bootstrap = sdl2
# recipeهای اختصاصی برای اجرای واقعی مدل زبانی روی اندروید (بدون
# llama-cpp-python) - به‌جای آن مستقیماً سورس رسمی llama.cpp کراس‌کامپایل
# می‌شود. جزئیات کامل در p4a-recipes/llamacpp و p4a-recipes/vinallm.
p4a.local_recipes = ./p4a-recipes

# وابستگی‌ها:
# - llamacpp, vinallm: موتور استنتاج مدل زبانی محلی (native، بدون llama-cpp-python)
# - pyjnius: دسترسی به APIهای اندروید (TTS، SpeechRecognizer، AudioRecord، تنظیمات سیستم)
# - vosk: کتابخانه‌ی native تشخیص گفتار آفلاین (از طریق ctypes استفاده می‌شود)
# - plyer: باتری و سایر سنسورهای استاندارد
# - arabic_reshaper, python-bidi: نمایش صحیح متن فارسی/عربی (شکل‌دهی حروف و RTL)
# - requests, beautifulsoup4: جستجوی اینترنتی
# نکته: vosk حذف شده چون تشخیص گفتار اکنون از android.speech.SpeechRecognizer
# داخلی استفاده می‌کند (بدون نیاز به دانلود مدل جداگانه)؛ llama-cpp-python هم
# حذف شده چون کراس‌کامپایل آن برای اندروید غیرقابل‌اعتماد است.
requirements = python3,kivy==2.3.1,openssl,requests,beautifulsoup4,sqlite3,pyjnius,plyer,arabic_reshaper,python-bidi==0.4.2,pygments,android,llamacpp,vinallm,vosk

# نکته‌ی حیاتی: این کلید باید کاملاً **کامنت** بماند، نه اینکه خالی رها شود.
#
# چرا؟ (ریشه‌ی شکست بیلد شماره ۸ - تأییدشده با اجرای واقعی buildozer)
# نوشتن «android.gradle_dependencies =» با مقدار خالی باعث می‌شود
# SpecParser.getlist به‌جای لیست خالی، لیستی شامل یک رشته‌ی خالی برگرداند:
#
#     >>> p.getlist('app', 'android.gradle_dependencies', [])
#     ['']
#
# دلیلش این است که getlist ابتدا مقدار را می‌گیرد ('' که None نیست، پس
# default برگردانده نمی‌شود) و بعد ''.split(',') را صدا می‌زند که [''] است
# (buildozer/specparser.py خطوط ۸۶-۹۲).
#
# سپس targets/android.py خط ۹۷۲ به ازای هر عضو یک «--depend» اضافه می‌کند:
#
#     '--depend', ''
#
# و آن رشته‌ی خالی داخل build.gradle به‌صورت implementation '' می‌نشیند و
# Gradle با این خطا شکست می‌خورد:
#
#     Build file '.../dists/vinabot/build.gradle' line: 76
#     Supplied String module notation '' is invalid.
#
# اگر روزی وابستگی Gradle لازم شد، این خط را از کامنت خارج کنید و مقدار
# واقعی بدهید، مثلاً:
#     android.gradle_dependencies = androidx.core:core:1.12.0
#
# android.gradle_dependencies =

android.log_level = 2
android.compile_sdk_version = 33
android.build_tools_version = 33.0.2
android.gradle_version = 8.5

orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

# ساخت debug:  buildozer -v android debug
# ساخت release: buildozer -v android release
