# -*- coding: utf-8 -*-
"""
تست ثابت‌های حیاتی buildozer.spec

چرا این تست‌ها؟ چند خواسته‌ی صریح پروژه مستقیماً به مقادیر این فایل
وابسته‌اند و یک تغییر کوچک و بی‌دقت می‌تواند بی‌سروصدا آن‌ها را نقض کند
(مثلاً APK چند صد مگابایتی شود یا مجوز میکروفون از دست برود). این
تست‌ها چند ثانیه طول می‌کشند، در حالی که کشف همین مشکلات بعد از یک بیلد
سه‌ساعته بسیار پرهزینه است.
"""

import configparser
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'buildozer.spec')


def _config():
    parser = configparser.ConfigParser()
    with open(SPEC, encoding='utf-8') as f:
        parser.read_file(f)
    return parser


def _list(parser, key):
    raw = parser.get('app', key, fallback='')
    return [item.strip() for item in raw.split(',') if item.strip()]


class TestModelIsNotBundled(unittest.TestCase):
    """مدل هرگز نباید داخل APK برود - خواسته‌ی صریح پروژه."""

    def test_gguf_not_in_include_exts(self):
        exts = [e.lower() for e in _list(_config(), 'source.include_exts')]
        self.assertNotIn(
            'gguf', exts,
            'پسوند gguf در source.include_exts باعث می‌شود فایل مدل داخل '
            'APK بسته‌بندی شود و حجم آن صدها مگابایت شود. مدل باید در '
            'زمان اجرا از حافظه‌ی دستگاه خوانده شود.')

    def test_gguf_not_in_include_patterns(self):
        patterns = _list(_config(), 'source.include_patterns')
        for pattern in patterns:
            self.assertNotIn(
                'gguf', pattern.lower(),
                f'الگوی «{pattern}» فایل مدل را وارد APK می‌کند')

    def test_gguf_explicitly_excluded(self):
        exts = [e.lower() for e in _list(_config(), 'source.exclude_exts')]
        self.assertIn('gguf', exts,
                      'برای اطمینان مضاعف، gguf باید صریحاً exclude شود')


class TestArchitectureAndApi(unittest.TestCase):

    def test_targets_android_8_or_lower_minapi(self):
        """هدف پروژه «اندروید ۸ به بالا» است → minapi حداکثر ۲۶."""
        parser = _config()
        minapi = int(parser.get('app', 'android.minapi'))
        self.assertLessEqual(
            minapi, 26,
            f'minapi={minapi} یعنی برنامه روی اندروید ۸ (API 26) نصب نمی‌شود')

    def test_ndk_api_matches_minapi(self):
        """ناهماهنگی این دو باعث خطاهای عجیب در زمان لینک می‌شود."""
        parser = _config()
        self.assertEqual(parser.get('app', 'android.ndk_api'),
                         parser.get('app', 'android.minapi'))

    def test_arch_is_supported_by_recipes(self):
        """معماری هدف باید در ABI_MAP همه‌ی recipeها موجود باشد."""
        archs = _list(_config(), 'android.archs')
        self.assertTrue(archs)
        for arch in archs:
            self.assertIn(arch, ('arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'))


class TestRequirements(unittest.TestCase):

    def test_no_llama_cpp_python(self):
        """استفاده از llama-cpp-python صریحاً ممنوع است."""
        reqs = ','.join(_list(_config(), 'requirements')).lower()
        self.assertNotIn('llama-cpp-python', reqs)
        self.assertNotIn('llama_cpp_python', reqs)

    def test_native_llama_recipes_present(self):
        reqs = _list(_config(), 'requirements')
        for name in ('llamacpp', 'vinallm'):
            self.assertIn(name, reqs,
                          f'recipe «{name}» برای اجرای native مدل لازم است')

    def test_local_recipes_configured(self):
        parser = _config()
        self.assertIn('p4a-recipes',
                      parser.get('app', 'p4a.local_recipes'))

    def test_every_local_recipe_dir_exists(self):
        """هر recipe ذکرشده در requirements باید واقعاً وجود داشته باشد."""
        recipes_dir = os.path.join(ROOT, 'p4a-recipes')
        available = {
            name for name in os.listdir(recipes_dir)
            if os.path.isdir(os.path.join(recipes_dir, name))
        }
        for name in ('llamacpp', 'vinallm', 'vosk'):
            if name in _list(_config(), 'requirements'):
                self.assertIn(name, available,
                              f'recipe «{name}» در requirements هست ولی '
                              f'پوشه‌اش در p4a-recipes وجود ندارد')


class TestPermissions(unittest.TestCase):

    def test_record_audio_present(self):
        """بدون این مجوز، هیچ قابلیت صوتی کار نمی‌کند."""
        perms = ','.join(_list(_config(), 'android.permissions'))
        self.assertIn('RECORD_AUDIO', perms)

    def test_internet_present(self):
        perms = ','.join(_list(_config(), 'android.permissions'))
        self.assertIn('INTERNET', perms)

    def test_no_legacy_storage_permission(self):
        """READ/WRITE_EXTERNAL_STORAGE دیگر لازم نیست و مضر است.

        از اندروید ۱۰+ (Scoped Storage) این مجوزها عملاً بی‌اثرند و
        گوگل‌پلی هم برای آن‌ها توجیه می‌خواهد. وارد کردن مدل از طریق
        Storage Access Framework انجام می‌شود که هیچ مجوزی لازم ندارد.
        """
        perms = ','.join(_list(_config(), 'android.permissions'))
        self.assertNotIn('WRITE_EXTERNAL_STORAGE', perms)
        self.assertNotIn('MANAGE_EXTERNAL_STORAGE', perms)


class TestExcludedDirs(unittest.TestCase):

    def test_heavy_dirs_excluded(self):
        excluded = [d.lower() for d in _list(_config(), 'source.exclude_dirs')]
        for name in ('tests', 'bin', 'models', 'memory'):
            self.assertIn(name, excluded,
                          f'پوشه‌ی «{name}» نباید داخل APK کپی شود')

    def test_p4a_recipes_excluded_from_app_sources(self):
        """recipeها کد بیلد هستند، نه کد برنامه.

        نکته: این کار بی‌خطر است چون buildozer مسیر recipeها را مستقیماً
        از ریشه‌ی پروژه به p4a می‌دهد (تأییدشده در لاگ بیلد:
        «--local-recipes /home/runner/work/vinabot/vinabot/p4a-recipes»)،
        نه از روی نسخه‌ی کپی‌شده در app dir.
        """
        excluded = [d.lower() for d in _list(_config(), 'source.exclude_dirs')]
        self.assertIn('p4a-recipes', excluded)


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestNoEmptyListValuedKeys(unittest.TestCase):
    """هیچ کلید لیستی نباید با مقدار خالی رها شود.

    ریشه‌ی شکست بیلد شماره ۸ (تأییدشده با اجرای واقعی buildozer):

        android.gradle_dependencies =

    این خط به‌نظر «هیچ وابستگی‌ای» می‌آید، اما SpecParser.getlist در عمل
    ``['']`` برمی‌گرداند نه ``[]``:

        مقدار '' است که None نیست → default برگردانده نمی‌شود
        ''.split(',') == ['']        (specparser.py خطوط ۸۶-۹۲)

    بعد targets/android.py (خط ۹۷۲) به ازای هر عضو یک «--depend» اضافه
    می‌کند، پس p4a آرگومان ``--depend ''`` می‌گیرد و آن رشته‌ی خالی داخل
    build.gradle می‌نشیند. Gradle شکست می‌خورد:

        Supplied String module notation '' is invalid.

    نکته‌ی مهم: این کلیدها باید **کامنت** شوند، نه اینکه خالی بمانند.
    """

    # کلیدهایی که buildozer با getlist می‌خواند (از سورس buildozer
    # استخراج شده‌اند). مقدار خالی برای این‌ها خطرناک است.
    LIST_KEYS = (
        'android.gradle_dependencies',
        'android.add_jars',
        'android.add_aars',
        'android.add_src',
        'android.add_activities',
        'android.add_assets',
        'android.add_resources',
        'android.add_compile_options',
        'android.add_gradle_repositories',
        'android.add_packaging_options',
        'android.features',
        'android.permissions',
        'android.res_xml',
        'services',
        'requirements',
        'source.include_exts',
        'source.exclude_exts',
        'source.exclude_dirs',
        'source.exclude_patterns',
    )

    def test_no_list_key_is_present_but_empty(self):
        import re

        with open(SPEC, encoding='utf-8') as f:
            lines = f.readlines()

        offenders = []
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            match = re.match(r'^([A-Za-z0-9_.]+)\s*=\s*(.*)$', stripped)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if key in self.LIST_KEYS and value == '':
                offenders.append(f'خط {number}: {key}')

        self.assertEqual(
            [], offenders,
            'این کلیدهای لیستی مقدار خالی دارند و باعث می‌شوند buildozer '
            'یک رشته‌ی خالی به p4a پاس بدهد (مثلاً --depend \'\') که Gradle '
            'را می‌شکند. آن‌ها را کامنت کنید یا مقدار واقعی بدهید:\n  '
            + '\n  '.join(offenders))

    def test_gradle_dependencies_parses_to_empty_list(self):
        """بررسی رفتار واقعی، نه فقط متن فایل.

        اگر buildozer نصب باشد، دقیقاً همان تابعی که در بیلد اجرا می‌شود
        صدا زده می‌شود تا مطمئن شویم [''] برنمی‌گردد.
        """
        try:
            from buildozer.specparser import SpecParser
        except Exception:
            self.skipTest('buildozer نصب نیست')

        parser = SpecParser()
        parser.read(SPEC)
        value = parser.getlist('app', 'android.gradle_dependencies', [])
        self.assertNotIn(
            '', value or [],
            "getlist مقدار [''] برگرداند؛ این باعث «--depend ''» و شکست "
            "Gradle با «Supplied String module notation '' is invalid» "
            "می‌شود.")
