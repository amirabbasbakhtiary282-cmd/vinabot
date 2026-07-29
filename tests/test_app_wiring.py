# -*- coding: utf-8 -*-
"""
تست اتصالات برنامه بدون اجرای واقعی رابط کاربری.

هدف: گرفتن خطاهای «متد وجود ندارد» / «امضا نمی‌خواند» که تست‌های واحد
منطقی نمی‌گیرند و فقط روی گوشی معلوم می‌شوند.
"""

import ast
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _parse(path):
    with open(path, encoding='utf-8') as f:
        return ast.parse(f.read(), filename=path)


def _class_methods(tree, class_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return set()


def _class_attrs(tree, class_name):
    """هم پراپرتی‌های سطح کلاس و هم ``self.x = ...`` داخل متدها."""
    out = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == class_name):
            continue
        for n in node.body:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        out.add(t.id)
        # نسبت‌دهی‌های self.x داخل متدها (مثلاً در build())
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if (isinstance(t, ast.Attribute)
                            and isinstance(t.value, ast.Name)
                            and t.value.id == 'self'):
                        out.add(t.attr)
    return out


class TestVinaAppSurface(unittest.TestCase):
    """متدها/پراپرتی‌هایی که UI صدا می‌زند باید واقعاً در VinaApp باشند."""

    @classmethod
    def setUpClass(cls):
        cls.tree = _parse(os.path.join(ROOT, 'main.py'))
        cls.methods = _class_methods(cls.tree, 'VinaApp')
        cls.attrs = _class_attrs(cls.tree, 'VinaApp')

    def test_voice_methods_exist(self):
        for name in ('start_voice_conversation', 'stop_voice_conversation',
                     'ensure_microphone_permission', 'set_offline_stt',
                     'download_stt_model', '_llm_stream_for_voice',
                     '_on_voice_state', '_add_user_message', '_toast'):
            self.assertIn(name, self.methods, f'VinaApp.{name} تعریف نشده')

    def test_voice_properties_exist(self):
        for name in ('prefer_offline_stt', 'barge_in_enabled',
                     'wake_word_enabled', 'voice_state', 'live_transcript'):
            self.assertIn(name, self.attrs, f'VinaApp.{name} تعریف نشده')

    def test_backward_compatible_methods_kept(self):
        for name in ('send_message', 'start_listening', 'toggle_voice',
                     '_get_response', '_add_bot_message'):
            self.assertIn(name, self.methods, f'متد قدیمی {name} حذف شده!')


class TestSettingsCallsExist(unittest.TestCase):
    """هر app.X(...) در صفحه‌ی تنظیمات باید در VinaApp وجود داشته باشد."""

    def test_settings_sections_call_real_methods(self):
        main_tree = _parse(os.path.join(ROOT, 'main.py'))
        app_names = (_class_methods(main_tree, 'VinaApp') |
                     _class_attrs(main_tree, 'VinaApp'))

        path = os.path.join(ROOT, 'src', 'screens', 'settings_sections.py')
        tree = _parse(path)

        missing = []
        for node in ast.walk(tree):
            # الگوی app.<name>  (چه فراخوانی، چه خواندن مقدار)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'app' and node.attr not in app_names:
                    missing.append(node.attr)

        # این‌ها از کلاس پایه‌ی Kivy App می‌آیند
        known_base = {'stop', 'root', 'title', 'get_running_app',
                      'user_data_dir', 'config'}
        real_missing = sorted(set(missing) - known_base)
        self.assertEqual(real_missing, [],
                         f'صفحه‌ی تنظیمات به این‌ها اشاره می‌کند ولی وجود ندارند: {real_missing}')


class TestVoiceScreenWiring(unittest.TestCase):

    def test_voice_screen_uses_conversation_api(self):
        path = os.path.join(ROOT, 'src', 'screens', 'voice.py')
        with open(path, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('start_voice_conversation', src)
        self.assertIn('stop_voice_conversation', src)
        self.assertIn('ensure_microphone_permission', src)


class TestVinaVoiceApi(unittest.TestCase):
    """API کلاس VinaVoice باید هم جدید باشد هم سازگار با کد قدیمی."""

    def test_methods(self):
        from src.voice import VinaVoice
        for name in ('speak', 'speak_queued', 'listen', 'stop_speaking',
                     'stop_listening', 'shutdown', 'create_conversation',
                     'stop_conversation', 'stt_engine_info',
                     'listen_for_wake_word', 'get_audio_levels',
                     'set_speech_rate', 'set_pitch'):
            self.assertTrue(hasattr(VinaVoice, name), f'VinaVoice.{name} نیست')

    def test_bridge_has_new_methods(self):
        from src.android_bridge import AndroidBridge
        for name in ('speak', 'stop_speaking', 'listen_once', 'stop_listening',
                     'is_speaking', 'set_speech_rate', 'set_pitch',
                     'request_permissions', 'has_permission'):
            self.assertTrue(hasattr(AndroidBridge, name),
                            f'AndroidBridge.{name} نیست')

    def test_instantiates_off_android(self):
        """ساخت شیء روی دسکتاپ نباید کرش کند (مسیر توسعه)."""
        from src.voice import VinaVoice
        v = VinaVoice()
        self.assertFalse(v.is_android)
        info = v.stt_engine_info()
        self.assertIn('label', info)
        # speak روی دسکتاپ باید امن باشد (فقط چاپ کند)
        self.assertFalse(v.speak('تست'))
        self.assertIsNone(v.conversation)


class TestBuildConfig(unittest.TestCase):

    def test_permissions_include_microphone_and_foreground(self):
        with open(os.path.join(ROOT, 'buildozer.spec'), encoding='utf-8') as f:
            spec = f.read()
        for perm in ('RECORD_AUDIO', 'FOREGROUND_SERVICE'):
            self.assertIn(perm, spec)

    def test_vosk_recipe_registered(self):
        with open(os.path.join(ROOT, 'buildozer.spec'), encoding='utf-8') as f:
            spec = f.read()
        req_line = [l for l in spec.splitlines() if l.startswith('requirements')][0]
        self.assertIn('vosk', req_line)
        self.assertTrue(os.path.exists(
            os.path.join(ROOT, 'p4a-recipes', 'vosk', '__init__.py')))

    def test_recipes_are_valid_python(self):
        for name in ('llamacpp', 'vinallm', 'vosk'):
            path = os.path.join(ROOT, 'p4a-recipes', name, '__init__.py')
            with open(path, encoding='utf-8') as f:
                ast.parse(f.read(), filename=path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
