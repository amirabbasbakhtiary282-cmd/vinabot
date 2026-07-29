# -*- coding: utf-8 -*-
"""
ضبط صدای خام از میکروفون (PCM 16-bit mono @ 16kHz)

چرا مستقیم AudioRecord اندروید و نه plyer؟
- plyer.audio روی اندروید فایل ضبط می‌کند (MediaRecorder) و جریان زنده نمی‌دهد؛
  برای VAD و تشخیص گفتار زنده به بایت‌های خام و لحظه‌ای نیاز داریم.
- android.media.AudioRecord دقیقاً همین را می‌دهد و از طریق pyjnius قابل
  استفاده است.

روی دسکتاپ (توسعه) اگر sounddevice نصب باشد از آن استفاده می‌شود، وگرنه
ضبط‌کننده به‌صورت غیرفعال گزارش می‌شود تا برنامه کرش نکند.
"""

import threading

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)   # 480 نمونه
FRAME_BYTES = FRAME_SAMPLES * 2                       # 16-bit = 2 بایت


def pcm16_to_float(pcm_bytes):
    """بایت‌های PCM 16-bit little-endian را به لیست float در بازه‌ی -1..1 تبدیل می‌کند."""
    import array
    arr = array.array('h')
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if usable <= 0:
        return []
    arr.frombytes(pcm_bytes[:usable])
    # روی معماری‌های big-endian باید بایت‌ها جابه‌جا شوند
    import sys
    if sys.byteorder == 'big':
        arr.byteswap()
    return [s / 32768.0 for s in arr]


class BaseRecorder:
    """رابط مشترک: start(on_frame) / stop()"""

    def is_available(self):
        return False

    def start(self, on_frame, on_error=None):
        raise NotImplementedError

    def stop(self):
        pass

    @property
    def is_recording(self):
        return False


class AndroidRecorder(BaseRecorder):
    """ضبط زنده از میکروفون با android.media.AudioRecord."""

    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._recording = False
        self._record = None

    def is_available(self):
        try:
            from src.android_bridge import is_android
            if not is_android():
                return False
            import importlib
            return importlib.util.find_spec('jnius') is not None
        except Exception:
            return False

    @property
    def is_recording(self):
        return self._recording

    def start(self, on_frame, on_error=None):
        if self._recording:
            return True
        if not self.is_available():
            if on_error:
                on_error('میکروفون در دسترس نیست')
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(on_frame, on_error), daemon=True,
            name='VinaAudioRecorder')
        self._thread.start()
        return True

    def _loop(self, on_frame, on_error):
        try:
            from jnius import autoclass
            AudioRecord = autoclass('android.media.AudioRecord')
            AudioFormat = autoclass('android.media.AudioFormat')
            MediaRecorder = autoclass('android.media.MediaRecorder$AudioSource')

            min_buf = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            if min_buf <= 0:
                min_buf = FRAME_BYTES * 10
            buf_size = max(min_buf, FRAME_BYTES * 10)

            # VOICE_RECOGNITION منبع بهتری از MIC است: اندروید خودش کاهش
            # نویز و حذف اکو را روی آن اعمال می‌کند، که هم دقت STT را بالا
            # می‌برد و هم جلوی این را می‌گیرد که صدای خود TTS دوباره وارد
            # میکروفون شود و باعث barge-in کاذب گردد.
            self._record = AudioRecord(
                MediaRecorder.VOICE_RECOGNITION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                buf_size,
            )

            if self._record.getState() != AudioRecord.STATE_INITIALIZED:
                if on_error:
                    on_error('میکروفون آماده نشد (مجوز ضبط صدا داده شده؟)')
                return

            self._record.startRecording()
            self._recording = True

            # بافر بایتی مشترک برای خواندن فریم‌ها
            buf = bytearray(FRAME_BYTES)
            while not self._stop_event.is_set():
                read = self._record.read(buf, 0, FRAME_BYTES)
                if read is None or read <= 0:
                    continue
                try:
                    on_frame(bytes(buf[:read]))
                except Exception as exc:  # noqa: BLE001
                    print(f'خطا در پردازش فریم صوتی: {exc}')
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(f'خطا در ضبط صدا: {exc}')
        finally:
            self._recording = False
            try:
                if self._record is not None:
                    self._record.stop()
                    self._record.release()
            except Exception:
                pass
            self._record = None

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._recording = False


class DesktopRecorder(BaseRecorder):
    """ضبط روی دسکتاپ با sounddevice (فقط برای توسعه و تست)."""

    def __init__(self):
        self._stream = None
        self._recording = False

    def is_available(self):
        try:
            import importlib
            return importlib.util.find_spec('sounddevice') is not None
        except Exception:
            return False

    @property
    def is_recording(self):
        return self._recording

    def start(self, on_frame, on_error=None):
        if not self.is_available():
            if on_error:
                on_error('sounddevice نصب نیست (فقط برای تست دسکتاپ لازم است)')
            return False
        try:
            import sounddevice as sd

            def _callback(indata, frames, time_info, status):  # noqa: ARG001
                try:
                    on_frame(bytes(indata))
                except Exception as exc:  # noqa: BLE001
                    print(f'خطا در پردازش فریم صوتی: {exc}')

            self._stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE, blocksize=FRAME_SAMPLES,
                dtype='int16', channels=1, callback=_callback)
            self._stream.start()
            self._recording = True
            return True
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(f'خطا در ضبط صدا: {exc}')
            return False

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._recording = False


def create_recorder():
    """ضبط‌کننده‌ی مناسب پلتفرم را برمی‌گرداند."""
    android = AndroidRecorder()
    if android.is_available():
        return android
    return DesktopRecorder()
