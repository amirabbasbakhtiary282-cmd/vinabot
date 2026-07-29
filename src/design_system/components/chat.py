# -*- coding: utf-8 -*-
"""
کامپوننت‌های اختصاصی چت سیستم طراحی وینا

- Avatar: آواتار دایره‌ای کاربر/وینا
- CodeBlock: بلوک کد با هایلایت نحو واقعی (pygments) و دکمه‌ی کپی
- ChatBubble: حباب چت با Markdown، بلوک کد، انیمیشن ظاهر شدن و دکمه‌های عملیات
- TypingIndicator / ThinkingAnimation: نشانگرهای «در حال نوشتن/فکر کردن»
- MessageActions: نوار دکمه‌های عملیات زیر یک پیام (کپی/ویرایش/حذف/بازتولید/اشتراک)
- ConversationCard: کارت یک مکالمه در لیست مکالمات (صفحه‌ی خانه)
"""

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, RoundedRectangle, BoxShadow

from src.design_system.base import ThemedWidgetMixin, theme, rgba_to_hex
from src.design_system.components.cards import GlassCard
from src.markdown_render import (
    parse_message_segments, highlight_code, markdown_text_to_kivy_markup,
)


class Avatar(Widget, ThemedWidgetMixin):
    """آواتار دایره‌ای کوچک برای کاربر یا وینا"""

    is_user = BooleanProperty(True)
    letter = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._bg_color = Color(*self._resolve_color())
            self._ellipse = Ellipse(pos=self.pos, size=self.size)
        self._label = Label(
            text=self.letter or ('●' if self.is_user else '◈'),
            font_name=theme.font_name, bold=True,
            color=theme.text_on_accent if self.is_user else theme.text_primary,
        )
        self.add_widget(self._label)
        self.bind(pos=self._redraw, size=self._redraw, is_user=self._redraw)
        self.bind_theme()

    def _resolve_color(self):
        return theme.accent if self.is_user else theme.bg_surface_alt

    def on_theme_changed(self):
        self._redraw()

    def _redraw(self, *args):
        self._bg_color.rgba = self._resolve_color()
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size
        self._label.pos = self.pos
        self._label.size = self.size
        self._label.color = theme.text_on_accent if self.is_user else theme.text_primary
        self._label.text = self.letter or ('●' if self.is_user else '◈')


class CodeBlock(BoxLayout, ThemedWidgetMixin):
    """بلوک کد با پس‌زمینه‌ی تیره، هایلایت نحو واقعی (pygments) و دکمه‌ی کپی"""

    language = StringProperty('')
    code = StringProperty('')
    on_copy = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.spacing = 0

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30),
                            padding=[dp(10), 0, dp(6), 0])
        with header.canvas.before:
            self._header_color = Color(*self._header_bg())
            self._header_rect = RoundedRectangle(
                pos=header.pos, size=header.size, radius=[dp(10), dp(10), 0, 0],
            )
        header.bind(pos=self._update_header, size=self._update_header)

        self._lang_label = Label(
            text=self.language or 'code', font_name=theme.font_name,
            font_size='11sp', color=theme.text_secondary, halign='left',
            size_hint_x=0.7,
        )
        header.add_widget(self._lang_label)

        self._copy_btn = Button(
            text='⧉', size_hint_x=0.3, background_normal='', background_down='',
            background_color=(0, 0, 0, 0), color=theme.text_secondary, font_size='14sp',
        )
        self._copy_btn.bind(on_release=self._do_copy)
        header.add_widget(self._copy_btn)
        self.add_widget(header)

        body = BoxLayout(orientation='vertical', padding=[dp(12), dp(8), dp(12), dp(10)],
                          size_hint_y=None)
        with body.canvas.before:
            self._body_color = Color(*self._body_bg())
            self._body_rect = RoundedRectangle(
                pos=body.pos, size=body.size, radius=[0, 0, dp(10), dp(10)],
            )
        body.bind(pos=self._update_body, size=self._update_body)

        self._code_label = Label(
            markup=True, font_name=theme.font_name,
            font_size='12.5sp', halign='left', valign='top',
            size_hint_y=None, color=theme.text_primary,
        )
        self._code_label.bind(texture_size=self._update_code_label_size)
        self._code_label.bind(width=lambda *a: setattr(
            self._code_label, 'text_size', (self._code_label.width, None)))
        body.add_widget(self._code_label)
        self._body = body
        self.add_widget(body)

        self.height = dp(30) + dp(60)
        self.bind(code=self._refresh_code, language=self._refresh_code)
        self._refresh_code()
        self.bind_theme()

    def _header_bg(self):
        return theme.bg_elevated

    def _body_bg(self):
        return (0, 0, 0, 0.25) if theme.is_dark else (0, 0, 0, 0.04)

    def on_theme_changed(self):
        self._header_color.rgba = self._header_bg()
        self._body_color.rgba = self._body_bg()
        self._lang_label.color = theme.text_secondary
        self._copy_btn.color = theme.text_secondary
        self._code_label.color = theme.text_primary
        self._refresh_code()

    def _update_header(self, instance, *args):
        self._header_rect.pos = instance.pos
        self._header_rect.size = instance.size

    def _update_body(self, instance, *args):
        self._body_rect.pos = instance.pos
        self._body_rect.size = instance.size

    def _update_code_label_size(self, instance, value):
        instance.height = value[1]
        self._body.height = instance.height + self._body.padding[1] + self._body.padding[3]
        self.height = dp(30) + self._body.height

    def _refresh_code(self, *args):
        self._lang_label.text = self.language or 'code'
        accent_hex = rgba_to_hex(theme.accent)
        self._code_label.text = highlight_code(self.code, self.language, accent_hex)
        Clock.schedule_once(lambda dt: setattr(
            self._code_label, 'text_size', (self._code_label.width, None)), 0)

    def _do_copy(self, *args):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.code)
        except Exception:
            pass
        if callable(self.on_copy):
            self.on_copy(self.code)


class MessageActions(BoxLayout):
    """نوار دکمه‌های عملیات زیر یک پیام: کپی، ویرایش، حذف، بازتولید، اشتراک"""

    def __init__(self, is_user=True, on_copy=None, on_edit=None, on_delete=None,
                 on_regenerate=None, on_share=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(28))
        kwargs.setdefault('spacing', dp(4))
        super().__init__(**kwargs)

        actions = [('⧉', on_copy)]
        if is_user:
            actions.append(('✎', on_edit))
        else:
            actions.append(('↻', on_regenerate))
        actions.append(('↗', on_share))
        actions.append(('🗑', on_delete))

        for icon, callback in actions:
            btn = Button(
                text=icon, font_size='12sp', size_hint_x=None, width=dp(28),
                background_normal='', background_down='', background_color=(0, 0, 0, 0),
                color=theme.text_disabled,
            )
            if callable(callback):
                btn.bind(on_release=lambda inst, cb=callback: cb())
            self.add_widget(btn)


class TypingIndicator(BoxLayout, ThemedWidgetMixin):
    """نشانگر انیمیشنی «وینا در حال نوشتن است...» با سه نقطه‌ی پالسی"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = 6
        self.size_hint = (None, None)
        self.size = (52, 24)
        self._dots = []

        for i in range(3):
            dot = Widget(size_hint=(None, None), size=(8, 8))
            with dot.canvas:
                dot._color = Color(*theme.text_secondary[:3], 0.9)
                dot._ellipse = Ellipse(pos=dot.pos, size=dot.size)
            dot.bind(pos=self._make_updater(dot), size=self._make_updater(dot))
            self._dots.append(dot)
            self.add_widget(dot)

        Clock.schedule_once(lambda dt: self._start_animation(), 0)
        self.bind_theme()

    def on_theme_changed(self):
        for dot in self._dots:
            dot._color.rgba = (*theme.text_secondary[:3], 0.9)

    def _make_updater(self, dot):
        def _update(*args):
            dot._ellipse.pos = dot.pos
            dot._ellipse.size = dot.size
        return _update

    def _start_animation(self):
        dur = theme.get_anim_duration(0.3)
        for i, dot in enumerate(self._dots):
            anim = (
                Animation(size=(11, 11), duration=dur, t='out_sine')
                + Animation(size=(8, 8), duration=dur, t='in_sine')
            )
            anim.repeat = True
            Clock.schedule_once(lambda dt, a=anim, d=dot: a.start(d), i * 0.15)

    def stop(self):
        for dot in self._dots:
            Animation.cancel_all(dot)


# نام مستعار: «انیمیشن فکر کردن» همان TypingIndicator با معنای مفهومی متفاوت است
ThinkingAnimation = TypingIndicator


class ChatBubble(BoxLayout, ThemedWidgetMixin):
    """حباب چت با پشتیبانی از Markdown، بلوک کد، انیمیشن ظاهر شدن و دکمه‌های عملیات"""

    is_user = BooleanProperty(True)
    timestamp = StringProperty('')
    raw_text = StringProperty('')

    def __init__(self, message='', is_user=True, time_str='', on_regenerate=None,
                 on_delete=None, on_edit=None, on_share=None, show_actions=False, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.spacing = dp(8)
        self.padding = [dp(4), dp(2), dp(4), dp(2)]

        self.is_user = is_user
        self.timestamp = time_str
        self.raw_text = message
        self._on_regenerate = on_regenerate
        self._on_delete = on_delete
        self._on_edit = on_edit
        self._on_share = on_share

        row = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None)
        row.bind(minimum_height=row.setter('height'))

        avatar = Avatar(is_user=is_user, size_hint=(None, None), size=(dp(30), dp(30)))
        avatar.opacity = 1 if theme.show_avatars else 0

        bubble_col = BoxLayout(
            orientation='vertical', size_hint_x=theme.chat_width_scale * 0.78,
            padding=[dp(14), dp(10), dp(14), dp(8)], spacing=dp(6), size_hint_y=None,
        )
        with bubble_col.canvas.before:
            self._shadow_color = Color(0, 0, 0, 0.22)
            self._shadow = BoxShadow(
                pos=bubble_col.pos, size=bubble_col.size,
                offset=(0, -2), blur_radius=14, spread_radius=(-4, -4),
                border_radius=(dp(16),) * 4,
            )
            self._bg_color_instr = Color(*self._resolve_bubble_color())
            self._bg_rect = RoundedRectangle(
                pos=bubble_col.pos, size=bubble_col.size, radius=self._corner_radii(),
            )
        bubble_col.bind(pos=self._update_bg, size=self._update_bg)
        self._bubble_col = bubble_col

        self._content_widgets = []
        self._build_content()

        self._time_label = Label(
            text=time_str, color=theme.text_disabled, font_name=theme.font_name,
            font_size='10sp', halign='right' if is_user else 'left', valign='top',
            size_hint_y=None, height=dp(14),
        )
        bubble_col.add_widget(self._time_label)

        spacer = Widget(size_hint_x=1 - theme.chat_width_scale * 0.78 - 0.12)

        if is_user:
            row.add_widget(spacer)
            row.add_widget(bubble_col)
            if theme.show_avatars:
                row.add_widget(avatar)
        else:
            if theme.show_avatars:
                row.add_widget(avatar)
            row.add_widget(bubble_col)
            row.add_widget(spacer)

        self.add_widget(row)
        self._row = row
        self.bind(minimum_height=self.setter('height'))
        row.bind(height=lambda *a: setattr(self, 'height', row.height))

        if show_actions:
            actions = MessageActions(
                is_user=is_user,
                on_copy=self._copy_text,
                on_edit=self._on_edit,
                on_delete=self._on_delete,
                on_regenerate=self._on_regenerate,
                on_share=self._on_share,
            )
            self.add_widget(actions)

        self.bind_theme()
        self._animate_in()

    def _animate_in(self):
        from src.design_system.animations import slide_in_up
        slide_in_up(self, distance=dp(12))

    def _copy_text(self):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.raw_text)
        except Exception:
            pass

    def _resolve_bubble_color(self):
        return theme.bubble_user if self.is_user else theme.bubble_bot

    def _resolve_text_color(self):
        return theme.bubble_user_text if self.is_user else theme.bubble_bot_text

    def _corner_radii(self):
        r = dp(16) * theme.corner_radius_scale
        small = dp(4)
        if self.is_user:
            return [r, r, small, r]
        return [r, r, r, small]

    def _build_content(self):
        for w in self._content_widgets:
            self._bubble_col.remove_widget(w)
        self._content_widgets = []

        segments = parse_message_segments(self.raw_text)
        for seg in segments:
            if seg['type'] == 'code':
                block = CodeBlock(language=seg.get('language', ''), code=seg['content'],
                                   size_hint_y=None)
                self._bubble_col.add_widget(block, index=len(self._content_widgets))
                self._content_widgets.append(block)
            else:
                content = seg['content'].strip('\n')
                if not content:
                    continue
                label = Label(
                    text=markdown_text_to_kivy_markup(content),
                    markup=True,
                    color=self._resolve_text_color(),
                    font_size='14.5sp',
                    font_name=theme.font_name,
                    halign='right' if self.is_user else 'left',
                    valign='top',
                    size_hint_y=None,
                )
                label.bind(texture_size=self._make_label_updater(label))
                label.bind(width=lambda inst, *a: setattr(
                    inst, 'text_size', (inst.width, None)))
                self._bubble_col.add_widget(label, index=len(self._content_widgets))
                self._content_widgets.append(label)
                Clock.schedule_once(lambda dt, lbl=label: setattr(
                    lbl, 'text_size', (lbl.width, None)), 0)

    def _make_label_updater(self, label):
        def _update(instance, value):
            instance.height = value[1]
            self._recalc_height()
        return _update

    def _recalc_height(self):
        total = self._bubble_col.padding[1] + self._bubble_col.padding[3]
        total += self._bubble_col.spacing * max(0, len(self._content_widgets))
        for w in self._content_widgets:
            total += w.height
        total += self._time_label.height + self._bubble_col.spacing
        self._bubble_col.height = total

    def _update_bg(self, *args):
        self._shadow.pos = (self._bubble_col.x, self._bubble_col.y - 1)
        self._shadow.size = self._bubble_col.size
        self._bg_rect.pos = self._bubble_col.pos
        self._bg_rect.size = self._bubble_col.size

    def on_theme_changed(self):
        self._bg_color_instr.rgba = self._resolve_bubble_color()
        self._bg_rect.radius = self._corner_radii()
        self._time_label.color = theme.text_disabled
        self._build_content()
        self._recalc_height()

    def set_text(self, new_text):
        self.raw_text = new_text
        self._build_content()
        self._recalc_height()

    def start_typing_animation(self, full_text=None):
        """شروع انیمیشن تایپ تدریجی متن (شبیه‌سازی استریم پاسخ)"""
        self._full_text = full_text if full_text is not None else self.raw_text
        self._char_index = 0
        self.set_text('')
        interval = max(0.008, 0.02 * theme.animation_speed_scale)
        Clock.schedule_interval(lambda dt: self._type_next_char(dt), interval)

    def _type_next_char(self, dt):
        if self._char_index < len(self._full_text):
            step = max(1, len(self._full_text) // 200)
            self._char_index = min(len(self._full_text), self._char_index + step)
            self.set_text(self._full_text[:self._char_index])
            return True
        return False


class ConversationCard(GlassCard):
    """کارت یک مکالمه در لیست مکالمات اخیر/سنجاق‌شده (صفحه‌ی خانه)"""

    title_text = StringProperty('')
    preview_text = StringProperty('')
    time_text = StringProperty('')
    is_pinned = BooleanProperty(False)

    def __init__(self, on_release=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(68))
        kwargs.setdefault('padding', [dp(14), dp(10), dp(14), dp(10)])
        kwargs.setdefault('spacing', dp(10))
        kwargs.setdefault('radius', 16)
        super().__init__(**kwargs)

        text_col = BoxLayout(orientation='vertical', spacing=dp(3))
        header_row = BoxLayout(orientation='horizontal', size_hint_y=0.5)

        self._title_label = Label(
            text=self.title_text, font_name=theme.font_name, bold=True,
            font_size='13.5sp', color=theme.text_primary, halign='right',
        )
        self._title_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        header_row.add_widget(self._title_label)

        if self.is_pinned:
            header_row.add_widget(Label(text='📌', font_size='11sp', size_hint_x=None, width=dp(18)))

        text_col.add_widget(header_row)

        self._preview_label = Label(
            text=self.preview_text, font_name=theme.font_name, font_size='11.5sp',
            color=theme.text_secondary, halign='right', size_hint_y=0.5,
        )
        self._preview_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(self._preview_label)

        self.add_widget(text_col)

        self._time_label = Label(
            text=self.time_text, font_name=theme.font_name, font_size='10sp',
            color=theme.text_disabled, size_hint_x=None, width=dp(46),
        )
        self.add_widget(self._time_label)

        if on_release:
            self.bind(on_touch_up=lambda inst, touch: (
                on_release() if self.collide_point(*touch.pos) else None
            ))

    def on_theme_changed(self):
        super().on_theme_changed()
        self._title_label.color = theme.text_primary
        self._preview_label.color = theme.text_secondary
        self._time_label.color = theme.text_disabled
