# -*- coding: utf-8 -*-
"""
وینا - دستیار هوش مصنوعی شخصی
فایل اصلی برنامه - نقطه ورود
"""

import os
import sys
import threading
import time
from datetime import datetime

os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition, WipeTransition
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.animation import Animation

Window.size = (400, 750)
Window.clearcolor = (0, 0.04, 0, 1)

from src.brain import VinaBrain
from src.memory import VinaMemory
from src.voice import VinaVoice
from src.search import VinaSearch
from src.system_control import VinaSystemControl


class LoginScreen(Screen):
    """صفحه ورود اختصاصی"""
    pass


class ChatScreen(Screen):
    """صفحه اصلی چت"""
    pass


class SettingsScreen(Screen):
    """صفحه تنظیمات"""
    pass


class VinaApp(App):
    app_title = "Vina AI"
    current_user = StringProperty("")
    chat_history = ListProperty([])
    is_listening = BooleanProperty(False)
    is_speaking = BooleanProperty(False)
    wake_word_active = BooleanProperty(True)
    voice_enabled = BooleanProperty(True)
    model_status = StringProperty("در حال بارگذاری...")
    current_hour = NumericProperty(datetime.now().hour)

    def build(self):
        self.memory = VinaMemory()
        self.brain = VinaBrain(self.memory)
        self.voice = VinaVoice()
        self.search = VinaSearch()
        self.system_ctrl = VinaSystemControl()

        self.sm = ScreenManager()
        self.sm.transition = FadeTransition(duration=0.5)
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(ChatScreen(name='chat'))
        self.sm.add_widget(SettingsScreen(name='settings'))

        Clock.schedule_interval(self._check_night_mode, 300)
        Clock.schedule_interval(self._check_reminders, 60)

        Clock.schedule_once(lambda dt: self._init_models(), 1)

        return self.sm

    def _init_models(self):
        """بارگذاری مدل‌ها در پس‌زمینه"""
        try:
            Clock.schedule_once(lambda dt: setattr(self, 'model_status', 'در حال بارگذاری مدل زبانی...'), 0)
            self.brain.load_model()
            Clock.schedule_once(lambda dt: setattr(self, 'model_status', 'آماده'), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self, 'model_status', f'خطا: {str(e)[:50]}'), 0)

    def _check_night_mode(self, dt):
        """بررسی حالت شب بر اساس ساعت"""
        hour = datetime.now().hour
        self.current_hour = hour

    def _check_reminders(self, dt):
        """بررسی یادآوری‌ها"""
        try:
            reminders = self.memory.get_pending_reminders()
            now = datetime.now()
            for reminder in reminders:
                reminder_time = datetime.strptime(reminder['time'], '%Y-%m-%d %H:%M')
                if reminder_time <= now:
                    self._show_reminder(reminder)
                    self.memory.mark_reminder_done(reminder['id'])
        except Exception:
            pass

    def _show_reminder(self, reminder):
        """نمایش یادآوری"""
        Clock.schedule_once(lambda dt: self._popup_reminder(reminder['message']), 0)

    def _popup_reminder(self, message):
        """پاپ‌آپ یادآوری"""
        try:
            content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            content.add_widget(Label(
                text=f'[color=00FF41][size=18]یادآوری[/size][/color]\n\n{message}',
                markup=True,
                color=(0.69, 1, 0.69, 1),
                size_hint_y=0.8
            ))
            btn = Button(
                text='متوجه شدم',
                size_hint_y=0.2,
                background_color=(0, 0.23, 0, 1),
                color=(0, 1, 0.25, 1),
                font_size=16
            )
            content.add_widget(btn)
            popup = Popup(title='', content=content, size_hint=(0.8, 0.4), auto_dismiss=False)
            btn.bind(on_press=popup.dismiss)
            popup.open()
        except Exception:
            pass

    def do_login(self, username, password):
        """انجام عملیات ورود"""
        if not username or not password:
            return False, "نام کاربری و رمز عبور را وارد کنید"

        success = self.memory.verify_user(username, password)
        if success:
            self.current_user = username
            self.memory.set_current_user(username)
            Clock.schedule_once(lambda dt: self._switch_to_chat(), 0)
            return True, "ورود موفق"
        else:
            exists = self.memory.user_exists(username)
            if exists:
                return False, "رمز عبور اشتباه است"
            else:
                self.memory.create_user(username, password)
                self.current_user = username
                self.memory.set_current_user(username)
                Clock.schedule_once(lambda dt: self._switch_to_chat(), 0)
                return True, "حساب کاربری جدید ایجاد شد"

    def _switch_to_chat(self):
        """رفتن به صفحه چت"""
        self.sm.current = 'chat'
        if self.wake_word_active:
            self._start_wake_word_listener()

    def send_message(self, text):
        """ارسال پیام کاربر و دریافت پاسخ"""
        if not text.strip():
            return

        self.chat_history.append({
            'role': 'user',
            'text': text,
            'time': datetime.now().strftime('%H:%M')
        })

        threading.Thread(target=self._process_message, args=(text,), daemon=True).start()

    def _process_message(self, text):
        """پردازش پیام در پس‌زمینه"""
        try:
            self.memory.save_conversation('user', text)
            response = self._get_response(text)
            self.memory.save_conversation('vina', response)

            self.memory.analyze_and_store_preferences(text)

            Clock.schedule_once(lambda dt: self._add_bot_message(response), 0)

            if self.voice_enabled:
                self._speak_response(response)
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._add_bot_message(f'خطا در پردازش: {str(e)[:100]}'), 0
            )

    def _get_response(self, text):
        """دریافت پاسخ از موتورهای مختلف"""
        text_lower = text.strip()

        system_result = self.system_ctrl.handle_command(text_lower)
        if system_result:
            return system_result

        search_triggers = ['جستجو', 'سرچ', 'اینترنت', 'گوگل', 'بدون', 'قیمت', 'آب و هوا', 'خبر', 'اخبار']
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
        return self.brain.generate_response(text, context)

    def _extract_search_query(self, text):
        """استخراج عبارت جستجو"""
        prefixes = ['جستجو کن', 'سرچ کن', 'از اینترنت بگرد', 'در اینترنت پیدا کن',
                     'بدون', 'قیمت', 'آب و هوا', 'خبر', 'اخبار']
        for prefix in prefixes:
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                query = text[idx:].strip()
                if query:
                    return query
        return text

    def _handle_reminder(self, text):
        """مدیریت یادآوری‌ها"""
        reminder_keywords = ['یادم باشد', 'یادت باشد', 'یادآوری کن', 'یادآور کن', 'یادداشت کن']
        for kw in reminder_keywords:
            if kw in text:
                idx = text.index(kw) + len(kw)
                message = text[idx:].strip()
                if message:
                    self.memory.add_reminder(message)
                    return f"حتماً یادآوری می‌کنم: {message}"
        return None

    def _handle_notes(self, text):
        """مدیریت یادداشت‌ها"""
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
        """گویش پاسخ"""
        Clock.schedule_once(lambda dt: setattr(self, 'is_speaking', True), 0)
        self.voice.speak(text)
        Clock.schedule_once(lambda dt: setattr(self, 'is_speaking', False), 0)

    def _add_bot_message(self, text):
        """افزودن پیام ربات به تاریخچه"""
        self.chat_history.append({
            'role': 'vina',
            'text': text,
            'time': datetime.now().strftime('%H:%M')
        })

    def start_listening(self):
        """شروع گوش دادن"""
        self.is_listening = True
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        """thread گوش دادن"""
        try:
            text = self.voice.listen()
            if text:
                Clock.schedule_once(lambda dt: self.send_message(text), 0)
        except Exception as e:
            print(f"خطای تشخیص صدا: {e}")
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'is_listening', False), 0)

    def _start_wake_word_listener(self):
        """شروع گوش دادن به کلمه فعال‌سازی"""
        threading.Thread(target=self._wake_word_thread, daemon=True).start()

    def _wake_word_thread(self):
        """thread کلمه فعال‌سازی"""
        while self.wake_word_active:
            try:
                detected = self.voice.listen_for_wake_word("هی وینا")
                if detected:
                    Clock.schedule_once(lambda dt: self._on_wake_word(), 0)
            except Exception:
                time.sleep(1)

    def _on_wake_word(self):
        """عملیات پس از تشخیص کلمه فعال‌سازی"""
        self.voice.speak("بله قربان")
        self.start_listening()

    def toggle_voice(self):
        """تغییر وضعیت صدا"""
        self.voice_enabled = not getattr(self, 'voice_enabled', True)

    def get_personality_context(self):
        """دریافت زمینه شخصیت وینا"""
        return self.memory.get_personality()


if __name__ == '__main__':
    VinaApp().run()
