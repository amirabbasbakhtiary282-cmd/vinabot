# -*- coding: utf-8 -*-
"""
تست کامل خط لوله‌ی گفتگوی صوتی با قطعات جعلی (fake).

این تست‌ها *منطق* کامل «کاربر حرف می‌زند -> STT -> LLM -> TTS -> پخش» و
«قطع کردن وسط صحبت» را بدون نیاز به اندروید، میکروفون یا مدل واقعی
راستی‌آزمایی می‌کنند.
"""

import os
import random
import struct
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio_recorder import FRAME_SAMPLES, pcm16_to_float  # noqa: E402
from src.voice_conversation import (  # noqa: E402
    STATE_IDLE, STATE_LISTENING, STATE_SPEAKING, VoiceConversation,
)


def make_pcm(amplitude, samples=FRAME_SAMPLES, seed=0):
    """یک فریم PCM 16-bit با دامنه‌ی مشخص می‌سازد."""
    rng = random.Random(seed)
    vals = [int(rng.uniform(-amplitude, amplitude) * 32767) for _ in range(samples)]
    return struct.pack('<%dh' % samples, *vals)


class FakeSTT:
    """موتور STT جعلی: هر چه به آن بدهیم، متن از پیش تعیین‌شده برمی‌گرداند."""

    def __init__(self, transcript='سلام وینا حالت چطوره'):
        self.transcript = transcript
        self.started = 0
        self.stopped = 0
        self.fed_bytes = 0
        self.on_partial = None

    def start(self, on_partial=None, on_final=None, on_error=None):
        self.started += 1
        self.on_partial = on_partial
        return True

    def feed(self, pcm):
        self.fed_bytes += len(pcm)
        return None

    def final_result(self):
        return self.transcript

    def stop(self):
        self.stopped += 1


class FakeRecorder:
    """ضبط‌کننده‌ی جعلی: فریم‌ها را دستی به آن تزریق می‌کنیم."""

    def __init__(self):
        self.on_frame = None
        self.started = False

    def start(self, on_frame, on_error=None):
        self.on_frame = on_frame
        self.started = True
        return True

    def stop(self):
        self.started = False

    def push(self, pcm):
        if self.on_frame:
            self.on_frame(pcm)


class FakeTTS:
    """TTS جعلی که مدت گفتن را شبیه‌سازی می‌کند و قابل قطع شدن است."""

    def __init__(self, per_sentence_sec=0.0):
        self.spoken = []
        self.stop_calls = 0
        self.per_sentence_sec = per_sentence_sec
        self._stop = threading.Event()

    def speak(self, text):
        self._stop.clear()
        self.spoken.append(text)
        if self.per_sentence_sec:
            self._stop.wait(self.per_sentence_sec)

    def stop(self):
        self.stop_calls += 1
        self._stop.set()


class VoiceConversationTestBase(unittest.TestCase):

    def build(self, response='سلام! من خوبم. چطور می‌توانم کمک کنم؟',
              transcript='حالت چطوره', token_delay=0.0, tts_delay=0.0,
              **kwargs):
        self.stt = FakeSTT(transcript)
        self.recorder = FakeRecorder()
        self.tts = FakeTTS(tts_delay)
        self.response = response
        self.tokens_emitted = []
        self.generate_calls = []

        def llm(text, on_token):
            self.generate_calls.append(text)
            out = []
            # شبیه‌سازی تولید توکن‌به‌توکن مثل مدل واقعی
            for i in range(0, len(self.response), 3):
                piece = self.response[i:i + 3]
                if on_token(piece) is False:
                    break
                out.append(piece)
                self.tokens_emitted.append(piece)
                if token_delay:
                    time.sleep(token_delay)
            return ''.join(out)

        conv = VoiceConversation(
            stt=self.stt, tts_speak=self.tts.speak, tts_stop=self.tts.stop,
            llm_generate=llm, recorder=self.recorder, **kwargs)
        self.states = []
        conv.on_state_change = self.states.append
        self.errors = []
        conv.on_error = self.errors.append
        self.conv = conv
        return conv

    def speak_into(self, conv, amplitude=0.6, frames=10, seed=0):
        for i in range(frames):
            self.recorder.push(make_pcm(amplitude, seed=seed + i))

    def silence_into(self, conv, frames=40, seed=500):
        for i in range(frames):
            self.recorder.push(make_pcm(0.0005, seed=seed + i))

    def wait_for(self, predicate, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return False


class TestFullPipeline(VoiceConversationTestBase):

    def test_end_to_end_speak_stt_llm_tts(self):
        """مسیر کامل: صحبت کاربر -> متن -> پاسخ مدل -> پخش صوتی."""
        conv = self.build()
        self.assertTrue(conv.start())
        self.assertEqual(conv.state, STATE_LISTENING)
        self.assertEqual(self.stt.started, 1)

        self.silence_into(conv, frames=30)   # کالیبراسیون نویز
        self.speak_into(conv, 0.6, frames=10)
        self.assertTrue(self.stt.fed_bytes > 0, 'صدا باید به STT داده شود')
        self.silence_into(conv, frames=40)   # پایان گفتار

        self.assertTrue(self.wait_for(lambda: self.tts.spoken),
                        'وینا باید پاسخ را با صدا بگوید')
        self.assertTrue(self.wait_for(
            lambda: conv.state == STATE_LISTENING and not conv._turn_thread.is_alive()))

        self.assertEqual(self.generate_calls, ['حالت چطوره'])
        # هیچ متنی نباید گم شود
        self.assertEqual(''.join(self.tts.spoken).replace(' ', ''),
                         self.response.replace(' ', ''))
        self.assertEqual(self.errors, [])
        conv.stop()

    def test_tts_starts_before_generation_finishes(self):
        """اثبات جریانی بودن: اولین جمله باید قبل از پایان کل پاسخ گفته شود."""
        conv = self.build(
            response='جمله‌ی اول اینجاست. ' + ('کلمه ' * 60) + '.',
            token_delay=0.002)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)

        # اولین جمله باید گفته شود در حالی که تولید هنوز ادامه دارد
        self.assertTrue(self.wait_for(lambda: len(self.tts.spoken) >= 1, 3.0))
        spoke_at = len(self.tokens_emitted)
        total = len(range(0, len(self.response), 3))
        self.assertLess(spoke_at, total,
                        'گفتار باید قبل از تولید کامل شروع شود')
        conv.stop()

    def test_multiple_turns(self):
        """چند نوبت پشت سر هم باید کار کند."""
        conv = self.build(response='بله حتماً انجام شد.')
        conv.start()
        self.silence_into(conv, frames=30)

        for turn in range(3):
            self.speak_into(conv, 0.6, frames=10, seed=turn * 100)
            self.silence_into(conv, frames=40, seed=turn * 100 + 500)
            self.assertTrue(self.wait_for(
                lambda t=turn: len(self.generate_calls) == t + 1, 4.0),
                f'نوبت {turn + 1} پاسخ داده نشد')
            self.assertTrue(self.wait_for(
                lambda: conv.state == STATE_LISTENING, 4.0))

        self.assertEqual(len(self.generate_calls), 3)
        self.assertEqual(self.errors, [])
        conv.stop()

    def test_empty_transcript_does_not_call_llm(self):
        """اگر چیزی تشخیص داده نشد، نباید مدل را بی‌خود صدا بزنیم."""
        conv = self.build(transcript='   ')
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        time.sleep(0.2)
        self.assertEqual(self.generate_calls, [])
        self.assertEqual(self.tts.spoken, [])
        conv.stop()


class TestBargeIn(VoiceConversationTestBase):

    def test_user_can_interrupt_while_vina_speaks(self):
        """قطع کردن وسط صحبت: TTS باید فوراً متوقف شود و تولید لغو گردد."""
        long_response = '. '.join(['این یک جمله‌ی نسبتاً بلند است'] * 12) + '.'
        conv = self.build(response=long_response, token_delay=0.004,
                          tts_delay=0.05)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)

        self.assertTrue(self.wait_for(
            lambda: conv.state == STATE_SPEAKING, 4.0), 'وینا شروع به گفتن نکرد')
        spoken_before = len(self.tts.spoken)

        # بعد از سپری شدن بازه‌ی محافظ، کاربر بلند صحبت می‌کند
        time.sleep(0.7)
        for i in range(6):
            self.recorder.push(make_pcm(0.95, seed=900 + i))

        self.assertTrue(self.wait_for(lambda: self.tts.stop_calls > 0, 2.0),
                        'TTS باید با قطع کردن کاربر متوقف شود')
        self.assertTrue(self.wait_for(
            lambda: conv.state == STATE_LISTENING, 2.0),
            'بعد از قطع کردن باید دوباره گوش بدهد')

        # تولید باید زودتر از پایان متوقف شده باشد
        time.sleep(0.3)
        self.assertLess(len(self.tts.spoken), spoken_before + 12,
                        'تولید/گفتار باید واقعاً قطع شده باشد')
        conv.stop()

    def test_vina_own_voice_does_not_trigger_barge_in(self):
        """صدای خود وینا (در بازه‌ی محافظ) نباید باعث قطع کاذب شود."""
        conv = self.build(response='یک جمله. دو جمله. سه جمله.',
                          token_delay=0.003, tts_delay=0.02)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)

        self.assertTrue(self.wait_for(lambda: conv.state == STATE_SPEAKING, 4.0))
        # بلافاصله (داخل بازه‌ی محافظ) صدای بلند شبیه‌سازی می‌کنیم
        for i in range(5):
            self.recorder.push(make_pcm(0.9, seed=700 + i))
        time.sleep(0.1)
        self.assertEqual(self.tts.stop_calls, 0,
                         'در بازه‌ی محافظ نباید قطع شود')
        conv.stop()

    def test_barge_in_can_be_disabled(self):
        conv = self.build(response='. '.join(['جمله‌ی طولانی نمونه'] * 10) + '.',
                          token_delay=0.004, tts_delay=0.04,
                          barge_in_enabled=False)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        self.assertTrue(self.wait_for(lambda: conv.state == STATE_SPEAKING, 4.0))
        time.sleep(0.7)
        for i in range(6):
            self.recorder.push(make_pcm(0.95, seed=800 + i))
        time.sleep(0.2)
        self.assertEqual(self.tts.stop_calls, 0)
        conv.stop()


class TestWakeWord(VoiceConversationTestBase):

    def test_ignores_speech_without_wake_word(self):
        conv = self.build(transcript='امروز هوا خوب است', wake_word_enabled=True)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        time.sleep(0.2)
        self.assertEqual(self.generate_calls, [],
                         'بدون کلمه‌ی فعال‌سازی نباید پاسخ دهد')
        conv.stop()

    def test_responds_to_wake_word_with_command(self):
        conv = self.build(transcript='هی وینا ساعت چند است',
                          wake_word_enabled=True)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        self.assertTrue(self.wait_for(lambda: self.generate_calls, 3.0))
        self.assertEqual(self.generate_calls, ['ساعت چند است'])
        conv.stop()


class TestPushToTalk(VoiceConversationTestBase):

    def test_push_to_talk_produces_response(self):
        conv = self.build(transcript='چراغ قوه را روشن کن')
        conv.start()
        conv.push_to_talk_start()
        self.assertEqual(conv.state, STATE_LISTENING)
        self.speak_into(conv, 0.6, frames=5)
        conv.push_to_talk_stop()
        self.assertTrue(self.wait_for(lambda: self.generate_calls, 3.0))
        self.assertEqual(self.generate_calls, ['چراغ قوه را روشن کن'])
        conv.stop()

    def test_push_to_talk_interrupts_speech(self):
        conv = self.build(response='. '.join(['متن طولانی نمونه'] * 10) + '.',
                          token_delay=0.004, tts_delay=0.04)
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        self.assertTrue(self.wait_for(lambda: conv.state == STATE_SPEAKING, 4.0))
        conv.push_to_talk_start()
        self.assertGreater(self.tts.stop_calls, 0)
        self.assertEqual(conv.state, STATE_LISTENING)
        conv.stop()


class TestLifecycleAndErrors(VoiceConversationTestBase):

    def test_stop_releases_everything(self):
        conv = self.build()
        conv.start()
        conv.stop()
        self.assertEqual(conv.state, STATE_IDLE)
        self.assertFalse(self.recorder.started)
        self.assertFalse(conv.is_running)
        self.assertGreater(self.stt.stopped, 0)

    def test_llm_error_is_reported_and_recovers(self):
        conv = self.build()

        def failing(text, on_token):
            raise RuntimeError('مدل بارگذاری نشده')

        conv.llm_generate = failing
        conv.start()
        self.silence_into(conv, frames=30)
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        self.assertTrue(self.wait_for(lambda: self.errors, 3.0))
        self.assertIn('مدل بارگذاری نشده', self.errors[0])
        # باید بعد از خطا دوباره آماده‌ی شنیدن شود، نه اینکه گیر کند
        self.assertTrue(self.wait_for(lambda: conv.state == STATE_LISTENING, 2.0))
        conv.stop()

    def test_frames_after_stop_are_ignored(self):
        conv = self.build()
        conv.start()
        conv.stop()
        self.speak_into(conv, 0.6, frames=10)
        self.silence_into(conv, frames=40)
        time.sleep(0.1)
        self.assertEqual(self.generate_calls, [])

    def test_double_start_is_safe(self):
        conv = self.build()
        self.assertTrue(conv.start())
        self.assertTrue(conv.start())
        self.assertEqual(self.stt.started, 1)
        conv.stop()


class TestPcmConversion(unittest.TestCase):

    def test_roundtrip_amplitude(self):
        pcm = struct.pack('<4h', 0, 16384, -16384, 32767)
        vals = pcm16_to_float(pcm)
        self.assertAlmostEqual(vals[0], 0.0, places=4)
        self.assertAlmostEqual(vals[1], 0.5, places=3)
        self.assertAlmostEqual(vals[2], -0.5, places=3)
        self.assertAlmostEqual(vals[3], 1.0, places=3)

    def test_odd_length_buffer_is_safe(self):
        self.assertEqual(pcm16_to_float(b'\x01'), [])
        self.assertEqual(pcm16_to_float(b''), [])
        self.assertEqual(len(pcm16_to_float(b'\x00\x10\x00\x20\x05')), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
