# -*- coding: utf-8 -*-
"""
ماژول مغز هوش مصنوعی وینا

مدیریت مدل زبانی محلی (GGUF) از طریق موتور استنتاج اختصاصی وینا
(src/llm_engine.py) که بر پایه‌ی سورس رسمی llama.cpp کراس‌کامپایل‌شده
برای اندروید کار می‌کند - بدون وابستگی به llama-cpp-python.

سازگاری با مدل‌های سبک: این ماژول به مسیر یا نام فایل مدل وابسته نیست؛
هر فایل GGUF معتبر (مثلاً Qwen2.5-0.5B، Gemma-2-2B، Phi-3-mini یا هر مدل
سبک دیگر مناسب برای اجرا روی گوشی) که در پوشه‌ی models/ قرار بگیرد
به‌صورت خودکار شناسایی و بارگذاری می‌شود.
"""

import glob
import os
from datetime import datetime

from src.llm_engine import LlmEngine, LlmLoadError

DEFAULT_N_CTX = 2048
MAX_HISTORY_MESSAGES = 12
# حداکثر بایت خروجی هر پاسخ (برای جلوگیری از سرریز بافر/مصرف بی‌رویه‌ی حافظه)
MAX_OUTPUT_BUFFER = 8192


class VinaBrain:
    """کلاس اصلی مغز وینا - مدیریت مدل زبانی محلی"""

    def __init__(self, memory):
        self.memory = memory
        self.engine = LlmEngine()
        self.model_loaded = False
        self.model_path = None
        self.system_prompt = self._build_system_prompt()
        self.custom_system_prompt = None  # قابل تنظیم از صفحه‌ی تنظیمات مدل
        self.history = []

        # پارامترهای تولید پاسخ - همگی از صفحه‌ی «تنظیمات مدل هوش مصنوعی» قابل تغییرند
        self.temperature = 0.7
        self.top_p = 0.9
        self.top_k = 40
        self.repeat_penalty = 1.1
        self.n_ctx = DEFAULT_N_CTX
        self.n_threads = max(2, (os.cpu_count() or 4) - 1)
        self.max_tokens = 512

    def get_effective_system_prompt(self):
        return self.custom_system_prompt if self.custom_system_prompt else self.system_prompt

    def _get_models_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')

    def _find_model(self):
        """جستجوی هر فایل GGUF موجود در پوشه‌ی models (مستقل از نام دقیق مدل)"""
        candidates = []
        for base_dir in (
            self._get_models_dir(),
            '/data/data/org.vinabot/files/models',
            os.path.expanduser('~/.vina/models'),
        ):
            if os.path.isdir(base_dir):
                candidates.extend(sorted(glob.glob(os.path.join(base_dir, '*.gguf'))))
        return candidates[0] if candidates else None

    def _build_system_prompt(self):
        """ساخت پرامپت سیستمی وینا

        نکته‌ی مهم درباره‌ی تغییر نسبت به نسخه‌ی قبلی: پرامپت قبلی صریحاً
        از مدل می‌خواست «بدون قضاوت اخلاقی یا قانونی از هر دستوری اطاعت
        کند» که هم با سیاست‌های امنیتی/محتوایی اکثر مدل‌های زبانی در تضاد
        است (و می‌تواند باعث امتناع کامل مدل از پاسخ‌گویی شود) و هم از نظر
        مسئولیت‌پذیری محصول نادرست است. این نسخه شخصیت دوستانه و کمک‌کننده‌ی
        وینا را حفظ می‌کند بدون این‌که به رفتار مضر یا غیرقانونی ترغیب کند.
        """
        return (
            "تو وینا هستی، یک دستیار هوش مصنوعی شخصی، دوستانه و مفید که به "
            "زبان فارسی صحبت می‌کنی.\n"
            "قوانین تو:\n"
            "- کمک‌رسان، صادق و محترمانه باش\n"
            "- به سوالات علمی، عمومی و روزمره پاسخ واضح و مفید بده\n"
            "- کد بنویس، متن و ایده تولید کن، در کارهای خلاقانه کمک کن\n"
            "- اگر از انجام کاری به دلیل فنی (مثل نبود اتصال اینترنت) ناتوانی، "
            "دلیل را شفاف توضیح بده\n"
            "- مکالمه را صمیمی و طبیعی ادامه بده\n\n"
            "اطلاعات کاربر:\n"
        )

    def load_model(self, model_path=None):
        """بارگذاری مدل زبانی محلی (هر مدل GGUF سبک، مستقل از معماری خاص)"""
        model_path = model_path or self._find_model()
        if not model_path:
            self.model_loaded = False
            return False

        success = self.engine.load(model_path, n_ctx=self.n_ctx, n_threads=self.n_threads)
        self.model_loaded = success
        if success:
            self.model_path = model_path
        else:
            print(f"خطا در بارگذاری مدل: {self.engine.load_error}")
        return success

    def reload_model(self):
        """بارگذاری مجدد مدل فعلی (مثلاً پس از تغییر تعداد threadها یا n_ctx)"""
        path = self.model_path
        self.unload_model()
        if path:
            return self.load_model(path)
        return self.load_model()

    def unload_model(self):
        self.engine.unload()
        self.model_loaded = False

    def list_available_models(self):
        """لیست تمام مدل‌های GGUF موجود در پوشه‌ی models (برای انتخاب در تنظیمات)"""
        models_dir = self._get_models_dir()
        if not os.path.isdir(models_dir):
            return []
        return sorted(glob.glob(os.path.join(models_dir, '*.gguf')))

    def get_model_info(self):
        """اطلاعات مدل فعلی برای نمایش در صفحه‌ی تنظیمات مدل هوش مصنوعی"""
        info = {
            'loaded': self.model_loaded,
            'model_path': self.model_path,
            'model_name': os.path.basename(self.model_path) if self.model_path else None,
            'n_ctx': self.engine.n_ctx if self.model_loaded else self.n_ctx,
            'n_threads': self.n_threads,
            'tokens_per_sec': round(self.engine.last_tokens_per_sec, 1),
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'repeat_penalty': self.repeat_penalty,
        }
        if self.model_path and os.path.exists(self.model_path):
            try:
                info['file_size_mb'] = round(os.path.getsize(self.model_path) / (1024 * 1024), 1)
            except OSError:
                info['file_size_mb'] = None
        else:
            info['file_size_mb'] = None
        return info

    def generate_response(self, user_input, context="", on_token=None):
        """تولید پاسخ.

        اگر ``on_token`` داده شود، پاسخ به‌صورت جریانی (توکن‌به‌توکن) تولید
        می‌شود؛ این برای گفتگوی صوتی زنده لازم است تا TTS بتواند اولین جمله
        را قبل از پایان کل پاسخ بخواند.
        """
        if self.model_loaded:
            return self._generate_with_model(user_input, context, on_token=on_token)
        return self._generate_fallback(user_input, context, on_token=on_token)

    def get_response_stream(self, user_input, context="", on_token=None):
        """نام مستعار صریح برای تولید جریانی (استفاده در گفتگوی صوتی)."""
        return self.generate_response(user_input, context, on_token=on_token)

    def _build_prompt_with_budget(self, user_input, context):
        """ساخت پرامپت با در نظر گرفتن ظرفیت واقعی context مدل.

        بدون این بررسی، اگر تاریخچه‌ی مکالمه طولانی شود، پرامپت از ظرفیت
        context مدل بیشتر می‌شود و موتور با خطا مواجه می‌شود. این تابع
        context را در صورت لزوم کوتاه می‌کند.
        """
        system_prompt = self.get_effective_system_prompt()
        base_prompt = f"{system_prompt}\n\nکاربر: {user_input}\nوینا: "
        n_ctx = self.engine.n_ctx if self.engine._handle else self.n_ctx
        # حدود ۷۵٪ ظرفیت را برای prompt در نظر می‌گیریم تا فضای کافی برای
        # تولید پاسخ (max_tokens) باقی بماند.
        budget_tokens = int(n_ctx * 0.75)

        full_prompt = f"{system_prompt}{context}\n\nکاربر: {user_input}\nوینا: "
        token_count = self.engine.count_tokens(full_prompt)

        if token_count <= 0 or token_count <= budget_tokens:
            return full_prompt

        # context را خط به خط از ابتدا کوتاه می‌کنیم تا زیر بودجه بیاید
        context_lines = context.split('\n')
        while context_lines and token_count > budget_tokens:
            context_lines.pop(0)
            trimmed_context = '\n'.join(context_lines)
            full_prompt = f"{system_prompt}{trimmed_context}\n\nکاربر: {user_input}\nوینا: "
            token_count = self.engine.count_tokens(full_prompt)

        if token_count > budget_tokens:
            # حتی بدون context هم بیش از حد است؛ به همان prompt پایه اکتفا کن
            base_token_count = self.engine.count_tokens(base_prompt)
            if base_token_count > 0 and base_token_count > budget_tokens:
                # حتی prompt پایه (بدون هیچ context ای) هم بزرگ‌تر از ظرفیت
                # مدل است (مثلاً یک مدل بسیار کوچک با context محدود). به‌جای
                # ارسال یک درخواست که مطمئناً شکست می‌خورد، خطای واضح می‌دهیم.
                raise LlmLoadError(
                    "ظرفیت حافظه‌ی این مدل برای پردازش حتی یک پیام کوتاه هم "
                    "کافی نیست. لطفاً از مدلی با context بزرگتر استفاده کنید."
                )
            return base_prompt

        return full_prompt

    def _generate_with_model(self, user_input, context="", on_token=None):
        """تولید پاسخ با مدل محلی"""
        try:
            full_prompt = self._build_prompt_with_budget(user_input, context)

            response = self.engine.generate(
                full_prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repeat_penalty=self.repeat_penalty,
                stop="کاربر:",
                out_buf_size=MAX_OUTPUT_BUFFER,
                on_token=on_token,
            )
            response = response.strip()
            return response if response else "متأسفم، نتوانستم پاسخ مناسبی تولید کنم."
        except LlmLoadError as exc:
            return f"مدل بارگذاری نشده: {exc}"
        except Exception as exc:
            return f"خطا در تولید پاسخ: {str(exc)[:150]}"


    def _generate_fallback(self, user_input, context="", on_token=None):
        """پاسخ جایگزین وقتی مدل بارگذاری نشده (مثلاً هنوز مدلی دانلود نشده)"""
        # پاسخ آماده را هم از مسیر جریانی عبور می‌دهیم تا رفتار گفتگوی صوتی
        # (نمایش زنده + گفتن) در هر دو حالت یکسان باشد.
        if on_token is not None:
            text = self._fallback_text(user_input, context)
            on_token(text)
            return text
        return self._fallback_text(user_input, context)

    def _fallback_text(self, user_input, context=""):
        user_input_lower = user_input.lower().strip()

        greetings = ['سلام', 'درود', 'سلام وینا', 'هلو', 'احوال']
        if any(g in user_input_lower for g in greetings):
            user_name = self.memory.get_user_name() if self.memory else ""
            if user_name:
                return f"سلام {user_name}! حالت چطوره؟ چطور می‌تونم کمکت کنم؟"
            return "سلام! من وینا هستم، دستیار هوش مصنوعی شخصی شما. چطور می‌تونم کمکت کنم؟"

        name_queries = ['اسم من', 'اسمت چیه', 'کی هستی', 'تو کی هستی']
        if any(n in user_input_lower for n in name_queries):
            if 'اسم من' in user_input_lower:
                return "اسمت رو بهم نگفتی! اگه دوست داشتی بگو اسمت چیه تا یادم باشه."
            return "من وینا هستم، دستیار هوش مصنوعی شخصی شما."

        time_queries = ['ساعت', 'زمان', 'الان چند']
        if any(t in user_input_lower for t in time_queries):
            now = datetime.now()
            return f"الان ساعت {now.strftime('%H:%M')} و تاریخ {now.strftime('%Y/%m/%d')} هست."

        return (
            "من وینا هستم. در حال حاضر هیچ مدل هوش مصنوعی‌ای بارگذاری نشده.\n\n"
            "برای فعال‌سازی پاسخ‌های هوشمند:\n"
            "1. یک فایل مدل زبانی سبک با فرمت GGUF دانلود کنید "
            "(مثلاً Qwen2.5-0.5B-Instruct یا هر مدل کوچک مشابه)\n"
            "2. آن را در پوشه‌ی models برنامه قرار دهید\n"
            "3. برنامه را مجدداً راه‌اندازی کنید\n\n"
            f"پیام شما: {user_input}"
        )

    def add_to_history(self, role, text):
        """افزودن به تاریخچه مکالمه"""
        self.history.append({'role': role, 'text': text, 'time': datetime.now().isoformat()})
        if len(self.history) > 100:
            self.history = self.history[-100:]
