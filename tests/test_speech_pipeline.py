# -*- coding: utf-8 -*-
"""تست‌های منطق خط لوله‌ی صوتی (بدون نیاز به اندروید/میکروفون)"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.speech_pipeline import (  # noqa: E402
    EnergyVAD, SentenceChunker, WakeWordMatcher, normalize_fa,
)


class TestSentenceChunker(unittest.TestCase):

    def test_splits_on_persian_question_mark(self):
        c = SentenceChunker()
        out = c.feed('حال شما چطور است؟ من خوبم.')
        self.assertEqual(out, ['حال شما چطور است؟'])
        self.assertEqual(c.flush(), ['من خوبم.'])

    def test_streaming_token_by_token_matches_whole(self):
        """مهم: نتیجه‌ی تکه‌تکه دادن باید با یک‌جا دادن یکسان باشد."""
        text = 'سلام دوست من. امروز هوا عالی است! چه کاری از من برمی‌آید؟'
        whole = SentenceChunker()
        got_whole = whole.feed(text) + whole.flush()

        piecewise = SentenceChunker()
        got_pieces = []
        for ch in text:  # بدترین حالت: کاراکتر به کاراکتر
            got_pieces += piecewise.feed(ch)
        got_pieces += piecewise.flush()

        self.assertEqual(got_whole, got_pieces)
        self.assertEqual(''.join(got_whole).replace(' ', ''),
                         text.replace(' ', ''))

    def test_no_split_inside_decimal_number(self):
        c = SentenceChunker()
        out = c.feed('The value is 3.14159 exactly. Done.')
        self.assertEqual(out, ['The value is 3.14159 exactly.'])

    def test_no_split_after_abbreviation(self):
        c = SentenceChunker()
        out = c.feed('Please ask Dr. Smith about it. Thanks.')
        self.assertEqual(out, ['Please ask Dr. Smith about it.'])

    def test_short_fragment_merges_forward(self):
        """«بله.» تنها نباید به‌عنوان یک جمله‌ی جدا به TTS برود."""
        c = SentenceChunker(min_chars=12)
        out = c.feed('بله. البته که می‌توانم کمک کنم.')
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith('بله.'))

    def test_long_text_without_punctuation_still_breaks(self):
        c = SentenceChunker(max_chars=60)
        long_text = 'کلمه ' * 40
        out = c.feed(long_text)
        self.assertGreater(len(out), 1)
        for s in out:
            self.assertLessEqual(len(s), 61)

    def test_nothing_lost_across_random_chunking(self):
        text = ('وینا یک دستیار هوشمند است. او می‌تواند صحبت کند! '
                'آیا آماده‌ای؟ بیا شروع کنیم.')
        rng = random.Random(1234)
        for _ in range(50):
            c = SentenceChunker()
            i, collected = 0, []
            while i < len(text):
                n = rng.randint(1, 7)
                collected += c.feed(text[i:i + n])
                i += n
            collected += c.flush()
            joined = ' '.join(collected)
            self.assertEqual(''.join(joined.split()), ''.join(text.split()))

    def test_flush_empty_is_safe(self):
        c = SentenceChunker()
        self.assertEqual(c.feed(''), [])
        self.assertEqual(c.flush(), [])


class TestEnergyVAD(unittest.TestCase):

    @staticmethod
    def _frame(vad, amp, seed=0):
        rng = random.Random(seed)
        return [rng.uniform(-amp, amp) for _ in range(vad.frame_size)]

    def test_silence_produces_no_events(self):
        vad = EnergyVAD()
        for i in range(50):
            self.assertIsNone(vad.process_frame(self._frame(vad, 0.001, i)))
        self.assertFalse(vad.is_speaking)

    def test_detects_speech_start_and_end(self):
        vad = EnergyVAD(hangover_ms=150, frame_ms=30)
        for i in range(30):  # کالیبره شدن روی نویز کم
            vad.process_frame(self._frame(vad, 0.002, i))

        events = []
        for i in range(10):  # گفتار بلند
            e = vad.process_frame(self._frame(vad, 0.5, 100 + i))
            if e:
                events.append(e)
        self.assertIn('speech_start', events)
        self.assertTrue(vad.is_speaking)

        events = []
        for i in range(20):  # برگشت به سکوت
            e = vad.process_frame(self._frame(vad, 0.001, 200 + i))
            if e:
                events.append(e)
        self.assertIn('speech_end', events)
        self.assertFalse(vad.is_speaking)

    def test_ignores_single_frame_click(self):
        """یک ضربه‌ی کوتاه (در بستن) نباید گفتار حساب شود."""
        vad = EnergyVAD(start_frames=3)
        for i in range(30):
            vad.process_frame(self._frame(vad, 0.002, i))
        e = vad.process_frame(self._frame(vad, 0.9, 999))
        self.assertIsNone(e)
        self.assertFalse(vad.is_speaking)

    def test_adapts_to_loud_room(self):
        """در محیط پرنویز، آستانه باید بالا برود تا نویز گفتار حساب نشود."""
        vad = EnergyVAD()
        for i in range(200):
            vad.process_frame(self._frame(vad, 0.05, i))
        self.assertGreater(vad.threshold, vad.min_threshold)
        self.assertFalse(vad.is_speaking)

    def test_rms_of_known_signal(self):
        vad = EnergyVAD()
        # موج سینوسی با دامنه 1 -> RMS = 1/sqrt(2)
        sig = [math.sin(2 * math.pi * i / 100) for i in range(1000)]
        self.assertAlmostEqual(vad.rms(sig), 1 / math.sqrt(2), places=2)
        self.assertEqual(vad.rms([]), 0.0)

    def test_reset_clears_state(self):
        vad = EnergyVAD()
        for i in range(30):
            vad.process_frame(self._frame(vad, 0.002, i))
        for i in range(10):
            vad.process_frame(self._frame(vad, 0.6, 100 + i))
        self.assertTrue(vad.is_speaking)
        vad.reset()
        self.assertFalse(vad.is_speaking)


class TestWakeWord(unittest.TestCase):

    def test_normalize_arabic_yeh_and_kaf(self):
        # ي عربی و ی فارسی باید یکسان شوند
        self.assertEqual(normalize_fa('وينا'), normalize_fa('وینا'))
        self.assertEqual(normalize_fa('كتاب'), normalize_fa('کتاب'))

    def test_bare_wake_word_returns_empty_command(self):
        m = WakeWordMatcher()
        self.assertEqual(m.match('هی وینا'), '')
        self.assertEqual(m.match('سلام وینا'), '')

    def test_wake_word_with_command(self):
        m = WakeWordMatcher()
        self.assertEqual(m.match('هی وینا ساعت چنده'), 'ساعت چنده')

    def test_longest_phrase_wins(self):
        """«سلام وینا» نباید فقط «وینا» تطبیق بخورد و «سلام» را دستور بداند."""
        m = WakeWordMatcher()
        self.assertEqual(m.match('سلام وینا چراغ قوه رو روشن کن'),
                         'چراغ قوه رو روشن کن')

    def test_no_wake_word_returns_none(self):
        m = WakeWordMatcher()
        self.assertIsNone(m.match('امروز هوا خوب است'))
        self.assertIsNone(m.match(''))
        self.assertIsNone(m.match(None))

    def test_english_wake_word(self):
        m = WakeWordMatcher()
        self.assertEqual(m.match('Hey Vina what time is it'),
                         'what time is it')

    def test_wake_word_mid_sentence(self):
        m = WakeWordMatcher()
        self.assertEqual(m.match('خب وینا چراغ را روشن کن'), 'چراغ را روشن کن')

    def test_custom_phrases(self):
        m = WakeWordMatcher(['رفیق'])
        self.assertEqual(m.match('رفیق سلام'), 'سلام')
        self.assertIsNone(m.match('هی وینا'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
