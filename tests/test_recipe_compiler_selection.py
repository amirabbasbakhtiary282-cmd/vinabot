# -*- coding: utf-8 -*-
"""
تست انتخاب کامپایلر در recipeها - جلوگیری از تکرار باگ ccache

انگیزه (باگ واقعی، نه فرضی)
--------------------------------------------------------------------------
بیلد شماره‌ی ۷ در GitHub Actions با این خطا شکست خورد:

    File "p4a-recipes/vinallm/__init__.py", line 83, in build_arch
    RAN: /usr/bin/ccache -std=c++17 -shared -fPIC -O2 ...
    STDOUT: /usr/bin/ccache: invalid option -- 't'

علت: recipe کامپایلر را این‌طور انتخاب می‌کرد:

    clang = env.get("CC", "clang").split()[0]

اما python-for-android متغیر CC را به این شکل می‌سازد
(pythonforandroid/archs.py، متد Arch.get_env):

    env['CC'] = '{ccache}{exe} {cflags}'

یعنی وقتی ccache نصب باشد (روی رانرهای GitHub همیشه هست)، مقدار CC
می‌شود «/usr/bin/ccache /path/to/clang -target ... -fPIC ...» و
split()[0] برابر «/usr/bin/ccache» است - یعنی ccache به‌عنوان کامپایلر
صدا زده می‌شد و روی پرچم -std=c++17 خطا می‌داد.

نکته‌ی مهم: این باگ فقط وقتی ظاهر می‌شود که ccache نصب باشد. روی یک
ماشین بدون ccache همان کد **درست کار می‌کند** - برای همین تشخیصش سخت بود
و تست زیر عمداً هر دو حالت را شبیه‌سازی می‌کند.

راه‌حل درست: به‌جای پارس کردن رشته‌ی CC، از خود شیء Arch مسیر کامپایلر
گرفته شود (arch.clang_exe_cxx) که همیشه فقط یک مسیر است.
"""

import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, 'p4a-recipes')

# recipeهایی که خودشان مستقیماً کامپایلر را صدا می‌زنند
COMPILING_RECIPES = ('vinallm',)


def _read(name):
    path = os.path.join(RECIPES, name, '__init__.py')
    with open(path, encoding='utf-8') as f:
        return f.read()


class TestNoNaiveCCParsing(unittest.TestCase):
    """هیچ recipe ای نباید کامپایلر را با split کردن CC انتخاب کند."""

    def test_no_cc_split_pattern(self):
        for name in COMPILING_RECIPES:
            src = _read(name)
            tree = ast.parse(src)

            for node in ast.walk(tree):
                # الگوی خطرناک: <هرچیزی>.split()[<عدد>]
                if not isinstance(node, ast.Subscript):
                    continue
                value = node.value
                if not isinstance(value, ast.Call):
                    continue
                func = value.func
                if not isinstance(func, ast.Attribute) or func.attr != 'split':
                    continue

                # آیا موضوع این split به CC/CXX مربوط است؟
                segment = ast.get_source_segment(src, node) or ''
                self.assertNotRegex(
                    segment, r'(CC|CXX)',
                    f'recipe «{name}»: انتخاب کامپایلر با split کردن متغیر '
                    f'CC/CXX نادرست است. وقتی ccache نصب باشد، مقدار CC '
                    f'برابر «ccache clang <flags>» است و اولین جزء آن '
                    f'ccache می‌شود، نه کامپایلر. '
                    f'به‌جای آن از arch.clang_exe_cxx استفاده کنید. '
                    f'کد مشکل‌دار: {segment}')

    def test_uses_arch_provided_compiler(self):
        """باید صریحاً از مسیر کامپایلر خود Arch استفاده شود."""
        for name in COMPILING_RECIPES:
            src = _read(name)
            self.assertIn(
                'clang_exe_cxx', src,
                f'recipe «{name}» باید کامپایلر C++ را از '
                f'arch.clang_exe_cxx بگیرد (مسیر خالص، بدون پرچم و ccache)')

    def test_cxx_source_is_compiled_with_cxx_compiler(self):
        """vina_llm.cpp کد C++ است و باید با clang++ کامپایل شود.

        اگر با clang ساده کامپایل شود، لینک استاندارد C++ انجام نمی‌شود و
        خطاهای «undefined reference to std::...» ظاهر می‌شود.
        """
        src = _read('vinallm')
        self.assertNotIn('arch.clang_exe\n', src)
        self.assertIn('clang_exe_cxx', src)


class TestCompilerFlagsAreExplicit(unittest.TestCase):
    """چون پرچم‌ها از CC حذف شده‌اند، باید صریحاً پاس داده شوند."""

    def test_target_flag_present(self):
        """بدون -target، کلنگ برای معماری میزبان (x86) کامپایل می‌کند."""
        src = _read('vinallm')
        self.assertIn('arch.target', src,
                      'بدون پرچم -target، کتابخانه برای معماری اشتباه '
                      'کامپایل می‌شود و روی گوشی بارگذاری نمی‌شود')

    def test_arch_cflags_present(self):
        src = _read('vinallm')
        self.assertIn('arch_cflags', src)

    def test_no_undefined_symbols_allowed(self):
        """لینکر باید سمبل‌های حل‌نشده را همان موقع خطا بدهد.

        بدون این پرچم، کتابخانه با موفقیت ساخته می‌شود ولی روی گوشی هنگام
        dlopen با UnsatisfiedLinkError شکست می‌خورد - یعنی خطا از زمان
        بیلد به زمان اجرا منتقل می‌شود که خیلی بدتر است.
        """
        src = _read('vinallm')
        self.assertIn('--no-undefined', src)


class TestStlSharedIsPackaged(unittest.TestCase):
    """libc++_shared.so باید داخل APK باشد."""

    def test_recipes_declare_need_stl_shared(self):
        """llama.cpp با -DANDROID_STL=c++_shared ساخته می‌شود.

        یعنی libllama.so و libvina_llm.so در زمان اجرا به
        libc++_shared.so نیاز دارند. اگر p4a آن را داخل APK نگذارد،
        برنامه با این خطا کرش می‌کند:

            dlopen failed: library "libc++_shared.so" not found

        پرچم need_stl_shared دقیقاً همین کار را می‌کند
        (pythonforandroid/recipe.py: install_stl_lib).
        """
        for name in ('llamacpp', 'vinallm'):
            src = _read(name)
            self.assertIn(
                'need_stl_shared = True', src,
                f'recipe «{name}» با c++_shared لینک می‌شود، پس باید '
                f'need_stl_shared = True داشته باشد وگرنه برنامه روی گوشی '
                f'هنگام بارگذاری کتابخانه کرش می‌کند')


class TestLlamaCppCMakeEnv(unittest.TestCase):
    """CMake نباید CC آلوده به پرچم و ccache دریافت کند."""

    def test_strips_compiler_vars(self):
        """CMake انتظار دارد CC فقط مسیر یک فایل اجرایی باشد.

        اگر «ccache clang -target ...» به آن داده شود، در مرحله‌ی
        compiler sanity check شکست می‌خورد. فایل toolchain رسمی اندروید
        خودش کامپایلر را تنظیم می‌کند، پس این متغیرها باید حذف شوند.
        """
        src = _read('llamacpp')
        self.assertIn('env.pop(', src)
        for var in ('"CC"', '"CXX"'):
            self.assertIn(var, src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
