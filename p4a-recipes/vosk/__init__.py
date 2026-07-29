# -*- coding: utf-8 -*-
"""
recipe اختصاصی python-for-android برای قرار دادن libvosk.so در APK

چرا از پکیج pip رسمی ``vosk`` استفاده نمی‌کنیم؟
--------------------------------------------------------------------------
پکیج pip به **cffi** وابسته است و هدر C را در زمان import پردازش می‌کند؛
این روی گوشی (که کامپایلر ندارد) کار نمی‌کند و کراس‌کامپایل cffi روی p4a
هم شکننده است. در عوض:

  1. اینجا فقط باینری رسمی از پیش کامپایل‌شده‌ی اندروید داخل APK قرار
     می‌گیرد (از روی artifact رسمی Maven).
  2. سمت پایتون، ``src/vosk_ctypes.py`` مستقیماً با ctypes به همان
     libvosk.so وصل می‌شود - بدون هیچ کامپایلی در زمان اجرا.

این دقیقاً همان الگویی است که برای llama.cpp هم استفاده شده است.

منبع دانلود
--------------------------------------------------------------------------
از artifact رسمی Maven استفاده می‌شود:

    com/alphacephei/vosk-android/{version}/vosk-android-{version}.aar

دلیل انتخاب Maven به‌جای فایل zip در GitHub Releases: ساختار داخلی فایل
aar استاندارد و تضمین‌شده است (``jni/<abi>/libvosk.so``) و همان منبعی
است که خودِ recipe رسمی python-for-android هم از آن استفاده می‌کند
(pythonforandroid/recipes/vosk/__init__.py). ساختار zip در Releases بین
نسخه‌ها تغییر کرده و قابل اتکا نیست.

رفتار در صورت شکست (تصمیم آگاهانه‌ی طراحی)
--------------------------------------------------------------------------
تشخیص گفتار آفلاین یک قابلیت **اختیاری** است: اگر libvosk در دسترس نباشد
برنامه به android.speech.SpeechRecognizer داخلی سیستم برمی‌گردد
(src/stt_engine.py این حالت را مدیریت می‌کند و src/vosk_ctypes.py هم
نبودن کتابخانه را با پیام روشن گزارش می‌کند - کرش نمی‌کند).

بنابراین اگر دانلود یا استخراج libvosk شکست بخورد، **کل بیلد APK را
متوقف نمی‌کنیم**؛ فقط یک هشدار پررنگ چاپ می‌شود. از دست دادن STT آفلاین
خیلی بهتر از نداشتن APK است. این تنها موردی است که در این پروژه خطا را
نادیده می‌گیریم و دلیلش هم دقیقاً همین‌جا مستند شده.
"""
import traceback
import zipfile
from os.path import basename, exists, join

from pythonforandroid.logger import info, warning
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import ensure_dir


def arch_name(arch):
    """نام معماری، چه شیء Arch داده شود چه رشته.

    python-for-android یکدست نیست: prepare_build_dir رشته می‌گیرد ولی
    should_build/build_arch شیء Arch. (جزئیات در p4a-recipes/vinallm.)
    """
    return arch if isinstance(arch, str) else arch.arch


# نگاشت نام ABI اندروید در p4a به نام پوشه داخل فایل aar
ABI_MAP = {
    'arm64-v8a': 'arm64-v8a',
    'armeabi-v7a': 'armeabi-v7a',
    'x86_64': 'x86_64',
    'x86': 'x86',
}


class VoskRecipe(Recipe):
    """قرار دادن libvosk.so از پیش کامپایل‌شده در APK (اختیاری)."""

    version = '0.3.45'
    # url را عمداً None می‌گذاریم تا مکانیزم دانلود/استخراج خودکار p4a
    # فعال نشود؛ خودمان aar را کنترل‌شده دانلود می‌کنیم تا بتوانیم در
    # صورت شکست به‌جای متوقف کردن بیلد فقط هشدار بدهیم.
    url = None

    aar_url = ('https://repo.maven.apache.org/maven2/com/alphacephei/'
               'vosk-android/{version}/vosk-android-{version}.aar')

    depends = []
    # توجه: built_libraries را تعریف *نمی‌کنیم*. اگر تعریف می‌شد، کلاس پایه
    # بعد از build_arch به‌صورت خودکار install_libraries را صدا می‌زد و در
    # صورت نبود فایل، بیلد با خطا متوقف می‌شد - دقیقاً همان چیزی که اینجا
    # نمی‌خواهیم. به‌جای آن خودمان فایل را کپی می‌کنیم.
    built_libraries = {}

    def prepare_build_dir(self, arch):
        ensure_dir(self.get_build_dir(arch_name(arch)))

    def should_build(self, arch):
        return not exists(join(self.get_build_dir(arch_name(arch)), 'libvosk.so'))

    def _download_aar(self):
        """دانلود aar رسمی و برگرداندن مسیر آن."""
        aar_dir = join(self.ctx.packages_path, 'vosk-android')
        ensure_dir(aar_dir)
        aar_name = f'vosk-android-{self.version}.aar'
        aar_path = join(aar_dir, aar_name)
        if not exists(aar_path):
            self.download_file(self.aar_url.format(version=self.version),
                               aar_name, cwd=aar_dir)
        return aar_path

    def build_arch(self, arch):
        name = arch_name(arch)
        abi = ABI_MAP.get(name)
        build_dir = self.get_build_dir(name)
        ensure_dir(build_dir)

        if abi is None:
            warning(f'Vosk: هیچ کتابخانه‌ای برای معماری {name} وجود ندارد؛ '
                    'تشخیص گفتار آفلاین در این بیلد غیرفعال می‌شود.')
            return

        try:
            aar_path = self._download_aar()
            member = f'jni/{abi}/libvosk.so'
            target = join(build_dir, 'libvosk.so')

            with zipfile.ZipFile(aar_path) as aar:
                with aar.open(member) as src, open(target, 'wb') as dst:
                    dst.write(src.read())

            libs_dir = self.ctx.get_libs_dir(name)
            ensure_dir(libs_dir)
            with open(target, 'rb') as src, \
                    open(join(libs_dir, 'libvosk.so'), 'wb') as dst:
                dst.write(src.read())

            info(f'Vosk: libvosk.so برای {abi} از {basename(aar_path)} نصب شد')

        except Exception:
            # عمداً هیچ استثنایی را بالا نمی‌فرستیم - توضیح کامل در docstring
            # بالای همین فایل. اما جزئیات خطا را کامل چاپ می‌کنیم تا
            # مشکل پنهان نماند.
            warning('=' * 70)
            warning('Vosk: نصب libvosk.so ناموفق بود - بیلد ادامه پیدا می‌کند.')
            warning('پیامد: تشخیص گفتار *آفلاین* در این APK کار نخواهد کرد؛')
            warning('برنامه به‌صورت خودکار از SpeechRecognizer اندروید استفاده')
            warning('می‌کند (نیازمند اینترنت روی اکثر گوشی‌ها).')
            warning('جزئیات فنی خطا:')
            for line in traceback.format_exc().splitlines():
                warning('  ' + line)
            warning('=' * 70)


recipe = VoskRecipe()
