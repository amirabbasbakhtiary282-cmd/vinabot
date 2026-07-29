# -*- coding: utf-8 -*-
"""تست انتخاب موتور STT و دانلود امن مدل آفلاین"""

import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import stt_engine  # noqa: E402
from src.model_downloader import VoskModelDownloader  # noqa: E402
from src.stt_engine import VOSK_MODELS, VoskSTT, create_stt  # noqa: E402


class TestModelDiscovery(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = stt_engine.get_vosk_models_dir
        stt_engine.get_vosk_models_dir = lambda: self.tmp

    def tearDown(self):
        stt_engine.get_vosk_models_dir = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_model_is_not_found(self):
        self.assertIsNone(stt_engine.find_vosk_model('fa'))

    def test_incomplete_model_dir_is_rejected(self):
        """پوشه‌ی خالی نباید به‌عنوان مدل معتبر شناخته شود."""
        os.makedirs(os.path.join(self.tmp, VOSK_MODELS['fa']['name']))
        self.assertIsNone(stt_engine.find_vosk_model('fa'))

    def test_valid_model_dir_is_found(self):
        root = os.path.join(self.tmp, VOSK_MODELS['fa']['name'])
        os.makedirs(os.path.join(root, 'am'))
        self.assertEqual(stt_engine.find_vosk_model('fa'), root)

    def test_unknown_language(self):
        self.assertIsNone(stt_engine.find_vosk_model('xx'))


class TestEngineSelection(unittest.TestCase):
    """موتور باید با توجه به ترجیح کاربر و در دسترس بودن انتخاب شود."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = stt_engine.get_vosk_models_dir
        stt_engine.get_vosk_models_dir = lambda: self.tmp

    def tearDown(self):
        stt_engine.get_vosk_models_dir = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_offline_unavailable_falls_back_with_note(self):
        """اگر مدل آفلاین نباشد، باید به موتور دیگر برگردد و به کاربر بگوید."""
        engine, note = create_stt(prefer_offline=True, lang='fa')
        self.assertIsNotNone(note, 'کاربر باید از تغییر موتور مطلع شود')
        self.assertFalse(engine.is_available())

    def test_vosk_reports_missing_model_clearly(self):
        e = VoskSTT('fa')
        self.assertFalse(e.is_available())
        self.assertIn('دانلود', e.load_error)

    def test_vosk_start_fails_gracefully(self):
        """نبود مدل نباید کرش کند - باید خطای قابل نمایش بدهد."""
        e = VoskSTT('fa')
        errors = []
        self.assertFalse(e.start(on_error=errors.append))
        self.assertEqual(len(errors), 1)

    def test_feed_without_start_is_safe(self):
        e = VoskSTT('fa')
        self.assertIsNone(e.feed(b'\x00\x01' * 100))
        self.assertEqual(e.final_result(), '')
        e.stop()
        e.close()


class TestSafeExtract(unittest.TestCase):
    """استخراج zip باید در برابر Zip Slip ایمن باشد."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = stt_engine.get_vosk_models_dir
        stt_engine.get_vosk_models_dir = lambda: self.tmp
        self.dl = VoskModelDownloader()
        self.dl.models_dir = self.tmp

    def tearDown(self):
        stt_engine.get_vosk_models_dir = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rejects_path_traversal(self):
        zpath = os.path.join(self.tmp, 'evil.zip')
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('../../evil.txt', 'pwned')
        dest = os.path.join(self.tmp, 'out')
        os.makedirs(dest)
        with self.assertRaises(ValueError):
            self.dl._safe_extract(zpath, dest, 'fa')
        self.assertFalse(os.path.exists(os.path.join(self.tmp, '..', 'evil.txt')))

    def test_extracts_normal_zip(self):
        zpath = os.path.join(self.tmp, 'ok.zip')
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('model/am/final.mdl', 'data')
        dest = os.path.join(self.tmp, 'out2')
        os.makedirs(dest)
        self.dl._safe_extract(zpath, dest, 'fa')
        self.assertTrue(os.path.exists(os.path.join(dest, 'model', 'am', 'final.mdl')))

    def test_list_available_reports_not_installed(self):
        items = self.dl.list_available()
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertFalse(item['installed'])
            self.assertGreater(item['size_mb'], 0)

    def test_delete_missing_model_is_safe(self):
        self.assertFalse(self.dl.delete('fa'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
