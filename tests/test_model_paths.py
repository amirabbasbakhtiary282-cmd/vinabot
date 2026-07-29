# -*- coding: utf-8 -*-
"""
تست منطق پیدا کردن مدل GGUF

انگیزه
--------------------------------------------------------------------------
خواسته‌ی صریح پروژه:

  «کاربر مدل را بعد از نصب APK به‌صورت دستی در پوشه‌ی Models برنامه
   می‌گذارد. برنامه باید مدل را خودکار تشخیص دهد. نام مدل پیش‌فرض
   gemma-3-1b-it-Q4_K_M.gguf است و نباید هیچ تغییری در کد لازم باشد.
   اگر مدلی نبود، برنامه نباید کرش کند.»

نسخه‌ی قبلی سه مشکل داشت:
  ۱) فقط در حافظه‌ی *خصوصی* برنامه دنبال مدل می‌گشت، جایی که کاربر روی
     گوشی روت‌نشده اصلاً نمی‌تواند فایل کپی کند.
  ۲) src/brain.py و src/model_downloader.py دو لیست مسیر *متفاوت*
     داشتند، پس ممکن بود مدل در جایی ذخیره شود که موتور نمی‌بیند.
  ۳) پوشه‌ی مدل‌ها فقط هنگام دانلود ساخته می‌شد، نه هنگام شروع برنامه.
"""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import model_paths  # noqa: E402


class TestFindModels(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._orig = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [self.tmp.name]
        self.addCleanup(lambda: setattr(model_paths, 'candidate_dirs', self._orig))

    def _touch(self, name):
        path = os.path.join(self.tmp.name, name)
        with open(path, 'wb') as f:
            f.write(b'GGUF fake')
        return path

    def test_no_model_returns_none_and_does_not_raise(self):
        """نبودِ مدل باید None برگرداند، نه استثنا (شرط: برنامه کرش نکند)."""
        self.assertIsNone(model_paths.find_model())
        self.assertEqual(model_paths.find_models(), [])

    def test_finds_any_gguf_regardless_of_name(self):
        self._touch('some-random-model.gguf')
        found = model_paths.find_model()
        self.assertIsNotNone(found)
        self.assertTrue(found.endswith('some-random-model.gguf'))

    def test_default_model_is_preferred(self):
        """اگر چند مدل باشد، مدل پیش‌فرض پروژه اولویت دارد."""
        self._touch('aaa-other-model.gguf')   # از نظر الفبا اول می‌آید
        self._touch(model_paths.DEFAULT_MODEL_NAME)
        found = model_paths.find_model()
        self.assertEqual(os.path.basename(found),
                         model_paths.DEFAULT_MODEL_NAME)

    def test_default_model_needs_no_code_change(self):
        """دقیقاً همان نام فایل خواسته‌شده باید بدون تنظیم اضافه کار کند."""
        self._touch('gemma-3-1b-it-Q4_K_M.gguf')
        found = model_paths.find_model()
        self.assertIsNotNone(found, 'مدل پیش‌فرض پروژه تشخیص داده نشد')
        self.assertTrue(found.endswith('gemma-3-1b-it-Q4_K_M.gguf'))

    def test_case_insensitive_extension(self):
        """برخی کاربران فایل را با پسوند بزرگ کپی می‌کنند."""
        self._touch('model.GGUF')
        self.assertIsNotNone(model_paths.find_model())

    def test_non_gguf_files_ignored(self):
        self._touch('readme.txt')
        self._touch('model.bin')
        self.assertIsNone(model_paths.find_model())

    def test_unreadable_directory_does_not_break_search(self):
        """یک مسیر خراب نباید کل جستجو را از کار بیندازد."""
        good = self._touch('good.gguf')
        model_paths.candidate_dirs = lambda: [
            '/nonexistent/path/definitely/not/here',
            self.tmp.name,
        ]
        self.assertEqual(model_paths.find_model(), good)

    def test_duplicates_are_not_listed_twice(self):
        self._touch('dup.gguf')
        model_paths.candidate_dirs = lambda: [self.tmp.name, self.tmp.name]
        self.assertEqual(len(model_paths.find_models()), 1)


class TestEnsureModelsDir(unittest.TestCase):

    def test_creates_directory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = os.path.join(tmp.name, 'models')

        orig = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [target]
        self.addCleanup(lambda: setattr(model_paths, 'candidate_dirs', orig))

        created = model_paths.ensure_models_dir()
        self.assertTrue(os.path.isdir(created))
        self.assertEqual(os.path.realpath(created), os.path.realpath(target))

    def test_writes_readme_for_user(self):
        """فایل راهنما باید نام مدل پیش‌فرض را داشته باشد."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = os.path.join(tmp.name, 'models')

        orig = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: [target]
        self.addCleanup(lambda: setattr(model_paths, 'candidate_dirs', orig))

        model_paths.ensure_models_dir()
        readme = os.path.join(target, 'README.txt')
        self.assertTrue(os.path.exists(readme))
        with open(readme, encoding='utf-8') as f:
            content = f.read()
        self.assertIn(model_paths.DEFAULT_MODEL_NAME, content)

    def test_never_returns_none(self):
        """حتی وقتی هیچ مسیری قابل نوشتن نیست، باید مسیری برگردد."""
        orig = model_paths.candidate_dirs
        model_paths.candidate_dirs = lambda: ['/proc/impossible/models']
        self.addCleanup(lambda: setattr(model_paths, 'candidate_dirs', orig))
        self.assertIsNotNone(model_paths.get_models_dir())


class TestAndroidPathPriority(unittest.TestCase):
    """روی اندروید، مسیر قابل‌دسترس برای کاربر باید اول باشد."""

    def test_external_dir_comes_before_private_dir(self):
        dirs = model_paths._android_dirs()
        joined = [d for d in dirs]

        external = [i for i, d in enumerate(joined)
                    if 'Android/data' in d or 'Android\\data' in d]
        private = [i for i, d in enumerate(joined) if d.startswith('/data/data')]

        self.assertTrue(external, f'هیچ مسیر external ای وجود ندارد: {joined}')
        if private:
            self.assertLess(
                min(external), min(private),
                'مسیر external (که کاربر می‌تواند در آن فایل کپی کند) باید '
                'قبل از حافظه‌ی خصوصی بررسی شود، وگرنه خواسته‌ی «کاربر مدل '
                'را دستی کپی می‌کند» عملاً غیرممکن است')

    def test_download_folder_is_a_fallback(self):
        """اندروید ۱۱+ ممکن است Android/data را محدود کند."""
        dirs = model_paths._android_dirs()
        self.assertTrue(
            any('Download' in d for d in dirs),
            'پوشه‌ی Download باید به‌عنوان مسیر پشتیبان بررسی شود چون در '
            'اندروید ۱۱+ همیشه برای کاربر قابل دسترسی است')


class TestSingleSourceOfTruth(unittest.TestCase):
    """brain و model_downloader نباید منطق مسیر جداگانه داشته باشند."""

    def _src(self, rel):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            return f.read()

    def test_brain_uses_shared_module(self):
        src = self._src('src/brain.py')
        self.assertIn('model_paths', src)
        self.assertNotIn("'/data/data/org.vinabot/files/models'", src,
                         'مسیر ثابت نباید در brain.py تکرار شود')

    def test_downloader_uses_shared_module(self):
        src = self._src('src/model_downloader.py')
        self.assertIn('model_paths', src)
        self.assertNotIn("'/data/data/org.vinabot/files/models'", src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
