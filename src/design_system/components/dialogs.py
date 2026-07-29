# -*- coding: utf-8 -*-
"""
کامپوننت‌های دیالوگ سیستم طراحی وینا

- ModernDialog: دیالوگ پایه‌ی گرد و شیشه‌ای وسط صفحه
- ConfirmationDialog: دیالوگ تایید/لغو (برای عملیات مخرب مثل پاک کردن حافظه)
- BottomSheet: پنل مودال که از پایین صفحه بالا می‌آید (منوی انتخاب تم و...)
- ActionSheet: لیست گزینه‌های قابل‌کلیک درون BottomSheet
"""

from kivy.animation import Animation
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget

from src.design_system.base import theme
from src.design_system.components.buttons import PrimaryButton, SecondaryButton, DangerButton
from src.design_system.components.cards import GlassCard


class ModernDialog(ModalView):
    """دیالوگ پایه‌ی گرد و شیشه‌ای، وسط صفحه با انیمیشن بزرگ‌شدن ملایم"""

    def __init__(self, title='', message='', **kwargs):
        kwargs.setdefault('size_hint', (0.86, None))
        kwargs.setdefault('background_color', (0, 0, 0, 0.6))
        kwargs.setdefault('background', '')
        kwargs.setdefault('auto_dismiss', True)
        super().__init__(**kwargs)

        card = GlassCard(orientation='vertical', radius=22, surface='elevated',
                          padding=[dp(20), dp(20), dp(20), dp(16)], spacing=dp(14),
                          size_hint_y=None)
        self._card = card

        if title:
            title_label = Label(
                text=title, font_name=theme.font_name, bold=True, font_size='17sp',
                color=theme.text_primary, size_hint_y=None, height=dp(28),
            )
            card.add_widget(title_label)
            self._title_label = title_label
        else:
            self._title_label = None

        if message:
            msg_label = Label(
                text=message, font_name=theme.font_name, font_size='13.5sp',
                color=theme.text_secondary, size_hint_y=None,
                halign='right', valign='top',
            )
            msg_label.bind(width=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
            msg_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            card.add_widget(msg_label)
            self._msg_label = msg_label
        else:
            self._msg_label = None

        self._button_row = BoxLayout(orientation='horizontal', spacing=dp(10),
                                      size_hint_y=None, height=dp(48))
        card.add_widget(self._button_row)

        card.bind(minimum_height=lambda inst, val: setattr(card, 'height', val))
        self.add_widget(card)
        self.height = dp(220)

    def add_button(self, widget):
        self._button_row.add_widget(widget)

    def open(self, *args, **kwargs):
        super().open(*args, **kwargs)
        self._card.opacity = 0
        Animation(opacity=1, duration=theme.get_anim_duration(theme.anim_normal)).start(self._card)


class ConfirmationDialog(ModernDialog):
    """دیالوگ تایید/لغو استاندارد - برای اقدامات حساس (پاک کردن حافظه، حذف مدل و...)"""

    def __init__(self, title='', message='', confirm_text='تایید', cancel_text='لغو',
                 on_confirm=None, danger=False, **kwargs):
        super().__init__(title=title, message=message, **kwargs)

        cancel_btn = SecondaryButton(text=cancel_text)
        cancel_btn.bind(on_release=lambda *a: self.dismiss())
        self.add_button(cancel_btn)

        confirm_cls = DangerButton if danger else PrimaryButton
        confirm_btn = confirm_cls(text=confirm_text)

        def _on_confirm_press(*a):
            self.dismiss()
            if callable(on_confirm):
                on_confirm()

        confirm_btn.bind(on_release=_on_confirm_press)
        self.add_button(confirm_btn)


class BottomSheet(ModalView):
    """پنل مودالی که از پایین صفحه بالا می‌آید (سبک متریال مدرن)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (1, None))
        kwargs.setdefault('background_color', (0, 0, 0, 0.55))
        kwargs.setdefault('background', '')
        super().__init__(**kwargs)
        self.pos_hint = {'x': 0, 'y': 0}

    def open(self, *args, **kwargs):
        super().open(*args, **kwargs)
        self.y = -self.height
        Animation(y=0, duration=theme.get_anim_duration(theme.anim_normal),
                  t='out_cubic').start(self)

    def dismiss(self, *args, **kwargs):
        anim = Animation(y=-self.height, duration=theme.get_anim_duration(theme.anim_fast),
                          t='in_cubic')
        anim.bind(on_complete=lambda *a: super(BottomSheet, self).dismiss(*args, **kwargs))
        anim.start(self)


class ActionSheetItem(BoxLayout):
    """یک ردیف قابل‌کلیک درون ActionSheet"""

    def __init__(self, text='', icon='', on_release=None, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(52))
        kwargs.setdefault('padding', [dp(16), dp(8), dp(16), dp(8)])
        kwargs.setdefault('spacing', dp(12))
        super().__init__(**kwargs)

        if icon:
            self.add_widget(Label(text=icon, font_size='18sp', color=theme.accent,
                                   size_hint_x=None, width=dp(26)))
        label = Label(text=text, font_name=theme.font_name, font_size='14sp',
                      color=theme.text_primary, halign='right')
        label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        self.add_widget(label)

        if on_release:
            self.bind(on_touch_up=lambda inst, touch: (
                on_release() if self.collide_point(*touch.pos) else None
            ))


class ActionSheet(BottomSheet):
    """BottomSheet با لیست گزینه‌های قابل‌کلیک (مثلاً: کپی/ویرایش/حذف/بازتولید پیام)"""

    def __init__(self, title='', items=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None

        card = GlassCard(orientation='vertical', radius=22, surface='elevated',
                          padding=[dp(8), dp(12), dp(8), dp(20)], spacing=dp(4),
                          size_hint_y=None)

        handle = Widget(size_hint=(None, None), size=(dp(36), dp(4)),
                         pos_hint={'center_x': 0.5})
        card.add_widget(handle)

        if title:
            card.add_widget(Label(
                text=title, font_name=theme.font_name, bold=True, font_size='14sp',
                color=theme.text_secondary, size_hint_y=None, height=dp(32),
            ))

        for item in (items or []):
            card.add_widget(ActionSheetItem(
                text=item.get('text', ''), icon=item.get('icon', ''),
                on_release=self._wrap_action(item.get('on_release')),
            ))

        card.bind(minimum_height=lambda inst, val: setattr(card, 'height', val))
        self.add_widget(card)
        self.height = dp(80 + 52 * len(items or []) + (32 if title else 0))

    def _wrap_action(self, callback):
        def _wrapped():
            self.dismiss()
            if callable(callback):
                callback()
        return _wrapped
