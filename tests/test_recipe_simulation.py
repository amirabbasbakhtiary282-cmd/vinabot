# -*- coding: utf-8 -*-
"""
شبیه‌سازی ترتیب واقعی فراخوانی p4a روی recipeها

چرا این تست از همه‌ی تست‌های دیگر recipe ارزشمندتر است؟
--------------------------------------------------------------------------
بقیه‌ی تست‌های recipe متن سورس را می‌خوانند (AST/regex). این تست
recipeها را **واقعاً اجرا می‌کند** - با همان ترتیبی که p4a صدا می‌زند و
با همان شکل متغیر CC که p4a می‌سازد (شامل پیشوند ccache).

باگی که این الگو می‌گیرد، دقیقاً همان چیزی است که بیلد شماره ۷ را
شکست: recipe به‌جای کامپایلر، ``ccache`` را اجرا می‌کرد. آن باگ روی
ماشین بدون ccache دیده نمی‌شد؛ اینجا ccache همیشه در محیط شبیه‌سازی‌شده
حاضر است تا دیگر پنهان نماند.
"""

import importlib.util
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, 'p4a-recipes')

# دقیقاً شکلی که pythonforandroid/archs.py می‌سازد وقتی ccache نصب است
CCACHE_CC = ('/usr/bin/ccache /ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/'
             'clang -target aarch64-linux-android24 -fPIC')


class FakeArch:
    arch = 'arm64-v8a'
    command_prefix = 'aarch64-linux-android'
    arch_cflags = ['-march=armv8-a', '-fPIC']
    target = 'aarch64-linux-android24'
    clang_exe = '/ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/clang'
    clang_exe_cxx = '/ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/clang++'

    def __str__(self):
        return self.arch


def _install_fakes(recorded, tmp):
    """ماژول‌های جعلی p4a/sh را نصب می‌کند و دستورات اجراشده را ثبت می‌کند."""

    class FakeCmd:
        def __init__(self, name):
            self.name = name

        def __call__(self, *args, **kwargs):
            recorded.append((self.name, [str(a) for a in args]))
            return ''

    sh = types.ModuleType('sh')
    sh.Command = lambda path: FakeCmd(str(path))
    sh.cmake = FakeCmd('cmake')
    sh.cp = FakeCmd('cp')
    sh.find = lambda *a, **k: ''
    sys.modules['sh'] = sh

    sys.modules['pythonforandroid'] = types.ModuleType('pythonforandroid')

    logger = types.ModuleType('pythonforandroid.logger')
    for name in ('info', 'debug', 'warning', 'error', 'info_main', 'info_notify'):
        setattr(logger, name, lambda *a, **k: None)
    logger.shprint = lambda cmd, *a, **k: cmd(*a, **k)
    sys.modules['pythonforandroid.logger'] = logger

    util = types.ModuleType('pythonforandroid.util')
    util.ensure_dir = lambda p: os.makedirs(p, exist_ok=True)

    class _CD:
        def __init__(self, d):
            self.d = d

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    util.current_directory = _CD
    sys.modules['pythonforandroid.util'] = util

    recipe_mod = types.ModuleType('pythonforandroid.recipe')

    class Recipe:
        version = None
        url = None
        depends = []
        built_libraries = {}
        name = None
        need_stl_shared = False

        def __init__(self):
            def libs_dir(a):
                path = os.path.join(tmp, 'libs', a)
                os.makedirs(path, exist_ok=True)
                return path

            self.ctx = types.SimpleNamespace(
                build_dir=tmp, ndk_api=24, ndk_dir='/ndk',
                local_recipes=None,
                packages_path=os.path.join(tmp, 'packages'),
                get_libs_dir=libs_dir)

        def get_build_container_dir(self, arch):
            return os.path.join(self.ctx.build_dir, 'other_builds',
                                self.name or 'x',
                                '{}__ndk_target_24'.format(arch))

        def get_build_dir(self, arch):
            return os.path.join(self.get_build_container_dir(arch),
                                self.name or 'x')

        def prepare_build_dir(self, arch):
            pass

        def should_build(self, arch):
            return True

        def install_libraries(self, arch):
            pass

        def download_file(self, url, name, cwd=None):
            raise RuntimeError('شبیه‌سازی: شبکه در دسترس نیست')

        def get_recipe_env(self, arch=None, with_flags_in_cc=True, **kwargs):
            if with_flags_in_cc:
                return {'CC': CCACHE_CC, 'CXX': CCACHE_CC + '++'}
            return {'CC': '/usr/bin/ccache ' + FakeArch.clang_exe,
                    'CXX': '/usr/bin/ccache ' + FakeArch.clang_exe_cxx,
                    'CFLAGS': '-fPIC', 'LDFLAGS': '-L/x'}

        @staticmethod
        def get_recipe(name, ctx):
            module = _load(name)
            cls = _recipe_class(module)
            obj = cls()
            obj.name = name
            return obj

    recipe_mod.Recipe = Recipe
    sys.modules['pythonforandroid.recipe'] = recipe_mod


def _load(name):
    path = os.path.join(RECIPES, name, '__init__.py')
    spec = importlib.util.spec_from_file_location('_sim_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recipe_class(module):
    found = None
    for value in vars(module).values():
        if isinstance(value, type) and value.__name__.endswith('Recipe'):
            found = value
    return found


class TestRecipeExecution(unittest.TestCase):

    def _run(self, name):
        recorded = []
        tmp = tempfile.mkdtemp()
        _install_fakes(recorded, tmp)
        module = _load(name)
        recipe = _recipe_class(module)()
        recipe.name = name
        arch = FakeArch()

        recipe.prepare_build_dir(arch.arch)
        recipe.should_build(arch)
        os.makedirs(recipe.get_build_dir(arch.arch), exist_ok=True)
        error = None
        try:
            recipe.build_arch(arch)
        except Exception as exc:  # noqa: BLE001
            # در شبیه‌سازی، cmake/clang واقعی اجرا نمی‌شوند، پس بررسی‌های
            # «خروجی ساخته نشد» طبیعتاً خطا می‌دهند. خودِ خطا مهم نیست؛
            # مهم این است که چه دستوری اجرا شده.
            error = exc
        return recorded, error

    def test_no_recipe_invokes_ccache_as_compiler(self):
        """هیچ recipe ای نباید ccache را به‌عنوان کامپایلر اجرا کند.

        این همان شکستی است که در بیلد شماره ۷ رخ داد:
            RAN: /usr/bin/ccache -std=c++17 -shared ...
            /usr/bin/ccache: invalid option -- 't'
        """
        for name in ('llamacpp', 'vinallm', 'vosk'):
            recorded, _ = self._run(name)
            for executable, args in recorded:
                self.assertNotIn(
                    'ccache', executable,
                    f'recipe «{name}» برنامه‌ی «{executable}» را اجرا کرد؛ '
                    f'ccache کامپایلر نیست و روی پرچم‌هایی مثل -std خطا '
                    f'می‌دهد. آرگومان‌ها: {args[:6]}')

    def test_vinallm_uses_clangxx_with_target(self):
        """کامپایل باید با clang++ و پرچم -target درست انجام شود."""
        recorded, _ = self._run('vinallm')
        compiles = [(e, a) for e, a in recorded if 'clang' in e]
        self.assertTrue(compiles, 'هیچ فراخوانی کامپایلری ثبت نشد')

        executable, args = compiles[0]
        self.assertTrue(executable.endswith('clang++'),
                        f'باید clang++ باشد (کد C++ است)، ولی {executable} بود')
        self.assertIn('-target', args)
        self.assertIn('aarch64-linux-android24', args)
        self.assertIn('-std=c++17', args)
        self.assertIn('--no-undefined', ' '.join(args))

    def test_llamacpp_passes_android_toolchain_to_cmake(self):
        recorded, _ = self._run('llamacpp')
        cmake_calls = [a for e, a in recorded if e == 'cmake']
        self.assertTrue(cmake_calls, 'cmake اصلاً صدا زده نشد')
        joined = ' '.join(cmake_calls[0])
        self.assertIn('android.toolchain.cmake', joined)
        self.assertIn('-DANDROID_ABI=arm64-v8a', joined)
        self.assertIn('-DBUILD_SHARED_LIBS=ON', joined)

    def test_vosk_failure_does_not_raise(self):
        """شکست دانلود vosk نباید کل بیلد APK را از بین ببرد."""
        _, error = self._run('vosk')
        self.assertIsNone(
            error,
            'recipe وسک استثنا داد؛ این کل بیلد APK را متوقف می‌کند در '
            'حالی که تشخیص گفتار آفلاین یک قابلیت اختیاری است.')

    def test_build_failures_are_reported_not_silent(self):
        """recipeهای اصلی باید نبود خروجی را با خطای روشن گزارش کنند."""
        for name in ('llamacpp', 'vinallm'):
            _, error = self._run(name)
            self.assertIsNotNone(
                error,
                f'recipe «{name}» وقتی هیچ کتابخانه‌ای ساخته نشده بود '
                f'سکوت کرد؛ باید صریحاً خطا بدهد وگرنه APK ناقص تولید '
                f'می‌شود و مشکل تا زمان اجرا روی گوشی پنهان می‌ماند.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
