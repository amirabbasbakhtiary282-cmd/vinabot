# -*- coding: utf-8 -*-
"""
recipe اختصاصی python-for-android برای قرار دادن libvosk.so در APK

چرا از پکیج pip رسمی ``vosk`` استفاده نمی‌کنیم؟
--------------------------------------------------------------------------
پکیج pip به **cffi** وابسته است و هدر C را در زمان import پردازش می‌کند؛
این روی گوشی (که کامپایلر ندارد) کار نمی‌کند و کراس‌کامپایل cffi روی p4a
هم شکننده است. در عوض:

  1. اینجا فقط باینری رسمی از پیش کامپایل‌شده‌ی اندروید (vosk-android.zip
     که خود تیم Vosk منتشر می‌کند و شامل libvosk.so برای همه‌ی ABIهاست)
     دانلود و در APK قرار داده می‌شود.
  2. سمت پایتون، ``src/vosk_ctypes.py`` مستقیماً با ctypes به همان
     libvosk.so وصل می‌شود - بدون هیچ کامپایلی در زمان اجرا.

این دقیقاً همان الگویی است که برای llama.cpp هم استفاده شده است.
"""
from os.path import exists, join

from pythonforandroid.logger import info, shprint
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory

import sh

# نگاشت نام ABI اندروید در p4a به نام پوشه در آرشیو رسمی Vosk
def arch_name(arch):
    """نام معماری، چه شیء Arch داده شود چه رشته.

    python-for-android یکدست نیست: prepare_build_dir رشته می‌گیرد ولی
    should_build/build_arch شیء Arch. (جزئیات در p4a-recipes/vinallm.)
    """
    return arch if isinstance(arch, str) else arch.arch


ABI_MAP = {
    'arm64-v8a': 'arm64-v8a',
    'armeabi-v7a': 'armeabi-v7a',
    'x86_64': 'x86_64',
    'x86': 'x86',
}


class VoskRecipe(Recipe):
    """قرار دادن libvosk.so از پیش کامپایل‌شده در APK."""

    version = '0.3.45'
    url = ('https://github.com/alphacep/vosk-api/releases/download/'
           'v{version}/vosk-android-{version}.zip')

    depends = []
    built_libraries = {'libvosk.so': '.'}

    def should_build(self, arch):
        # توجه: should_build یک شیء Arch می‌گیرد (نه رشته) - build.py خط ۵۲۹
        return not exists(join(self.get_build_dir(arch_name(arch)), 'libvosk.so'))

    # نکته‌ی مهم: prepare_build_dir را override نمی‌کنیم.
    #
    # نسخه‌ی قبلی این کار را می‌کرد:
    #     ensure_dir(self.get_build_dir(arch))
    #     super().prepare_build_dir(arch)
    #
    # که یک باگ *بی‌صدا* بود: متد unpack در p4a فقط وقتی آرشیو را استخراج
    # می‌کند که پوشه‌ی مقصد هنوز وجود نداشته باشد
    # (recipe.py: ``if not exists(directory_name) or not isdir(...)``).
    # ساختن آن پوشه از قبل باعث می‌شد استخراج کاملاً نادیده گرفته شود و
    # بعداً build_arch با «libvosk.so پیدا نشد» شکست بخورد - بدون هیچ
    # پیام روشنی درباره‌ی علت واقعی. رفتار پیش‌فرض کلاس پایه درست است.

    def build_arch(self, arch):
        """libvosk.so مربوط به ABI هدف را از آرشیو استخراج‌شده برمی‌دارد.

        ساختار آرشیو رسمی:
            vosk-android-<version>/<abi>/libvosk.so
        اما بسته به نسخه ممکن است یک لایه پوشه‌ی اضافه داشته باشد، پس
        به‌جای فرض کردن مسیر دقیق، فایل را جستجو می‌کنیم.
        """
        name = arch_name(arch)
        build_dir = self.get_build_dir(name)
        abi = ABI_MAP.get(name, name)

        info(f'Vosk: locating libvosk.so for ABI={abi}')

        found = None
        with current_directory(build_dir):
            # جستجوی امن‌تر از فرض مسیر ثابت (ساختار zip بین نسخه‌ها فرق دارد)
            for line in sh.find('.', '-name', 'libvosk.so').splitlines():
                candidate = line.strip()
                if not candidate:
                    continue
                if f'/{abi}/' in candidate.replace('\\', '/'):
                    found = candidate
                    break

            if not found:
                raise RuntimeError(
                    f'libvosk.so برای معماری {abi} در آرشیو Vosk پیدا نشد. '
                    'ساختار آرشیو ممکن است در این نسخه تغییر کرده باشد.')

            info(f'Vosk: using {found}')
            # کپی در ریشه‌ی build dir تا built_libraries آن را پیدا کند
            shprint(sh.cp, found, join(build_dir, 'libvosk.so'))


recipe = VoskRecipe()
