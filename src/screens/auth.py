# -*- coding: utf-8 -*-
"""
صفحات ورودی (Onboarding و Login) - همچنان KV-driven چون ساختار بصری
ثابت و ساده‌ای دارند.
"""

from kivy.app import App
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen, SlideTransition

from src.text_utils import fix_rtl

ONBOARDING_PAGES = [
    {
        'subtitle': fix_rtl(
            'وینا دستیار هوش مصنوعی شخصی شماست که به‌طور کامل و آفلاین '
            'روی گوشی شما اجرا می‌شود.'
        ),
        'button': fix_rtl('بعدی'),
    },
    {
        'subtitle': fix_rtl(
            'تمام مکالمات، یادداشت‌ها و اطلاعات شما فقط روی دستگاه خودتان '
            'ذخیره می‌شود؛ چیزی به سرور خارجی ارسال نمی‌شود.'
        ),
        'button': fix_rtl('بعدی'),
    },
    {
        'subtitle': fix_rtl(
            'برای فعال‌سازی پاسخ‌های هوشمند، از تنظیمات یک مدل زبانی سبک '
            'دانلود کنید یا فایل GGUF دلخواه خود را در پوشه‌ی models قرار دهید.'
        ),
        'button': fix_rtl('شروع کنیم'),
    },
]


class OnboardingScreen(Screen):
    """صفحه‌ی خوشامدگویی که فقط بار اول نصب نمایش داده می‌شود"""

    page_index = NumericProperty(0)
    subtitle_text = StringProperty(ONBOARDING_PAGES[0]['subtitle'])
    button_text = StringProperty(ONBOARDING_PAGES[0]['button'])

    def next_page(self):
        if self.page_index < len(ONBOARDING_PAGES) - 1:
            self.page_index += 1
            self.subtitle_text = ONBOARDING_PAGES[self.page_index]['subtitle']
            self.button_text = ONBOARDING_PAGES[self.page_index]['button']
        else:
            app = App.get_running_app()
            app.memory.set_flag('onboarding_seen', '1')
            app.sm.transition = SlideTransition(direction='left')
            app.sm.current = 'login'


class LoginScreen(Screen):
    """صفحه ورود اختصاصی"""

    status_text = StringProperty("")
    tagline = StringProperty(fix_rtl("دستیار هوش مصنوعی شخصی شما"))
    username_hint = StringProperty(fix_rtl("نام کاربری"))
    password_hint = StringProperty(fix_rtl("رمز عبور"))
    login_button_text = StringProperty(fix_rtl("ورود"))

    def do_login(self):
        app = App.get_running_app()
        username = self.ids.username_input.text.strip()
        password = self.ids.password_input.text
        success, message = app.do_login(username, password)
        self.status_text = fix_rtl(message)
        if success:
            self.ids.username_input.text = ""
            self.ids.password_input.text = ""
