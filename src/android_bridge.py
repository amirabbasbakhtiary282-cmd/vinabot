# -*- coding: utf-8 -*-
"""
ماژول یکپارچه‌سازی با اندروید

این ماژول تمام دسترسی‌های واقعی به API های اندروید (از طریق pyjnius) را
پیاده‌سازی می‌کند: مجوزها، گفتار به متن، متن به گفتار، کنترل سیستم و غیره.

نکته‌ی مهم درباره‌ی محدودیت‌های واقعی اندروید (از نسخه‌های جدید):
- اپلیکیشن‌های عادی (غیرسیستمی) دیگر اجازه‌ی روشن/خاموش کردن مستقیم
  وای‌فای یا بلوتوث را از طریق کد ندارند؛ در عوض باید پنل تنظیمات مربوطه
  را باز کرد تا کاربر خودش تغییر را اعمال کند. این ماژول همین رفتار واقعی
  و مجاز را پیاده می‌کند - نه یک دستور شل جعلی که روی گوشی معمولی (بدون
  روت) اصلاً اجرا نمی‌شود.
- تنظیم روشنایی سیستمی نیاز به مجوز ویژه‌ی WRITE_SETTINGS دارد که کاربر
  باید صریحاً از صفحه‌ی تنظیمات اندروید به برنامه بدهد.
"""


def is_android():
    """تشخیص واقعی اجرای برنامه روی اندروید (نه ترموکس یا لینوکس معمولی)"""
    try:
        from kivy.utils import platform
        return platform == 'android'
    except Exception:
        return False


class AndroidBridge:
    """پوششی یکپارچه روی APIهای اندروید با استفاده از pyjnius"""

    def __init__(self):
        self._android = is_android()
        self._tts = None
        self._activity = None
        self._speech_recognizer = None

        if self._android:
            try:
                from jnius import autoclass
                self._autoclass = autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                self._activity = PythonActivity.mActivity
            except Exception as exc:
                print(f"AndroidBridge: خطا در مقداردهی اولیه: {exc}")
                self._android = False

    # ------------------------------------------------------------------
    # مجوزها
    # ------------------------------------------------------------------
    def request_permissions(self, permissions, callback=None):
        """درخواست مجوزهای runtime (لازم برای API 23 به بالا)"""
        if not self._android:
            if callback:
                callback(permissions, [True] * len(permissions))
            return
        try:
            from android.permissions import request_permissions
            request_permissions(permissions, callback)
        except Exception as exc:
            print(f"خطا در درخواست مجوز: {exc}")
            if callback:
                callback(permissions, [False] * len(permissions))

    def has_permission(self, permission):
        if not self._android:
            return True
        try:
            from android.permissions import check_permission
            return check_permission(permission)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # متن به گفتار (TTS) - از طریق android.speech.tts.TextToSpeech واقعی
    # ------------------------------------------------------------------
    def _ensure_tts(self):
        if self._tts is not None or not self._android:
            return self._tts
        try:
            TextToSpeech = self._autoclass('android.speech.tts.TextToSpeech')
            self._tts = TextToSpeech(self._activity, None)
        except Exception as exc:
            print(f"خطا در مقداردهی TTS: {exc}")
            self._tts = None
        return self._tts

    def set_tts_language_fa(self):
        """تلاش برای تنظیم زبان فارسی؛ در صورت نبود، پیش‌فرض دستگاه حفظ می‌شود"""
        tts = self._ensure_tts()
        if not tts:
            return False
        try:
            Locale = self._autoclass('java.util.Locale')
            fa_locale = Locale('fa', 'IR')
            result = tts.setLanguage(fa_locale)
            # LANG_MISSING_DATA = -1، LANG_NOT_SUPPORTED = -2
            return result >= 0
        except Exception:
            return False

    def speak(self, text):
        """گویش متن با موتور TTS داخلی اندروید"""
        if not text:
            return False
        if not self._android:
            print(f"[TTS شبیه‌سازی‌شده - فقط دسکتاپ]: {text}")
            return False

        tts = self._ensure_tts()
        if not tts:
            return False
        try:
            TextToSpeechClass = self._autoclass('android.speech.tts.TextToSpeech')
            tts.speak(text, TextToSpeechClass.QUEUE_FLUSH, None, None)
            return True
        except Exception as exc:
            print(f"خطا در speak(): {exc}")
            return False

    def stop_speaking(self):
        if self._tts is not None:
            try:
                self._tts.stop()
            except Exception:
                pass

    def shutdown_tts(self):
        if self._tts is not None:
            try:
                self._tts.shutdown()
            except Exception:
                pass
            self._tts = None

    # ------------------------------------------------------------------
    # گفتار به متن (STT) - از طریق android.speech.SpeechRecognizer واقعی
    # ------------------------------------------------------------------
    def listen_once(self, on_result, on_error, language='fa-IR', timeout_sec=12):
        """یک بار گوش می‌دهد و متن تشخیص داده‌شده را از طریق callback برمی‌گرداند.

        این متد asynchronous است: بلافاصله برمی‌گردد و نتیجه با فراخوانی
        on_result(text) یا on_error(message) اعلام می‌شود.
        """
        if not self._android:
            on_error("گفتار به متن فقط روی اندروید در دسترس است.")
            return

        try:
            from android.runnable import run_on_ui_thread
            autoclass = self._autoclass

            Intent = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')

            if not SpeechRecognizer.isRecognitionAvailable(self._activity):
                on_error("سرویس تشخیص گفتار روی این دستگاه در دسترس نیست.")
                return

            from jnius import PythonJavaClass, java_method

            class _Listener(PythonJavaClass):
                __javainterfaces__ = ['android/speech/RecognitionListener']

                def __init__(self, result_cb, error_cb, recognizer_holder):
                    super().__init__()
                    self.result_cb = result_cb
                    self.error_cb = error_cb
                    self.recognizer_holder = recognizer_holder

                @java_method('(Landroid/os/Bundle;)V')
                def onReadyForSpeech(self, params):
                    pass

                @java_method('()V')
                def onBeginningOfSpeech(self):
                    pass

                @java_method('(F)V')
                def onRmsChanged(self, rmsdB):
                    pass

                @java_method('([B)V')
                def onBufferReceived(self, buffer):
                    pass

                @java_method('()V')
                def onEndOfSpeech(self):
                    pass

                @java_method('(I)V')
                def onError(self, error):
                    messages = {
                        1: "خطای شبکه (تایم‌اوت)",
                        2: "خطای شبکه",
                        3: "خطای صوتی",
                        4: "خطای سرور",
                        5: "خطای کلاینت",
                        6: "زمان صحبت تمام شد",
                        7: "چیزی تشخیص داده نشد",
                        8: "سرویس مشغول است",
                        9: "دسترسی کافی وجود ندارد",
                    }
                    self.error_cb(messages.get(error, f"خطای ناشناخته ({error})"))
                    recognizer = self.recognizer_holder.get('instance')
                    if recognizer:
                        recognizer.destroy()

                @java_method('(Landroid/os/Bundle;)V')
                def onResults(self, results):
                    matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if matches and matches.size() > 0:
                        self.result_cb(matches.get(0))
                    else:
                        self.error_cb("متنی تشخیص داده نشد.")
                    recognizer = self.recognizer_holder.get('instance')
                    if recognizer:
                        recognizer.destroy()

                @java_method('(Landroid/os/Bundle;)V')
                def onPartialResults(self, partialResults):
                    pass

                @java_method('(ILandroid/os/Bundle;)V')
                def onEvent(self, eventType, params):
                    pass

            recognizer_holder = {}

            @run_on_ui_thread
            def _start():
                intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
                )
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language)
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)

                listener = _Listener(on_result, on_error, recognizer_holder)
                recognizer = SpeechRecognizer.createSpeechRecognizer(self._activity)
                recognizer.setRecognitionListener(listener)
                recognizer_holder['instance'] = recognizer
                recognizer_holder['listener'] = listener
                recognizer.startListening(intent)

            _start()
        except Exception as exc:
            on_error(f"خطا در راه‌اندازی تشخیص گفتار: {exc}")

    # ------------------------------------------------------------------
    # باز کردن برنامه‌های دیگر (از طریق PackageManager واقعی، نه شل)
    # ------------------------------------------------------------------
    def launch_app_by_package(self, package_name):
        if not self._android:
            return False, "باز کردن برنامه فقط روی اندروید ممکن است."
        try:
            context = self._activity.getApplicationContext()
            pm = context.getPackageManager()
            intent = pm.getLaunchIntentForPackage(package_name)
            if intent is None:
                return False, f"برنامه‌ای با شناسه {package_name} نصب نیست."
            self._activity.startActivity(intent)
            return True, None
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # وای‌فای - از اندروید 10 به بعد، اپ‌های عادی نمی‌توانند مستقیماً
    # وای‌فای را روشن/خاموش کنند؛ باز کردن پنل تنظیمات، رفتار صحیح و مجاز است.
    # ------------------------------------------------------------------
    def is_wifi_enabled(self):
        if not self._android:
            return None
        try:
            Context = self._autoclass('android.content.Context')
            wifi_manager = self._activity.getSystemService(Context.WIFI_SERVICE)
            return bool(wifi_manager.isWifiEnabled())
        except Exception:
            return None

    def open_wifi_settings(self):
        if not self._android:
            return False
        try:
            Intent = self._autoclass('android.content.Intent')
            Settings = self._autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_WIFI_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self._activity.startActivity(intent)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # بلوتوث
    # ------------------------------------------------------------------
    def is_bluetooth_enabled(self):
        if not self._android:
            return None
        try:
            BluetoothAdapter = self._autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            return bool(adapter.isEnabled()) if adapter else None
        except Exception:
            return None

    def open_bluetooth_settings(self):
        if not self._android:
            return False
        try:
            Intent = self._autoclass('android.content.Intent')
            Settings = self._autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self._activity.startActivity(intent)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # روشنایی صفحه (نیاز به مجوز WRITE_SETTINGS)
    # ------------------------------------------------------------------
    def can_write_settings(self):
        if not self._android:
            return False
        try:
            Settings = self._autoclass('android.provider.Settings')
            return bool(Settings.System.canWrite(self._activity))
        except Exception:
            return False

    def open_write_settings_permission_screen(self):
        if not self._android:
            return False
        try:
            Intent = self._autoclass('android.content.Intent')
            Settings = self._autoclass('android.provider.Settings')
            Uri = self._autoclass('android.net.Uri')
            intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
            intent.setData(Uri.parse(f"package:{self._activity.getPackageName()}"))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self._activity.startActivity(intent)
            return True
        except Exception:
            return False

    def set_brightness_percent(self, percent):
        """تنظیم روشنایی (۰ تا ۱۰۰). نیازمند مجوز WRITE_SETTINGS."""
        if not self._android:
            return False, "این قابلیت فقط روی اندروید کار می‌کند."
        if not self.can_write_settings():
            self.open_write_settings_permission_screen()
            return False, "لطفاً ابتدا مجوز تغییر تنظیمات سیستم را برای وینا فعال کنید."
        try:
            Settings = self._autoclass('android.provider.Settings')
            level = max(0, min(255, int(percent * 255 / 100)))
            resolver = self._activity.getContentResolver()
            Settings.System.putInt(resolver, Settings.System.SCREEN_BRIGHTNESS, level)
            return True, None
        except Exception as exc:
            return False, str(exc)

    def get_brightness_percent(self):
        if not self._android:
            return None
        try:
            Settings = self._autoclass('android.provider.Settings')
            resolver = self._activity.getContentResolver()
            level = Settings.System.getInt(resolver, Settings.System.SCREEN_BRIGHTNESS)
            return round(level * 100 / 255)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # آلارم - از طریق Intent واقعی AlarmClock (بدون نیاز به شل یا روت)
    # ------------------------------------------------------------------
    def set_alarm(self, hour, minute, message="یادآوری وینا"):
        if not self._android:
            return False, "تنظیم آلارم فقط روی اندروید ممکن است."
        try:
            Intent = self._autoclass('android.content.Intent')
            AlarmClock = self._autoclass('android.provider.AlarmClock')
            intent = Intent(AlarmClock.ACTION_SET_ALARM)
            intent.putExtra(AlarmClock.EXTRA_HOUR, hour)
            intent.putExtra(AlarmClock.EXTRA_MINUTES, minute)
            intent.putExtra(AlarmClock.EXTRA_MESSAGE, message)
            intent.putExtra(AlarmClock.EXTRA_SKIP_UI, False)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            self._activity.startActivity(intent)
            return True, None
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # باتری - از طریق plyer (کتابخانه‌ی استاندارد و واقعی برای این کار)
    # ------------------------------------------------------------------
    def get_battery_status(self):
        try:
            from plyer import battery
            return battery.status
        except Exception:
            return None

    # ------------------------------------------------------------------
    # اسکرین‌شات از خودِ برنامه (نه کل صفحه؛ اپ‌های عادی بدون مجوز
    # MediaProjection اجازه‌ی گرفتن اسکرین‌شات از کل صفحه را ندارند)
    # ------------------------------------------------------------------
    def take_app_screenshot(self, path):
        try:
            from kivy.core.window import Window
            Window.screenshot(name=path)
            return True, None
        except Exception as exc:
            return False, str(exc)
