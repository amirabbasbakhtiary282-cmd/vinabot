# -*- coding: utf-8 -*-
"""
وینا - دستیار هوش مصنوعی شخصی
فایل اصلی برنامه - نقطه ورود
"""

import os
import threading
from datetime import datetime

os.environ['KIVY_NO_ARGS'] = '1'
os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, FadeTransition, SlideTransition, NoTransition
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.clock import Clock

Window.size = (400, 750)

# ثبت فونت فارسی «وزیر» به عنوان فونت پیش‌فرض؛ بدون این کار، حروف فارسی/عربی
# با فونت لاتین پیش‌فرض سیستم به شکل نادرست (یا به‌صورت جعبه‌های خالی)
# نمایش داده می‌شوند.
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts')
_VAZIR_TTF = os.path.join(_FONT_DIR, 'Vazir.ttf')
if os.path.exists(_VAZIR_TTF):
    LabelBase.register(name='Vazir', fn_regular=_VAZIR_TTF)
    LabelBase.register(name='Roboto', fn_regular=_VAZIR_TTF)  # فونت پیش‌فرض کیوی را هم بازنویسی می‌کنیم

import src.ui  # noqa: E402,F401  ثبت ویجت‌های سفارشی در Factory قبل از بارگذاری KV
from src.design_system import theme
from src.brain import VinaBrain
from src.memory import VinaMemory
from src.voice import VinaVoice
from src.search import VinaSearch
from src.system_control import VinaSystemControl
from src.storage_manager import StorageManager
from src.text_utils import fix_rtl

from src.screens.auth import OnboardingScreen, LoginScreen
from src.screens.home import HomeScreen
from src.screens.chat import ChatScreen
from src.screens.voice import VoiceScreen
from src.screens.settings_hub import SettingsHubScreen
from src.screens.settings_detail import SettingsDetailScreen
from src.screens.settings_sections import SETTINGS_SECTIONS

Window.clearcolor = theme.bg_primary
theme.bind(bg_primary=lambda instance, value: setattr(Window, 'clearcolor', value))

_SECTION_TITLES = {s['key']: s['title'] for s in SETTINGS_SECTIONS}


class VinaApp(App):
    app_title = "Vina AI"
    current_user = StringProperty("")
    chat_history = ListProperty([])
    is_listening = BooleanProperty(False)
    is_speaking = BooleanProperty(False)
    voice_enabled = BooleanProperty(True)
    # تنظیمات گفتگوی صوتی (Phase A)
    prefer_offline_stt = BooleanProperty(True)   # پیش‌فرض: حریم خصوصی
    barge_in_enabled = BooleanProperty(True)
    wake_word_enabled = BooleanProperty(False)
    voice_state = StringProperty('idle')
    live_transcript = StringProperty('')
    model_status = StringProperty(fix_rtl("در حال بارگذاری..."))
    current_hour = NumericProperty(datetime.now().hour)

    def build(self):
        self.title = self.app_title
        self.memory = VinaMemory()
        self.brain = VinaBrain(self.memory)
        self.voice = VinaVoice(prefer_offline_stt=self.prefer_offline_stt)
        self.search = VinaSearch()
        self.system_ctrl = VinaSystemControl()
        self.storage = StorageManager(self.memory)

        self._last_user_message = None

        # ریشه‌ی float برای نمایش Toast/Snackbar روی هر صفحه‌ای
        self.root_float_layout = FloatLayout()

        self.sm = ScreenManager()
        self.sm.transition = FadeTransition(duration=0.3)
        self.sm.add_widget(OnboardingScreen(name='onboarding'))
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(HomeScreen(name='home'))
        self.sm.add_widget(ChatScreen(name='chat'))
        self.sm.add_widget(VoiceScreen(name='voice'))
        self.sm.add_widget(SettingsHubScreen(name='settings'))
        self.sm.add_widget(SettingsDetailScreen(name='settings_detail'))

        onboarding_seen = self.memory.get_flag('onboarding_seen')
        self.sm.current = 'login' if onboarding_seen else 'onboarding'

        self.root_float_layout.add_widget(self.sm)

        Clock.schedule_interval(self._check_night_mode, 300)
        Clock.schedule_interval(self._check_reminders, 60)
        Clock.schedule_once(lambda dt: self._init_models(), 1)
        Clock.schedule_once(lambda dt: self._request_runtime_permissions(), 0.5)

        return self.root_float_layout

    def _request_runtime_permissions(self):
        """درخواست مجوزهای اجرایی لازم.

        نکاتی که در نسخه‌ی قبلی رعایت نشده بود:

        ۱) ``INTERNET`` یک مجوز «normal» است، نه «dangerous». اندروید آن
           را در زمان نصب می‌دهد و درخواست runtime برایش بی‌اثر است.
           نگه داشتنش در این لیست فقط گمراه‌کننده بود.

        ۲) ``POST_NOTIFICATIONS`` از اندروید ۱۳ (API 33) یک مجوز
           dangerous است و بدون درخواست runtime، هیچ اعلانی (از جمله
           یادآوری‌ها که در ``_check_reminders`` استفاده می‌شوند) نمایش
           داده نمی‌شود - بی‌سروصدا و بدون هیچ خطایی.
           روی نسخه‌های قدیمی‌تر این ثابت وجود ندارد، پس با getattr
           به‌صورت ایمن گرفته می‌شود.

        ۳) نتیجه‌ی درخواست باید لاگ شود؛ اگر کاربر میکروفون را رد کند،
           باید بدانیم چرا قابلیت صوتی کار نمی‌کند.
        """
        try:
            from src.android_bridge import AndroidBridge, is_android
            if not is_android():
                return

            bridge = AndroidBridge()
            from android.permissions import Permission

            wanted = [Permission.RECORD_AUDIO]

            # فقط روی اندروید ۱۳+ وجود دارد
            post_notifications = getattr(Permission, 'POST_NOTIFICATIONS', None)
            if post_notifications:
                wanted.append(post_notifications)

            def _on_result(permissions, grants):
                for name, granted in zip(permissions, grants):
                    state = 'داده شد' if granted else 'رد شد'
                    print(f'وینا: مجوز {name}: {state}')
                    if not granted and 'RECORD_AUDIO' in str(name):
                        Clock.schedule_once(
                            lambda dt: setattr(
                                self, 'voice_state', 'no_permission'), 0)

            bridge.request_permissions(wanted, _on_result)
        except Exception as exc:
            print(f"خطا در درخواست مجوزها: {exc}")

    def on_stop(self):
        """پاک‌سازی منابع هنگام بستن برنامه (جلوگیری از نشت حافظه/تردهای معلق)"""
        try:
            self.brain.unload_model()
        except Exception:
            pass
        try:
            self.voice.shutdown()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ناوبری
    # ------------------------------------------------------------------
    def switch_tab(self, tab_name):
        """جابه‌جایی بین تب‌های اصلی (خانه/چت/صدا/تنظیمات) بدون افکت اسلاید اضافی"""
        self.sm.transition = NoTransition()
        self.sm.current = tab_name

    def open_settings_section(self, section_key):
        """باز کردن صفحه‌ی جزئیات یک بخش تنظیمات"""
        detail_screen = self.sm.get_screen('settings_detail')
        title = _SECTION_TITLES.get(section_key, section_key)
        detail_screen.load_section(section_key, title)
        self.sm.transition = SlideTransition(direction='left')
        self.sm.current = 'settings_detail'

    def close_settings_section(self):
        self.sm.transition = SlideTransition(direction='right')
        self.sm.current = 'settings'

    # ------------------------------------------------------------------
    # بارگذاری مدل
    # ------------------------------------------------------------------
    def _init_models(self):
        """بارگذاری مدل‌ها در پس‌زمینه"""
        threading.Thread(target=self._load_model_thread, daemon=True).start()

    def _load_model_thread(self):
        try:
            Clock.schedule_once(
                lambda dt: setattr(self, 'model_status', fix_rtl('در حال بارگذاری مدل زبانی...')), 0
            )

            # پوشه‌ی مدل‌ها همیشه ساخته می‌شود، حتی وقتی هیچ مدلی نیست.
            # (خواسته‌ی صریح: برنامه باید پوشه‌ی Models را خودکار بسازد تا
            # کاربر بتواند فایل را داخلش کپی کند.)
            from src import model_paths
            try:
                models_dir = model_paths.ensure_models_dir()
                print(f'وینا: پوشه‌ی مدل‌ها: {models_dir}')
            except Exception as exc:
                print(f'وینا: ساخت پوشه‌ی مدل‌ها ناموفق بود: {exc}')

            loaded = self.brain.load_model()

            if loaded:
                status = 'آماده'
            elif self.brain.engine.load_error:
                # مدل پیدا شد ولی بارگذاری نشد - این با «مدلی نیست» فرق
                # دارد و کاربر باید تفاوت را بفهمد.
                status = 'خطا در بارگذاری مدل - جزئیات در تنظیمات'
                print(f'وینا: خطای بارگذاری مدل: {self.brain.engine.load_error}')
            else:
                status = 'بدون مدل - از تنظیمات یک مدل اضافه کنید'
                print('وینا: هیچ فایل GGUF پیدا نشد. مسیرهای بررسی‌شده:\n'
                      + model_paths.describe_search_locations())

            Clock.schedule_once(lambda dt: setattr(self, 'model_status', fix_rtl(status)), 0)
        except Exception as exc:
            error_text = f'خطا: {str(exc)[:50]}'
            Clock.schedule_once(lambda dt: setattr(self, 'model_status', fix_rtl(error_text)), 0)

    def start_model_download(self):
        """شروع دانلود اولین مدل پیشنهادی از تنظیمات"""
        from src.model_downloader import ModelDownloader

        def _download():
            downloader = ModelDownloader()
            downloader.status_callback = lambda msg: Clock.schedule_once(
                lambda dt: setattr(self, 'model_status', fix_rtl(msg)), 0
            )
            recommended = list(ModelDownloader.RECOMMENDED_MODELS.keys())
            if not recommended:
                return
            success = downloader.download_model(recommended[0])
            if success:
                self._load_model_thread()

        threading.Thread(target=_download, daemon=True).start()

    # ------------------------------------------------------------------
    # حالت شب و یادآوری‌ها
    # ------------------------------------------------------------------
    def _check_night_mode(self, dt):
        self.current_hour = datetime.now().hour

    def _check_reminders(self, dt):
        try:
            reminders = self.memory.get_pending_reminders()
            now = datetime.now()
            for reminder in reminders:
                reminder_time = datetime.strptime(reminder['time'], '%Y-%m-%d %H:%M')
                if reminder_time <= now:
                    self._show_reminder(reminder)
                    self.memory.mark_reminder_done(reminder['id'])
        except Exception as exc:
            print(f"خطا در بررسی یادآوری‌ها: {exc}")

    def _show_reminder(self, reminder):
        message = reminder['message']
        Clock.schedule_once(lambda dt: self._popup_reminder(message), 0)

    def _popup_reminder(self, message):
        try:
            from src.design_system import ModernDialog, PrimaryButton
            dialog = ModernDialog(title=fix_rtl('یادآوری'), message=fix_rtl(message))
            btn = PrimaryButton(text=fix_rtl('متوجه شدم'))
            btn.bind(on_release=lambda *a: dialog.dismiss())
            dialog.add_button(btn)
            dialog.open()
        except Exception as exc:
            print(f"خطا در نمایش یادآوری: {exc}")

    # ------------------------------------------------------------------
    # ورود کاربر
    # ------------------------------------------------------------------
    def do_login(self, username, password):
        if not username or not password:
            return False, "نام کاربری و رمز عبور را وارد کنید"

        success = self.memory.verify_user(username, password)
        if success:
            self.current_user = username
            self.memory.set_current_user(username)
            Clock.schedule_once(lambda dt: self._switch_to_home(), 0)
            return True, "ورود موفق"

        exists = self.memory.user_exists(username)
        if exists:
            return False, "رمز عبور اشتباه است"

        created = self.memory.create_user(username, password)
        if not created:
            return False, "خطا در ایجاد حساب کاربری"
        self.current_user = username
        self.memory.set_current_user(username)
        Clock.schedule_once(lambda dt: self._switch_to_home(), 0)
        return True, "حساب کاربری جدید ایجاد شد"

    def _switch_to_home(self):
        self.sm.transition = SlideTransition(direction='left')
        self.sm.current = 'home'

    # ------------------------------------------------------------------
    # چت
    # ------------------------------------------------------------------
    def send_message(self, text):
        if not text.strip():
            return

        self._last_user_message = text
        user_msg = {
            'role': 'user',
            'text': text,
            'time': datetime.now().strftime('%H:%M'),
        }
        self.chat_history.append(user_msg)
        self._notify_new_message(user_msg)
        self._set_typing_indicator(True)

        threading.Thread(target=self._process_message, args=(text,), daemon=True).start()

    def regenerate_last_response(self):
        """بازتولید آخرین پاسخ وینا (حذف آخرین پاسخ و تولید دوباره)"""
        if not self._last_user_message:
            return
        if self.chat_history and self.chat_history[-1]['role'] == 'vina':
            self.chat_history.pop()
            Clock.schedule_once(lambda dt: self._refresh_chat_screen(), 0)
        self._set_typing_indicator(True)
        threading.Thread(
            target=self._process_message, args=(self._last_user_message,), daemon=True
        ).start()

    def _refresh_chat_screen(self):
        try:
            chat_screen = self.sm.get_screen('chat')
            chat_screen._render_history()
        except Exception:
            pass

    def _notify_new_message(self, msg):
        def _apply(dt):
            try:
                chat_screen = self.sm.get_screen('chat')
                chat_screen.on_new_message(msg)
            except Exception:
                pass
        Clock.schedule_once(_apply, 0)

    def _set_typing_indicator(self, visible):
        def _apply(dt):
            try:
                chat_screen = self.sm.get_screen('chat')
                if visible:
                    chat_screen.show_typing_indicator()
                else:
                    chat_screen.hide_typing_indicator()
            except Exception:
                pass
        Clock.schedule_once(_apply, 0)

    def _process_message(self, text):
        try:
            self.memory.save_conversation('user', text)
            response = self._get_response(text)
            self.memory.save_conversation('vina', response)
            self.memory.analyze_and_store_preferences(text)

            self._set_typing_indicator(False)
            self._add_bot_message(response)

            if self.voice_enabled:
                self._speak_response(response)
        except Exception as exc:
            self._set_typing_indicator(False)
            error_text = f'خطا در پردازش: {str(exc)[:100]}'
            self._add_bot_message(error_text)

    def _get_response(self, text, on_token=None):
        """پاسخ وینا؛ اگر ``on_token`` داده شود، تولید جریانی انجام می‌شود.

        مسیر دستورات سیستمی/جستجو/یادآوری پاسخ آماده برمی‌گرداند (جریانی
        نیست)، اما برای یکنواختی همان را هم از طریق callback می‌فرستیم.
        """
        text_lower = text.strip()

        def _direct(answer):
            """پاسخ‌های آماده (غیر LLM) را هم از مسیر جریانی عبور می‌دهد."""
            if on_token is not None and answer:
                on_token(answer)
            return answer

        system_result = self.system_ctrl.handle_command(text_lower)
        if system_result:
            return system_result

        search_triggers = ['جستجو', 'سرچ', 'اینترنت', 'گوگل', 'قیمت', 'آب و هوا', 'خبر', 'اخبار']
        if any(trigger in text_lower for trigger in search_triggers):
            query = self._extract_search_query(text_lower)
            if query:
                return self.search.search(query)

        reminder_result = self._handle_reminder(text_lower)
        if reminder_result:
            return reminder_result

        note_result = self._handle_notes(text_lower)
        if note_result:
            return note_result

        context = self.memory.get_context()
        return self.brain.generate_response(text, context, on_token=on_token)

    def _extract_search_query(self, text):
        prefixes = ['جستجو کن', 'سرچ کن', 'از اینترنت بگرد', 'در اینترنت پیدا کن',
                    'قیمت', 'آب و هوا', 'خبر', 'اخبار']
        for prefix in prefixes:
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                query = text[idx:].strip()
                if query:
                    return query
        return text

    def _handle_reminder(self, text):
        reminder_keywords = ['یادم باشد', 'یادت باشد', 'یادآوری کن', 'یادآور کن']
        for kw in reminder_keywords:
            if kw in text:
                idx = text.index(kw) + len(kw)
                message = text[idx:].strip()
                if message:
                    self.memory.add_reminder(message)
                    return f"حتماً یادآوری می‌کنم: {message}"
        return None

    def _handle_notes(self, text):
        note_keywords = ['یادداشت کن', 'ثبت کن', 'ذخیره کن', 'به خاطر بسپار']
        for kw in note_keywords:
            if kw in text:
                idx = text.index(kw) + len(kw)
                note = text[idx:].strip()
                if note:
                    self.memory.save_note(note)
                    return f"یادداشت شد: {note}"
        return None

    def _speak_response(self, text):
        Clock.schedule_once(lambda dt: setattr(self, 'is_speaking', True), 0)
        try:
            self.voice.speak(text)
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'is_speaking', False), 0)

    def _add_user_message(self, text):
        msg = {
            'role': 'user',
            'text': text,
            'time': datetime.now().strftime('%H:%M'),
        }
        self.chat_history.append(msg)
        self._notify_new_message(msg)

    def _add_bot_message(self, text):
        msg = {
            'role': 'vina',
            'text': text,
            'time': datetime.now().strftime('%H:%M'),
        }
        self.chat_history.append(msg)
        self._notify_new_message(msg)

    def clear_history(self):
        """پاک کردن تاریخچه‌ی چت فعلی از حافظه‌ی نمایشی (نه دیتابیس)"""
        self.chat_history = []
        try:
            chat_screen = self.sm.get_screen('chat')
            chat_screen._render_history()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # صدا
    # ------------------------------------------------------------------
    def start_listening(self, on_transcript=None):
        self.is_listening = True
        threading.Thread(target=self._listen_thread, args=(on_transcript,), daemon=True).start()

    def _listen_thread(self, on_transcript=None):
        try:
            text = self.voice.listen()
            if text:
                if callable(on_transcript):
                    Clock.schedule_once(lambda dt: on_transcript(text), 0)
                Clock.schedule_once(lambda dt: self.send_message(text), 0)
        except Exception as exc:
            print(f"خطای تشخیص صدا: {exc}")
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'is_listening', False), 0)

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled

    # ------------------------------------------------------------------
    # گفتگوی صوتی زنده (Phase A)
    # ------------------------------------------------------------------
    def set_offline_stt(self, enabled):
        """تغییر موتور تشخیص گفتار بین آفلاین (Vosk) و آنلاین (گوگل)."""
        self.prefer_offline_stt = bool(enabled)
        self.voice.prefer_offline_stt = bool(enabled)
        # جلسه‌ی گفتگوی فعلی باید بازسازی شود تا موتور جدید اعمال گردد
        was_running = bool(self.voice.conversation and self.voice.conversation.is_running)
        self.voice.stop_conversation()
        self._voice_conversation = None
        if was_running:
            self.start_voice_conversation()
        info = self.voice.stt_engine_info()
        self._toast(info.get('label', ''))

    def download_stt_model(self, lang='fa'):
        """دانلود مدل آفلاین تشخیص گفتار در پس‌زمینه."""
        from src.model_downloader import VoskModelDownloader

        downloader = VoskModelDownloader()
        downloader.status_callback = lambda msg: Clock.schedule_once(
            lambda dt: self._toast(msg), 0)
        downloader.progress_callback = lambda key, pct: Clock.schedule_once(
            lambda dt: setattr(self, 'model_status',
                               fix_rtl(f'دانلود مدل صوتی: {pct:.0f}%')), 0)
        threading.Thread(target=downloader.download, args=(lang,),
                         daemon=True, name='VoskDownload').start()

    def _toast(self, message):
        """نمایش پیام کوتاه به کاربر (اگر Toast در دسترس نبود، در لاگ)."""
        try:
            from src.design_system import Toast
            Toast(text=fix_rtl(str(message))).show(self.root_float_layout)
        except Exception:
            print(f'[وینا] {message}')

    def _llm_stream_for_voice(self, user_text, on_token):
        """پل بین گفتگوی صوتی و مغز وینا (با تولید جریانی).

        از همان ``_get_response`` استفاده می‌کند تا گفتگوی صوتی دقیقاً همان
        قابلیت‌های چت متنی (دستورات سیستمی، جستجو، یادآوری، حافظه) را داشته
        باشد - نه یک مسیر جداگانه و ناقص.
        """
        self.memory.save_conversation('user', user_text)
        Clock.schedule_once(lambda dt: self._add_user_message(user_text), 0)

        collected = []

        def _token(piece):
            collected.append(piece)
            Clock.schedule_once(
                lambda dt: setattr(self, 'live_transcript', ''.join(collected)), 0)
            # اگر گفتگو قطع شده باشد، on_token مقدار False می‌دهد و تولید
            # باید فوراً متوقف شود (قطع کردن وسط صحبت).
            return on_token(piece)

        response = self._get_response(user_text, on_token=_token)
        response = (response or ''.join(collected)).strip()

        self.memory.save_conversation('vina', response)
        try:
            self.memory.analyze_and_store_preferences(user_text)
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._add_bot_message(response), 0)
        return response

    def ensure_microphone_permission(self, callback):
        """مجوز میکروفون را در زمان اجرا می‌گیرد (اندروید ۶ به بالا).

        مجوز دقیقاً *در لحظه‌ی نیاز* درخواست می‌شود، نه همه با هم هنگام
        اجرا شدن برنامه؛ این هم توصیه‌ی رسمی اندروید است و هم نرخ پذیرش
        کاربر را بالا می‌برد.
        """
        from src.android_bridge import is_android

        if not is_android():
            callback(True)
            return

        perm = 'android.permission.RECORD_AUDIO'
        if self.voice.bridge.has_permission(perm):
            callback(True)
            return

        def _on_result(permissions, grants):
            granted = bool(grants) and all(grants)
            Clock.schedule_once(lambda dt: callback(granted), 0)

        self.voice.bridge.request_permissions([perm], _on_result)

    def start_voice_conversation(self):
        """شروع گفتگوی صوتی زنده و دوطرفه."""
        conv = self.voice.conversation
        if conv is None:
            conv = self.voice.create_conversation(
                llm_generate=self._llm_stream_for_voice,
                wake_word_enabled=self.wake_word_enabled,
                barge_in_enabled=self.barge_in_enabled,
            )
            conv.on_state_change = lambda st: Clock.schedule_once(
                lambda dt: self._on_voice_state(st), 0)
            conv.on_partial_transcript = lambda t: Clock.schedule_once(
                lambda dt: setattr(self, 'live_transcript', t), 0)
            conv.on_error = lambda msg: Clock.schedule_once(
                lambda dt: self._toast(msg), 0)

        if self.voice.stt_note:
            self._toast(self.voice.stt_note)

        if not conv.start():
            self._toast('میکروفون در دسترس نیست - مجوز ضبط صدا را بررسی کنید')
            return False
        return True

    def stop_voice_conversation(self):
        self.voice.stop_conversation()
        self.voice_state = 'idle'
        self.is_listening = False
        self.is_speaking = False

    def _on_voice_state(self, state):
        self.voice_state = state
        self.is_listening = (state == 'listening')
        self.is_speaking = (state == 'speaking')

    def get_personality_context(self):
        return self.memory.get_personality()


if __name__ == '__main__':
    VinaApp().run()
