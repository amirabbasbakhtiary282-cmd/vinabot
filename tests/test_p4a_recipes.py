# -*- coding: utf-8 -*-
"""
تست‌های recipeهای python-for-android.

انگیزه‌ی این فایل یک شکست واقعی بیلد بود:

    Could not extract b5026 download, it must be .zip, .tar.gz or
    .tar.bz2 or .tar.xz

علت: p4a نام فایل دانلودی را با ``basename(versioned_url)`` می‌سازد
(pythonforandroid/recipe.py). آدرس codeload گیت‌هاب به «b5026» بدون پسوند
ختم می‌شد، پس p4a نمی‌دانست چطور استخراجش کند.

این تست‌ها همان قاعده را روی *همه‌ی* recipeها اعمال می‌کنند تا این دسته از
خطا دیگر فقط بعد از یک ساعت بیلد معلوم نشود.
"""

import ast
import os
import posixpath
import unittest
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES_DIR = os.path.join(ROOT, 'p4a-recipes')

# دقیقاً همان پسوندهایی که p4a می‌تواند استخراج کند
P4A_EXTRACTABLE = ('.zip', '.whl', '.tar.gz', '.tgz',
                   '.tar.bz2', '.tbz2', '.tar.xz', '.txz')


def _recipe_names():
    return sorted(
        name for name in os.listdir(RECIPES_DIR)
        if os.path.isdir(os.path.join(RECIPES_DIR, name))
        and os.path.exists(os.path.join(RECIPES_DIR, name, '__init__.py'))
    )


def _recipe_class_fields(name):
    """مقدار version/url را بدون import کردن recipe استخراج می‌کند.

    (import مستقیم ممکن نیست چون به ماژول‌های p4a و sh نیاز دارد.)
    """
    path = os.path.join(RECIPES_DIR, name, '__init__.py')
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=path)

    fields = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id not in ('version', 'url'):
                    continue
                try:
                    fields[target.id] = ast.literal_eval(stmt.value)
                except ValueError:
                    pass
    return fields


class TestRecipeUrls(unittest.TestCase):

    def test_recipes_exist(self):
        names = _recipe_names()
        for expected in ('llamacpp', 'vinallm', 'vosk'):
            self.assertIn(expected, names)

    def test_download_filename_has_extractable_extension(self):
        """basename هر URL باید پسوندی داشته باشد که p4a بشناسد."""
        for name in _recipe_names():
            fields = _recipe_class_fields(name)
            url = fields.get('url')
            if not url:
                continue  # recipeهایی مثل vinallm که سورس محلی دارند

            versioned = url.format(version=fields.get('version', '0'))
            filename = posixpath.basename(urlparse(versioned).path)

            self.assertTrue(
                filename.endswith(P4A_EXTRACTABLE),
                f"recipe «{name}»: نام فایل دانلودی «{filename}» پسوند قابل "
                f"استخراج ندارد. p4a با خطای «Could not extract» شکست "
                f"می‌خورد. URL: {versioned}",
            )

    def test_no_codeload_urls(self):
        """آدرس codeload دقیقاً همان تله‌ای است که یک بار بیلد را شکست."""
        for name in _recipe_names():
            url = _recipe_class_fields(name).get('url') or ''
            self.assertNotIn(
                'codeload.github.com', url,
                f"recipe «{name}»: آدرس codeload نام فایل بدون پسوند تولید "
                f"می‌کند؛ به‌جای آن از /archive/refs/tags/{{version}}.tar.gz "
                f"استفاده کنید.",
            )

    def test_urls_are_https(self):
        for name in _recipe_names():
            url = _recipe_class_fields(name).get('url')
            if url:
                self.assertTrue(url.startswith('https://'),
                                f'recipe «{name}» از https استفاده نمی‌کند')

    def test_version_placeholder_is_used(self):
        """اگر version تعریف شده، URL باید از آن استفاده کند (نه عدد ثابت)."""
        for name in _recipe_names():
            fields = _recipe_class_fields(name)
            url, version = fields.get('url'), fields.get('version')
            if url and version:
                self.assertIn('{version}', url,
                              f'recipe «{name}»: نسخه در URL هاردکد شده است')


class TestLlamaCppRecipe(unittest.TestCase):
    """تست‌های اختصاصی recipe که بیلد را شکسته بود."""

    def setUp(self):
        self.fields = _recipe_class_fields('llamacpp')

    def test_uses_github_archive_url(self):
        self.assertEqual(
            self.fields['url'],
            'https://github.com/ggml-org/llama.cpp/archive/refs/tags/{version}.tar.gz')

    def test_resolved_filename(self):
        versioned = self.fields['url'].format(version=self.fields['version'])
        self.assertTrue(versioned.endswith('.tar.gz'))
        self.assertEqual(posixpath.basename(versioned), 'b5026.tar.gz')

    def test_build_dir_matches_archive_root(self):
        """نام پوشه‌ی build باید با ریشه‌ی داخل تاربال یکی باشد.

        آرشیو گیت‌هاب پوشه‌ای به نام «llama.cpp-<tag>» می‌سازد؛ اگر
        get_build_dir چیز دیگری برگرداند، p4a پوشه را جابه‌جا می‌کند و
        مسیرهای built_libraries می‌شکند.
        """
        path = os.path.join(RECIPES_DIR, 'llamacpp', '__init__.py')
        with open(path, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('"llama.cpp-" + self.version', src)

    def test_expected_libraries_declared(self):
        path = os.path.join(RECIPES_DIR, 'llamacpp', '__init__.py')
        with open(path, encoding='utf-8') as f:
            src = f.read()
        for lib in ('libllama.so', 'libggml.so',
                    'libggml-base.so', 'libggml-cpu.so'):
            self.assertIn(lib, src)


class TestVoskRecipe(unittest.TestCase):

    def test_url_is_zip(self):
        fields = _recipe_class_fields('vosk')
        versioned = fields['url'].format(version=fields['version'])
        self.assertTrue(versioned.endswith('.zip'))
        self.assertEqual(posixpath.basename(versioned),
                         'vosk-android-0.3.45.zip')


if __name__ == '__main__':
    unittest.main(verbosity=2)
