# -*- coding: utf-8 -*-
"""
تست اجرای واقعی متدهای recipe با قرارداد فراخوانی p4a.

انگیزه: شکست دوم بیلد
    AttributeError: 'str' object has no attribute 'arch'

python-for-android در فراخوانی متدهای recipe **یکدست نیست** (تأییدشده از
سورس pythonforandroid/build.py):

    prepare_build_dir(arch)   -> رشته      (خط ۵۱۲)
    prebuild_arch(arch)       -> شیء Arch  (خط ۵۲۲)
    should_build(arch)        -> شیء Arch  (خط ۵۲۹)
    build_arch(arch)          -> شیء Arch  (خط ۵۳۰)
    install_libraries(arch)   -> شیء Arch  (خط ۵۳۳)

این تست‌ها recipeها را با ماژول‌های جعلی p4a واقعاً **اجرا** می‌کنند (نه
فقط متن را می‌خوانند) تا این دسته از خطا قبل از یک بیلد یک‌ساعته پیدا شود.
"""

import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, 'p4a-recipes')


class FakeArch:
    """شبیه‌سازی pythonforandroid.archs.Arch"""

    def __init__(self, name='arm64-v8a'):
        self.arch = name

    def __str__(self):
        return self.arch


def _install_fake_p4a():
    """ماژول‌های جعلی p4a و sh را در sys.modules می‌گذارد.

    این‌طور می‌توانیم recipeها را import و اجرا کنیم بدون نصب کل p4a.
    """
    created = []

    def _mod(name):
        m = types.ModuleType(name)
        sys.modules[name] = m
        created.append(name)
        return m

    if 'sh' not in sys.modules:
        sh = _mod('sh')
        sh.Command = lambda *a, **k: (lambda *args, **kw: None)
        sh.cp = lambda *a, **k: None
        sh.cmake = lambda *a, **k: None
        sh.find = lambda *a, **k: ''

    if 'pythonforandroid' not in sys.modules:
        _mod('pythonforandroid')

    if 'pythonforandroid.logger' not in sys.modules:
        logger = _mod('pythonforandroid.logger')
        logger.info = lambda *a, **k: None
        logger.shprint = lambda *a, **k: None
        logger.info_main = lambda *a, **k: None

    if 'pythonforandroid.recipe' not in sys.modules:
        recipe_mod = _mod('pythonforandroid.recipe')

        class Recipe:
            """حداقل پیاده‌سازی سازگار با کلاس پایه‌ی واقعی."""
            version = None
            url = None
            depends = []
            built_libraries = {}
            name = None

            def __init__(self):
                self.ctx = types.SimpleNamespace(
                    build_dir='/tmp/fake-build', ndk_api=24,
                    ndk_dir='/tmp/fake-ndk', local_recipes=None)

            def get_build_container_dir(self, arch):
                # کلاس واقعی هم از format استفاده می‌کند، پس شیء Arch
                # از طریق __str__ به نام معماری تبدیل می‌شود.
                return os.path.join(
                    self.ctx.build_dir, 'other_builds', self.name or 'x',
                    '{}__ndk_target_{}'.format(arch, self.ctx.ndk_api))

            def get_build_dir(self, arch):
                return os.path.join(self.get_build_container_dir(arch),
                                    self.name or 'x')

            def prepare_build_dir(self, arch):
                return None

            def get_recipe_env(self, arch=None, **kwargs):
                return {'CC': 'clang'}

            @staticmethod
            def get_recipe(name, ctx):
                raise NotImplementedError

        recipe_mod.Recipe = Recipe

    if 'pythonforandroid.util' not in sys.modules:
        util = _mod('pythonforandroid.util')
        util.ensure_dir = lambda p: os.makedirs(p, exist_ok=True)

        class _CD:
            def __init__(self, d):
                self.d = d

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        util.current_directory = _CD

    return created


def _load_recipe(name):
    """recipe را به‌عنوان ماژول مستقل بارگذاری می‌کند."""
    import importlib.util
    _install_fake_p4a()
    path = os.path.join(RECIPES, name, '__init__.py')
    spec = importlib.util.spec_from_file_location(f'_recipe_{name}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestArchNameHelper(unittest.TestCase):
    """تابع arch_name باید هر دو نوع ورودی را بپذیرد."""

    def test_all_recipes_have_helper(self):
        for name in ('llamacpp', 'vinallm', 'vosk'):
            mod = _load_recipe(name)
            self.assertTrue(hasattr(mod, 'arch_name'),
                            f'recipe «{name}» تابع arch_name ندارد')

    def test_accepts_string(self):
        for name in ('llamacpp', 'vinallm', 'vosk'):
            mod = _load_recipe(name)
            self.assertEqual(mod.arch_name('arm64-v8a'), 'arm64-v8a')

    def test_accepts_arch_object(self):
        for name in ('llamacpp', 'vinallm', 'vosk'):
            mod = _load_recipe(name)
            self.assertEqual(mod.arch_name(FakeArch('armeabi-v7a')),
                             'armeabi-v7a')


class TestPrepareBuildDirAcceptsString(unittest.TestCase):
    """بازتولید دقیق شکست بیلد: p4a اینجا *رشته* پاس می‌دهد."""

    def test_vinallm_prepare_build_dir_with_string(self):
        mod = _load_recipe('vinallm')
        recipe = mod.VinaLlmRecipe()
        recipe.name = 'vinallm'
        with tempfile.TemporaryDirectory() as tmp:
            recipe.ctx.build_dir = tmp
            # این دقیقاً همان فراخوانی build.py:512 است که کرش می‌کرد
            recipe.prepare_build_dir('arm64-v8a')
            self.assertTrue(os.path.isdir(recipe.get_build_dir('arm64-v8a')))

    def test_vinallm_prepare_build_dir_with_object_too(self):
        """حتی اگر p4a روزی رفتارش را عوض کند، نباید بشکند."""
        mod = _load_recipe('vinallm')
        recipe = mod.VinaLlmRecipe()
        recipe.name = 'vinallm'
        with tempfile.TemporaryDirectory() as tmp:
            recipe.ctx.build_dir = tmp
            recipe.prepare_build_dir(FakeArch('arm64-v8a'))
            self.assertTrue(os.path.isdir(recipe.get_build_dir('arm64-v8a')))

    def test_get_build_dir_same_for_string_and_object(self):
        """مسیر باید یکسان باشد، وگرنه استخراج و بیلد در دو جای مختلف می‌افتند."""
        for name, cls in (('vinallm', 'VinaLlmRecipe'),
                          ('llamacpp', 'LlamaCppRecipe'),
                          ('vosk', 'VoskRecipe')):
            mod = _load_recipe(name)
            recipe = getattr(mod, cls)()
            recipe.name = name
            self.assertEqual(recipe.get_build_dir('arm64-v8a'),
                             recipe.get_build_dir(FakeArch('arm64-v8a')),
                             f'recipe «{name}»: مسیر build برای رشته و شیء فرق دارد')


class TestShouldBuildAcceptsArchObject(unittest.TestCase):
    """should_build یک شیء Arch می‌گیرد (build.py:529)."""

    def test_vosk_should_build(self):
        mod = _load_recipe('vosk')
        recipe = mod.VoskRecipe()
        recipe.name = 'vosk'
        with tempfile.TemporaryDirectory() as tmp:
            recipe.ctx.build_dir = tmp
            # نباید AttributeError بدهد
            self.assertTrue(recipe.should_build(FakeArch('arm64-v8a')))

            # وقتی کتابخانه موجود باشد، باید False برگرداند
            bd = recipe.get_build_dir('arm64-v8a')
            os.makedirs(bd, exist_ok=True)
            with open(os.path.join(bd, 'libvosk.so'), 'w') as f:
                f.write('x')
            self.assertFalse(recipe.should_build(FakeArch('arm64-v8a')))


class TestVoskDoesNotBreakUnpack(unittest.TestCase):
    """باگ بی‌صدا: ساختن پوشه‌ی build از قبل، استخراج را لغو می‌کند.

    در p4a متد unpack فقط وقتی استخراج می‌کند که پوشه‌ی مقصد وجود نداشته
    باشد:
        if not exists(directory_name) or not isdir(directory_name):
    پس recipe نباید در prepare_build_dir آن پوشه را از قبل بسازد.
    """

    def test_vosk_does_not_override_prepare_build_dir(self):
        mod = _load_recipe('vosk')
        self.assertNotIn('prepare_build_dir', vars(mod.VoskRecipe),
                         'VoskRecipe نباید prepare_build_dir را override کند - '
                         'این باعث می‌شود آرشیو هرگز استخراج نشود')

    def test_no_recipe_ensure_dirs_its_own_build_dir_before_unpack(self):
        """هیچ recipe ای که url دارد نباید پوشه‌ی build را زودتر بسازد."""
        for name in ('llamacpp', 'vosk'):
            path = os.path.join(RECIPES, name, '__init__.py')
            with open(path, encoding='utf-8') as f:
                src = f.read()
            if 'def prepare_build_dir' in src:
                self.assertNotIn(
                    'ensure_dir(self.get_build_dir', src,
                    f'recipe «{name}»: ساختن پوشه‌ی build قبل از unpack '
                    f'باعث می‌شود استخراج نادیده گرفته شود')


class TestNoRawArchAttributeAccess(unittest.TestCase):
    """جز داخل خود arch_name، جایی نباید مستقیم arch.arch بنویسد."""

    def test_no_bare_arch_arch(self):
        """با AST بررسی می‌شود، نه متن ساده.

        جستجوی متنی روی docstringها و کامنت‌های فارسی مثبت کاذب می‌دهد؛
        AST فقط دسترسی‌های واقعی به صفت را می‌بیند.
        """
        import ast

        for name in ('llamacpp', 'vinallm', 'vosk'):
            path = os.path.join(RECIPES, name, '__init__.py')
            with open(path, encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=path)

            # بدنه‌ی تابع arch_name تنها جای مجاز است
            allowed = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == 'arch_name':
                    for sub in ast.walk(node):
                        allowed.add(id(sub))

            offenders = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                if node.attr != 'arch':
                    continue
                if not (isinstance(node.value, ast.Name) and node.value.id == 'arch'):
                    continue
                if id(node) in allowed:
                    continue
                offenders.append(f'{name}: خط {node.lineno}')

            self.assertEqual(
                offenders, [],
                'دسترسی مستقیم به arch.arch پیدا شد؛ از arch_name(arch) '
                'استفاده کنید: ' + ', '.join(offenders))


if __name__ == '__main__':
    unittest.main(verbosity=2)
