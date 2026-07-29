# -*- coding: utf-8 -*-
"""
تست import شدن همه‌ی ماژول‌های رابط کاربری

چرا این تست ارزش دارد؟
--------------------------------------------------------------------------
بقیه‌ی تست‌های این پروژه عمداً به Kivy وابسته نیستند تا سریع اجرا شوند.
نتیجه‌ی جانبی‌اش این بود که یک اشتباه ساده در لایه‌ی UI - مثل import
گمشده، نام اشتباه یک کلاس، یا ارجاع به صفتی که وجود ندارد - در هیچ
تستی دیده نمی‌شد و فقط بعد از یک بیلد یک‌ساعته و نصب APK روی گوشی
معلوم می‌شد (آن هم به‌صورت کرش هنگام باز شدن برنامه).

این تست همه‌ی ماژول‌های UI را واقعاً import می‌کند تا این دسته خطاها
همان اول پیدا شوند.

محدودیت صادقانه‌ی این تست
--------------------------------------------------------------------------
این تست فقط *import* را بررسی می‌کند، نه ساخت و رندر ویجت‌ها. ساخت
ویجت در محیط بدون OpenGL ممکن نیست، چون Kivy در ``dp()`` و در سازنده‌ی
هر Widget تابع ``EventLoop.ensure_window()`` را صدا می‌زند و آن هم بدون
درایور گرافیکی مستقیماً ``sys.exit(1)`` می‌کند (تأییدشده:
kivy/base.py خط ۱۳۹). بنابراین درستی *ظاهر* و چیدمان با این تست تأیید
نمی‌شود و همچنان نیاز به اجرای واقعی روی دستگاه دارد.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import kivy  # noqa: F401
    HAS_KIVY = True
except Exception:
    HAS_KIVY = False


UI_MODULES = [
    'src.design_system',
    'src.design_system.tokens',
    'src.design_system.typography',
    'src.design_system.animations',
    'src.design_system.base',
    'src.design_system.components.buttons',
    'src.design_system.components.cards',
    'src.design_system.components.chat',
    'src.design_system.components.controls',
    'src.design_system.components.dialogs',
    'src.design_system.components.feedback',
    'src.design_system.components.inputs',
    'src.design_system.components.loaders',
    'src.design_system.components.navigation',
    'src.design_system.components.voice',
    'src.ui',
    'src.screens.base',
    'src.screens.auth',
    'src.screens.home',
    'src.screens.chat',
    'src.screens.voice',
    'src.screens.settings_hub',
    'src.screens.settings_detail',
    'src.screens.settings_sections',
    'src.markdown_render',
]


def _stub_window():
    """یک Window جعلی می‌گذارد تا import در محیط بدون گرافیک کار کند."""
    os.environ.setdefault('KIVY_NO_ARGS', '1')
    import kivy.core.window as kcw

    class _FakeWindow:
        size = (400, 750)
        width, height = 400, 750
        clearcolor = (0, 0, 0, 1)
        softinput_mode = ''
        keyboard_height = 0

        def bind(self, **kwargs):
            pass

        def add_widget(self, *args, **kwargs):
            pass

        def remove_widget(self, *args, **kwargs):
            pass

    kcw.Window = _FakeWindow()
    sys.modules['kivy.core.window'].Window = kcw.Window


@unittest.skipUnless(HAS_KIVY, 'Kivy نصب نیست - این تست رد می‌شود')
class TestUiModulesImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _stub_window()

    def test_all_ui_modules_import(self):
        failures = []
        for name in UI_MODULES:
            try:
                __import__(name)
            except Exception as exc:
                failures.append(f'{name}: {type(exc).__name__}: {exc}')
        self.assertEqual(
            [], failures,
            'این ماژول‌های رابط کاربری import نشدند:\n' + '\n'.join(failures))

    def test_main_module_imports(self):
        """نقطه‌ی ورود برنامه باید واقعاً import شود.

        این تست یک باگ واقعی را گرفت: ``main.py`` نام
        ``SETTINGS_SECTIONS`` را از ``src.screens.settings_sections``
        import می‌کرد در حالی که آن نام در ``src.screens.settings_hub``
        تعریف شده است. نتیجه ``ImportError`` هنگام اجرا بود، یعنی
        برنامه روی گوشی **قبل از نمایش هر چیزی** کرش می‌کرد - و هیچ
        تستی هم آن را نمی‌دید چون هیچ تستی main را import نمی‌کرد.
        """
        import importlib
        module = importlib.import_module('main')
        self.assertTrue(hasattr(module, 'VinaApp'))

    def test_settings_sections_all_builders_exist(self):
        """هر بخش تنظیمات باید یک تابع سازنده‌ی واقعی داشته باشد.

        اگر کلیدی در SETTINGS_SECTIONS باشد ولی سازنده‌اش نباشد، کاربر
        صفحه‌ی «این بخش هنوز آماده نیست» می‌بیند - بی‌سروصدا.
        """
        from src.screens import settings_hub, settings_sections as ss
        missing = [
            section['key'] for section in settings_hub.SETTINGS_SECTIONS
            if section['key'] not in ss.SECTION_BUILDERS
        ]
        self.assertEqual([], missing,
                         f'بخش‌های تنظیمات بدون سازنده: {missing}')

    def test_model_section_has_import_and_rescan(self):
        """دکمه‌های افزودن مدل باید واقعاً وجود داشته باشند."""
        from src.screens import settings_sections as ss
        self.assertTrue(hasattr(ss, '_pick_model_file'))
        self.assertTrue(hasattr(ss, '_rescan_models'))

    def test_theme_engine_switches_all_themes(self):
        """تعویض زنده‌ی تم نباید خطا بدهد و باید رنگ را واقعاً عوض کند."""
        from src.design_system import theme, THEMES

        self.assertGreaterEqual(len(THEMES), 8,
                                'تم‌های خواسته‌شده: emerald/blue/purple/'
                                'orange/red/cyan/amoled/light')

        seen = set()
        for key in THEMES:
            theme.apply_palette(key)
            seen.add(tuple(theme.bg_primary) + tuple(theme.accent))
        # تم‌های مختلف نباید همگی رنگ یکسان بدهند
        self.assertGreater(len(seen), 1,
                           'تعویض تم هیچ تغییری در رنگ‌ها ایجاد نکرد')

    def test_custom_accent_applies(self):
        """رنگ اکسنت سفارشی باید بلافاصله اعمال شود (بدون راه‌اندازی مجدد)."""
        from src.design_system import theme
        theme.apply_palette('emerald')
        self.assertTrue(theme.set_custom_accent('#1ABC9C'))
        self.assertAlmostEqual(theme.accent[0], 0x1A / 255.0, places=2)
        self.assertAlmostEqual(theme.accent[1], 0xBC / 255.0, places=2)
        # حباب چت کاربر هم باید با اکسنت هماهنگ شود
        self.assertEqual(tuple(theme.bubble_user), tuple(theme.accent))

    def test_default_theme_is_black_emerald(self):
        """تم پیش‌فرض خواسته‌شده: مشکی + سبز زمردی."""
        from src.design_system import theme
        theme.apply_palette('emerald')
        r, g, b = theme.bg_primary[:3]
        self.assertLess(max(r, g, b), 0.2,
                        f'پس‌زمینه‌ی تم پیش‌فرض باید تیره باشد، ولی {(r,g,b)} است')
        ar, ag, ab = theme.accent[:3]
        self.assertGreater(ag, ar, 'مؤلفه‌ی سبز اکسنت باید غالب باشد')
        self.assertGreater(ag, ab, 'مؤلفه‌ی سبز اکسنت باید غالب باشد')


if __name__ == '__main__':
    unittest.main(verbosity=2)
