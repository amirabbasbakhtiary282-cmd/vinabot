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
from pythonforandroid.util import current_directory, ensure_dir

import sh

# نگاشت نام ABI اندروید در p4a به نام پوشه در آرشیو رسمی Vosk
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
        return not exists(join(self.get_build_dir(arch.arch), 'libvosk.so'))

    def prepare_build_dir(self, arch):
        """آرشیو رسمی را دانلود و استخراج می‌کند."""
        ensure_dir(self.get_build_dir(arch))
        super().prepare_build_dir(arch)

    def build_arch(self, arch):
        """libvosk.so مربوط به ABI هدف را از آرشیو استخراج‌شده برمی‌دارد.

        ساختار آرشیو رسمی:
            vosk-android-<version>/<abi>/libvosk.so
        اما بسته به نسخه ممکن است یک لایه پوشه‌ی اضافه داشته باشد، پس
        به‌جای فرض کردن مسیر دقیق، فایل را جستجو می‌کنیم.
        """
        build_dir = self.get_build_dir(arch.arch)
        abi = ABI_MAP.get(arch.arch, arch.arch)

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
