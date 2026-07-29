# -*- coding: utf-8 -*-
"""
تست تولید جریانی در مغز وینا و لایه‌ی ctypes موتور.

موتور native واقعی اینجا در دسترس نیست، پس با یک جایگزین (fake) قرارداد
بین brain -> engine -> callback راستی‌آزمایی می‌شود.
"""

import ctypes
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brain import VinaBrain  # noqa: E402
from src.llm_engine import LlmEngine  # noqa: E402


class FakeEngine:
    """موتور جعلی که پاسخ ثابتی را توکن‌به‌توکن بیرون می‌دهد."""

    def __init__(self, text='سلام. من وینا هستم. چطور کمک کنم؟'):
        self.text = text
        self.n_ctx = 2048
        self._handle = object()
        self.last_on_token = None
        self.stopped_early = False

    def count_tokens(self, text):
        return max(1, len(text) // 4)

    def generate(self, prompt, on_token=None, **kwargs):
        self.last_on_token = on_token
        out = []
        for i in range(0, len(self.text), 4):
            piece = self.text[i:i + 4]
            if on_token is not None and on_token(piece) is False:
                self.stopped_early = True
                break
            out.append(piece)
        return ''.join(out)


class FakeMemory:
    def get_context(self):
        return ''

    def get_user_name(self):
        return 'کاربر'

    def get_personality(self):
        return {}

    def save_conversation(self, *a):
        pass

    def analyze_and_store_preferences(self, *a):
        pass


class TestBrainStreaming(unittest.TestCase):

    def setUp(self):
        self.brain = VinaBrain(FakeMemory())
        self.engine = FakeEngine()
        self.brain.engine = self.engine
        self.brain.model_loaded = True

    def test_tokens_are_streamed_in_order(self):
        pieces = []
        result = self.brain.generate_response('سلام', on_token=lambda p: pieces.append(p) or True)
        self.assertGreater(len(pieces), 1, 'باید بیش از یک قطعه ارسال شود')
        self.assertEqual(''.join(pieces), self.engine.text)
        self.assertEqual(result, self.engine.text)

    def test_get_response_stream_alias(self):
        pieces = []
        self.brain.get_response_stream('سلام', on_token=lambda p: pieces.append(p) or True)
        self.assertEqual(''.join(pieces), self.engine.text)

    def test_callback_false_stops_generation(self):
        """بازگرداندن False باید تولید را قطع کند (پایه‌ی barge-in)."""
        pieces = []

        def stop_after_two(piece):
            pieces.append(piece)
            return len(pieces) < 2

        self.brain.generate_response('سلام', on_token=stop_after_two)
        self.assertTrue(self.engine.stopped_early)
        self.assertEqual(len(pieces), 2)

    def test_non_streaming_still_works(self):
        """سازگاری با کد قبلی: بدون on_token باید متن کامل برگردد."""
        result = self.brain.generate_response('سلام')
        self.assertEqual(result, self.engine.text)

    def test_fallback_streams_when_model_missing(self):
        """حتی وقتی مدل بارگذاری نشده، مسیر صوتی نباید ساکت بماند."""
        self.brain.model_loaded = False
        pieces = []
        result = self.brain.generate_response('سلام', on_token=lambda p: pieces.append(p) or True)
        self.assertTrue(pieces, 'پاسخ جایگزین هم باید به callback برود')
        self.assertEqual(''.join(pieces), result)
        self.assertTrue(result.strip())


class TestEngineCtypesContract(unittest.TestCase):
    """امضای ctypes باید با امضای C در vina_llm.cpp بخواند."""

    def test_callback_type_signature(self):
        engine = LlmEngine()

        class FakeLib:
            def __getattr__(self, name):
                fn = type('F', (), {})()
                fn.restype = None
                fn.argtypes = None
                return fn

        engine._lib = FakeLib()
        engine._setup_signatures()
        cb_type = engine._TokenCallback
        self.assertIsNotNone(cb_type)
        # int (*)(const char*, void*)
        self.assertEqual(cb_type._restype_, ctypes.c_int)
        self.assertEqual(list(cb_type._argtypes_),
                         [ctypes.c_char_p, ctypes.c_void_p])

    def test_generate_without_model_raises_clear_error(self):
        engine = LlmEngine()
        with self.assertRaises(Exception) as ctx:
            engine.generate('سلام')
        self.assertIn('مدل', str(ctx.exception))


class TestCppSourceHasStreamingSymbol(unittest.TestCase):
    """اطمینان از اینکه تابع جریانی واقعاً در سورس C++ صادر شده است."""

    def test_symbol_exported(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'p4a-recipes', 'vinallm', 'src', 'vina_llm.cpp')
        with open(path, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('VINA_API int vina_llm_generate_stream', src)
        self.assertIn('typedef int (*vina_token_cb)', src)
        # نسخه‌ی قدیمی باید حفظ شده باشد (سازگاری به عقب)
        self.assertIn('VINA_API int vina_llm_generate(', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
