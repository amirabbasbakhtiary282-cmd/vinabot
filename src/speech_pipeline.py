# -*- coding: utf-8 -*-
"""
خط لوله‌ی گفتگوی صوتی وینا (Phase A)

این ماژول منطق «خالص پایتون» گفتگوی صوتی را نگه می‌دارد تا بتوان آن را
بدون اندروید و بدون میکروفون تست کرد:

  1. ``SentenceChunker`` : متن جریانی مدل را به جمله‌های کامل می‌شکند تا
     TTS بتواند قبل از پایان کل پاسخ شروع به خواندن کند.
  2. ``EnergyVAD``       : تشخیص فعالیت صوتی بر پایه‌ی انرژی سیگنال، برای
     شروع/پایان خودکار ضبط و برای «قطع کردن وسط صحبت» (barge-in).
  3. ``WakeWordMatcher`` : تطبیق کلمه‌ی فعال‌سازی روی متن خروجی STT.

بخش‌های وابسته به سخت‌افزار (میکروفون، TTS، STT) در ماژول‌های دیگر هستند و
از طریق interface به این‌ها وصل می‌شوند.
"""

import math
import re
import unicodedata

# ---------------------------------------------------------------------------
# ۱) تکه‌کردن جمله‌ای برای TTS
# ---------------------------------------------------------------------------

# نقطه‌پایان‌های جمله در فارسی و انگلیسی. توجه: «؟» و «؛» و «।» فارسی/عربی
# با کدپوینت متفاوت از معادل انگلیسی‌شان هستند و هر دو باید پوشش داده شوند.
_SENTENCE_ENDS = '.!?\u061F\u06D4\u003B\u061B\n'  # . ! ? ؟ ۔ ; ؛ newline

# اختصاراتی که نقطه‌ی بعدشان پایان جمله نیست (وگرنه TTS وسط جمله می‌برد).
_ABBREVIATIONS = {
    'dr', 'mr', 'mrs', 'ms', 'prof', 'inc', 'ltd', 'jr', 'sr', 'st',
    'e.g', 'i.e', 'etc', 'vs', 'fig', 'no', 'approx',
}


class SentenceChunker:
    """متن جریانی را می‌گیرد و جمله‌های کامل بیرون می‌دهد.

    استفاده::

        chunker = SentenceChunker()
        for piece in stream:
            for sentence in chunker.feed(piece):
                tts.speak(sentence)
        for sentence in chunker.flush():
            tts.speak(sentence)

    پارامتر ``min_chars`` جلوی ارسال تکه‌های خیلی کوتاه («بله.») را به‌صورت
    جداگانه می‌گیرد چون باعث می‌شود گفتار بریده‌بریده به‌نظر برسد؛ آن‌ها با
    جمله‌ی بعدی ادغام می‌شوند. ``max_chars`` تضمین می‌کند اگر مدل متن خیلی
    طولانی بدون نقطه تولید کرد (که رخ می‌دهد)، باز هم TTS گیر نکند.
    """

    def __init__(self, min_chars=12, max_chars=180):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self._buf = ''

    def feed(self, text):
        """قطعه‌ی جدید را اضافه می‌کند و لیست جمله‌های کامل را برمی‌گرداند."""
        if not text:
            return []
        self._buf += text
        out = []

        while True:
            idx = self._find_break(self._buf)
            if idx is None:
                break
            sentence = self._buf[:idx + 1].strip()
            self._buf = self._buf[idx + 1:]
            if sentence:
                out.append(sentence)

        return out

    def flush(self):
        """هر چیزی که در بافر مانده را (در پایان پاسخ) بیرون می‌دهد."""
        rest = self._buf.strip()
        self._buf = ''
        return [rest] if rest else []

    def reset(self):
        self._buf = ''

    @property
    def pending(self):
        return self._buf

    # ------------------------------------------------------------------
    def _find_break(self, buf):
        """ایندکس آخرین کاراکتر یک جمله‌ی کامل، یا None."""
        for i, ch in enumerate(buf):
            if ch not in _SENTENCE_ENDS:
                continue
            # جمله باید حداقل طول لازم را داشته باشد
            if i + 1 < self.min_chars:
                continue
            # اعداد اعشاری (3.14) یا نسخه (v1.2) نباید بشکنند
            if ch == '.' and i > 0 and i + 1 < len(buf):
                if buf[i - 1].isdigit() and buf[i + 1].isdigit():
                    continue
            # اختصارات (Dr. / e.g.)
            if ch == '.' and self._is_abbreviation(buf[:i]):
                continue
            # نقطه‌ی وسط پاراگراف باید بعدش فاصله/پایان داشته باشد
            if i + 1 < len(buf) and not buf[i + 1].isspace() and ch not in '\n':
                continue
            return i

        # هیچ نقطه‌ی پایانی نبود: اگر بافر خیلی بلند شد، روی آخرین فاصله بشکن
        if len(buf) >= self.max_chars:
            cut = buf.rfind(' ', 0, self.max_chars)
            if cut > self.min_chars:
                return cut
        return None

    @staticmethod
    def _is_abbreviation(prefix):
        m = re.search(r'([A-Za-z.]+)$', prefix)
        if not m:
            return False
        return m.group(1).lower().strip('.') in _ABBREVIATIONS


# ---------------------------------------------------------------------------
# ۲) تشخیص فعالیت صوتی (VAD) بر پایه‌ی انرژی
# ---------------------------------------------------------------------------

class EnergyVAD:
    """VAD سبک بر پایه‌ی RMS با آستانه‌ی تطبیقی نسبت به نویز محیط.

    چرا انرژی و نه یک مدل عصبی؟ چون باید روی هر گوشی اندرویدی و در ترد
    پس‌زمینه با مصرف CPU نزدیک به صفر اجرا شود. WebRTC-VAD و Silero هر دو
    وابستگی native اضافه می‌آورند که چرخه‌ی build اندروید را شکننده می‌کند.

    منطق: سطح نویز پس‌زمینه به‌صورت پیوسته تخمین زده می‌شود؛ گفتار وقتی
    اعلام می‌شود که انرژی برای چند فریم پیاپی از (نویز × ضریب) بیشتر باشد،
    و پایان گفتار وقتی که سکوت به اندازه‌ی ``hangover_ms`` طول بکشد.
    """

    STATE_SILENCE = 'silence'
    STATE_SPEECH = 'speech'

    def __init__(self, sample_rate=16000, frame_ms=30,
                 start_frames=3, hangover_ms=800,
                 threshold_factor=3.0, min_threshold=0.012):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_size = int(sample_rate * frame_ms / 1000)
        self.start_frames = start_frames
        self.hangover_frames = max(1, int(hangover_ms / frame_ms))
        self.threshold_factor = threshold_factor
        self.min_threshold = min_threshold
        self.reset()

    def reset(self):
        self.state = self.STATE_SILENCE
        self._noise_level = self.min_threshold
        self._speech_run = 0
        self._silence_run = 0
        self._calibrated_frames = 0
        self.last_rms = 0.0

    # ------------------------------------------------------------------
    @staticmethod
    def rms(samples):
        """RMS نرمال‌شده در بازه‌ی 0..1 برای نمونه‌های float در بازه‌ی -1..1."""
        if not samples:
            return 0.0
        total = 0.0
        for s in samples:
            total += s * s
        return math.sqrt(total / len(samples))

    @property
    def threshold(self):
        return max(self.min_threshold, self._noise_level * self.threshold_factor)

    def process_frame(self, samples):
        """یک فریم صوتی را پردازش می‌کند.

        بازگشت یکی از: ``None`` (تغییری نبود)، ``'speech_start'``،
        ``'speech_end'``.
        """
        level = self.rms(samples)
        self.last_rms = level
        event = None

        if level > self.threshold:
            self._speech_run += 1
            self._silence_run = 0
            if self.state == self.STATE_SILENCE and self._speech_run >= self.start_frames:
                self.state = self.STATE_SPEECH
                event = 'speech_start'
        else:
            self._silence_run += 1
            self._speech_run = 0
            # تخمین نویز فقط در سکوت به‌روزرسانی می‌شود (میانگین متحرک آرام)
            if self.state == self.STATE_SILENCE:
                self._noise_level = 0.95 * self._noise_level + 0.05 * level
                self._calibrated_frames += 1
            if self.state == self.STATE_SPEECH and self._silence_run >= self.hangover_frames:
                self.state = self.STATE_SILENCE
                event = 'speech_end'

        return event

    @property
    def is_speaking(self):
        return self.state == self.STATE_SPEECH


# ---------------------------------------------------------------------------
# ۳) تطبیق کلمه‌ی فعال‌سازی
# ---------------------------------------------------------------------------

# نویسه‌های عربی که باید به فارسی نرمال شوند (خروجی STT ناسازگار است)
_CHAR_MAP = {
    '\u064A': '\u06CC',  # ي -> ی
    '\u0649': '\u06CC',  # ى -> ی
    '\u0643': '\u06A9',  # ك -> ک
    '\u200C': ' ',       # نیم‌فاصله -> فاصله
}


def normalize_fa(text):
    """نرمال‌سازی متن فارسی برای مقایسه: حذف اعراب، یکسان‌سازی ی/ک، فاصله‌ها."""
    if not text:
        return ''
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(_CHAR_MAP.get(ch, ch) for ch in text)
    # حذف اعراب (حرکات) عربی
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


class WakeWordMatcher:
    """تشخیص کلمه‌ی فعال‌سازی روی *متن* خروجی STT.

    این جایگزین صادقانه‌ی Porcupine است: به‌جای keyword spotting روی موج
    صوتی (که نیاز به کلید فعال‌سازی آنلاین و کتابخانه‌ی native دارد)، VAD
    یک قطعه‌ی گفتار را جدا می‌کند، STT آفلاین آن را متن می‌کند، و اینجا
    بررسی می‌شود که آیا کلمه‌ی فعال‌سازی در آن هست یا نه.
    """

    DEFAULT_PHRASES = ('هی وینا', 'سلام وینا', 'وینا', 'hey vina', 'vina')

    def __init__(self, phrases=None):
        self.set_phrases(phrases or self.DEFAULT_PHRASES)

    def set_phrases(self, phrases):
        self.phrases = [normalize_fa(p) for p in phrases if p and p.strip()]
        # طولانی‌ترین اول، تا «سلام وینا» قبل از «وینا» تطبیق بخورد
        self.phrases.sort(key=len, reverse=True)

    def match(self, text):
        """اگر کلمه‌ی فعال‌سازی پیدا شد، *باقی‌مانده‌ی* دستور را برمی‌گرداند.

        بازگشت ``None`` یعنی کلمه‌ی فعال‌سازی نبود. بازگشت رشته‌ی خالی یعنی
        فقط کلمه‌ی فعال‌سازی گفته شد (بدون دستور) - در این حالت باید حالت
        شنیدن فعال شود و منتظر دستور بماند.
        """
        norm = normalize_fa(text)
        if not norm:
            return None
        for phrase in self.phrases:
            if norm == phrase:
                return ''
            if norm.startswith(phrase + ' '):
                return norm[len(phrase):].strip()
            # کلمه‌ی فعال‌سازی ممکن است وسط جمله باشد
            idx = norm.find(' ' + phrase + ' ')
            if idx != -1:
                return norm[idx + len(phrase) + 2:].strip()
        return None
