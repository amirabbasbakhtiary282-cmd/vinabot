# -*- coding: utf-8 -*-
"""
تست‌های ایمنی راه‌اندازی — جلوگیری از کرش هنگام باز شدن برنامه

انگیزه (باگ واقعی گزارش‌شده توسط کاربر)
--------------------------------------------------------------------------
APK بیلد ۱۲ روی گوشی نصب شد، «Loading» را نشان داد و حدود یک ثانیه بعد
بدون هیچ پیامی بسته شد. لاگ هم در دسترس نبود.

سه علت مستقل پیدا و رفع شد:

۱) **بلاک شدن ترد اصلی** — ``VinaVoice.__init__`` که داخل
   ``VinaApp.build()`` روی ترد UI اجرا می‌شود، ``set_tts_language_fa()``
   را صدا می‌زد و آن تا ۵ ثانیه با ``ready.wait(timeout=5.0)`` منتظر
   می‌ماند. بلاک کردن ترد اصلی هنگام راه‌اندازی روی اندروید به ANR/کرش
   منجر می‌شود.

۲) **جدا نشدن ترد از JVM** — تردهای پس‌زمینه‌ای که با pyjnius کار
   می‌کنند باید ``jnius.detach()`` را قبل از خروج صدا بزنند، وگرنه ART
   با «Native thread exited without calling DetachCurrentThread» کل
   پروسه را abort می‌کند (مستندات رسمی pyjnius).

۳) **نبود شبکه‌ی ایمنی** — هر استثنایی در ``build()`` باعث بسته شدن
   بی‌صدای برنامه می‌شد.
"""

import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class TestMainThreadIsNotBlocked(unittest.TestCase):
    """هیچ کار مسدودکننده‌ای نباید در مسیر build() اجرا شود."""

    def test_voice_init_uses_async_tts(self):
        """VinaVoice نباید نسخه‌ی مسدودکننده را صدا بزند.

        این دقیقاً همان خطی بود که برنامه را می‌کشت.
        """
        src = _read('src/voice.py')
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != '__init__':
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                func = sub.func
                if isinstance(func, ast.Attribute):
                    self.assertNotEqual(
                        func.attr, 'set_tts_language_fa',
                        'VinaVoice.__init__ روی ترد اصلی اجرا می‌شود و '
                        'set_tts_language_fa تا ۵ ثانیه بلاک می‌کند؛ '
                        'باید از set_tts_language_fa_async استفاده شود.')

    def test_async_variant_exists_and_uses_thread(self):
        src = _read('src/android_bridge.py')
        self.assertIn('def set_tts_language_fa_async', src)
        start = src.index('def set_tts_language_fa_async')
        end = src.index('def set_tts_language_fa(', start)
        body = src[start:end]
        self.assertIn('Thread', body,
                      'نسخه‌ی async باید واقعاً روی ترد پس‌زمینه اجرا شود')

    def test_no_unbounded_wait_on_import_path(self):
        """هیچ wait/sleep بدون timeout در ماژول‌های راه‌اندازی نباشد."""
        for rel in ('src/voice.py', 'src/android_bridge.py'):
            src = _read(rel)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == 'wait':
                    has_timeout = bool(node.args) or any(
                        kw.arg == 'timeout' for kw in node.keywords)
                    self.assertTrue(
                        has_timeout,
                        f'{rel}: فراخوانی wait() بدون timeout می‌تواند '
                        f'برنامه را برای همیشه قفل کند')


class TestJniThreadsAreDetached(unittest.TestCase):
    """تردهای پس‌زمینه‌ای که JNI را لمس می‌کنند باید detach شوند."""

    def test_detach_helper_exists(self):
        src = _read('src/android_bridge.py')
        self.assertIn('def _detach_jnius', src)
        self.assertIn('jnius.detach()', src)

    def test_model_loader_thread_detaches(self):
        """ترد بارگذاری مدل از طریق model_paths با JNI کار می‌کند."""
        src = _read('main.py')
        self.assertIn('_detach_jnius', src,
                      'ترد بارگذاری مدل باید قبل از خروج از JVM جدا شود، '
                      'وگرنه ART کل پروسه را abort می‌کند')

    def test_tts_thread_detaches(self):
        src = _read('src/android_bridge.py')
        start = src.index('def set_tts_language_fa_async')
        end = src.index('def set_tts_language_fa(', start)
        self.assertIn('_detach_jnius', src[start:end])


class TestBuildHasFailsafe(unittest.TestCase):
    """build() هرگز نباید استثنا را به بیرون بدهد."""

    def test_build_wraps_everything_in_try(self):
        src = _read('main.py')
        tree = ast.parse(src)

        build_fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'build':
                build_fn = node
                break

        self.assertIsNotNone(build_fn, 'متد build پیدا نشد')

        # بدنه‌ی build باید عملاً فقط یک try/except باشد
        real_statements = [
            s for s in build_fn.body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
        ]
        self.assertTrue(
            all(isinstance(s, ast.Try) for s in real_statements),
            'کل بدنه‌ی build() باید داخل try/except باشد تا هر خطای '
            'غیرمنتظره به‌جای بستن بی‌صدای برنامه، صفحه‌ی خطا نشان دهد')

    def test_failsafe_screen_exists(self):
        src = _read('main.py')
        self.assertIn('def _build_failsafe_screen', src)
        self.assertIn('def _write_crash_log', src)

    def test_failsafe_uses_only_primitive_widgets(self):
        """صفحه‌ی خطا نباید به سیستم طراحی وابسته باشد.

        اگر تم یا design_system خودش خراب باشد، صفحه‌ی خطا هم از کار
        می‌افتد و دوباره کرش بی‌صدا می‌گیریم.
        """
        src = _read('main.py')
        start = src.index('def _build_failsafe_screen')
        end = src.index('def _request_runtime_permissions', start)
        body = src[start:end]
        for forbidden in ('GlassCard', 'theme.', 'PrimaryButton', 'fix_rtl'):
            self.assertNotIn(
                forbidden, body,
                f'صفحه‌ی خطای اضطراری نباید از «{forbidden}» استفاده کند')


class TestModelDiscoveryRobustness(unittest.TestCase):

    def test_finds_model_in_subdirectory(self):
        import tempfile
        from src import model_paths

        tmp = tempfile.mkdtemp()
        sub = os.path.join(tmp, 'gemma')
        os.makedirs(sub)
        target = os.path.join(sub, 'gemma-3-1b-it-Q4_K_M.gguf')
        with open(target, 'wb') as f:
            f.write(b'\0' * (2 * 1024 * 1024))

        original = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [tmp]
        try:
            self.assertEqual(model_paths.find_model(), target,
                             'مدل داخل زیرپوشه باید پیدا شود')
        finally:
            model_paths.candidate_dirs = original

    def test_ignores_partial_and_tiny_files(self):
        import tempfile
        from src import model_paths

        tmp = tempfile.mkdtemp()
        # فایل خالی (کپی ناموفق) و فایل نیمه‌کپی‌شده
        open(os.path.join(tmp, 'empty.gguf'), 'wb').close()
        with open(os.path.join(tmp, 'x.gguf.importing'), 'wb') as f:
            f.write(b'\0' * (2 * 1024 * 1024))

        original = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [tmp]
        try:
            self.assertIsNone(
                model_paths.find_model(),
                'فایل خالی یا نیمه‌کپی‌شده نباید به‌عنوان مدل معتبر '
                'انتخاب شود (باعث خطای مبهم در موتور می‌شود)')
        finally:
            model_paths.candidate_dirs = original

    def test_ensure_creates_all_candidate_dirs(self):
        import tempfile
        from src import model_paths

        tmp = tempfile.mkdtemp()
        a = os.path.join(tmp, 'a', 'models')
        b = os.path.join(tmp, 'b', 'models')

        original = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [a, b]
        try:
            model_paths.ensure_models_dir()
            self.assertTrue(os.path.isdir(a))
            self.assertTrue(os.path.isdir(b),
                            'همه‌ی مسیرهای شناخته‌شده باید ساخته شوند تا '
                            'کاربر هر کدام را باز کرد، وجود داشته باشد')
        finally:
            model_paths.candidate_dirs = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
