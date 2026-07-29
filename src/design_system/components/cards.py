# -*- coding: utf-8 -*-
"""
کامپوننت‌های کارت (Card) سیستم طراحی وینا

- GlassCard: کارت پایه‌ی شیشه‌ای گرد با سایه (زیربنای بقیه‌ی کارت‌ها)
- SettingsCard: ردیف تنظیمات با آیکون/عنوان/توضیح/کنترل سمت راست
- FeatureCard: کارت اکشن سریع (صفحه‌ی خانه)
- ModelCard: کارت نمایش وضعیت مدل هوش مصنوعی
- MemoryCard / StatisticsCard: کارت‌های آماری
"""

from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, OptionProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle, BoxShadow

from src.design_system.base import ThemedWidgetMixin, theme
from src.design_system.tokens import IconSize


class GlassCard(BoxLayout, ThemedWidgetMixin):
    """کارت گرد با پس‌زمینه‌ی نیمه‌شفاف، حاشیه‌ی ظریف و سایه‌ی نرم"""

    radius = NumericProperty(16)
    surface = OptionProperty('surface', options=['surface', 'surface_alt', 'elevated'])
    bg_color = ListProperty([0, 0, 0, 0])
    border_color = ListProperty([0, 0, 0, 0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._shadow_color = Color(*theme.shadow)
            self._shadow = BoxShadow(
                pos=self.pos, size=self.size,
                offset=(0, -4), blur_radius=24, spread_radius=(-2, -2),
                border_radius=(self.radius,) * 4,
            )
            self._bg_color_instr = Color(*self._resolve_bg())
            self._bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
            self._border_color_instr = Color(*self._resolve_border())
            self._border_line = Line(
                rounded_rectangle=(*self.pos, *self.size, self.radius),
                width=1.1,
            )
        self.bind(pos=self._redraw, size=self._redraw,
                  radius=self._redraw, bg_color=self._redraw,
                  border_color=self._redraw, surface=self._redraw)
        self.bind_theme()

    def _resolve_bg(self):
        if any(self.bg_color):
            return self.bg_color
        return {
            'surface': theme.bg_surface,
            'surface_alt': theme.bg_surface_alt,
            'elevated': theme.bg_elevated,
        }[self.surface]

    def _resolve_border(self):
        return self.border_color if any(self.border_color) else theme.glass_border

    def on_theme_changed(self):
        self._redraw()

    def _redraw(self, *args):
        self._shadow_color.rgba = theme.shadow
        self._shadow.pos = (self.x, self.y - 2)
        self._shadow.size = self.size
        self._shadow.border_radius = (self.radius,) * 4
        self._bg_color_instr.rgba = self._resolve_bg()
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [self.radius]
        self._border_color_instr.rgba = self._resolve_border()
        self._border_line.rounded_rectangle = (*self.pos, *self.size, self.radius)


class SettingsCard(GlassCard):
    """ردیف استاندارد یک گزینه‌ی تنظیمات: آیکون + عنوان + توضیح + مقدار/کنترل + فلش"""

    icon = StringProperty('')
    title_text = StringProperty('')
    description_text = StringProperty('')
    value_text = StringProperty('')
    show_arrow = OptionProperty(False, options=[True, False])

    def __init__(self, control=None, on_release=None, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(64))
        kwargs.setdefault('padding', [dp(16), dp(10), dp(16), dp(10)])
        kwargs.setdefault('spacing', dp(12))
        kwargs.setdefault('radius', 16)
        super().__init__(**kwargs)

        if self.icon:
            icon_label = Label(
                text=self.icon, font_size=f'{IconSize.MD}sp',
                size_hint_x=None, width=dp(30), color=theme.accent,
            )
            self.add_widget(icon_label)
            self._icon_label = icon_label
        else:
            self._icon_label = None

        text_col = BoxLayout(orientation='vertical', spacing=dp(2))
        self._title_label = Label(
            text=self.title_text, font_name=theme.font_name, bold=True,
            font_size='14.5sp', color=theme.text_primary,
            halign='right', valign='middle', size_hint_y=0.55,
        )
        self._title_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(self._title_label)

        if self.description_text:
            self._desc_label = Label(
                text=self.description_text, font_name=theme.font_name,
                font_size='11.5sp', color=theme.text_secondary,
                halign='right', valign='middle', size_hint_y=0.45,
            )
            self._desc_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
            text_col.add_widget(self._desc_label)
        else:
            self._desc_label = None

        self.add_widget(text_col)

        if control is not None:
            self.add_widget(control)
        elif self.value_text:
            self._value_label = Label(
                text=self.value_text, font_name=theme.font_name,
                font_size='12.5sp', color=theme.text_secondary,
                size_hint_x=None, width=dp(90),
            )
            self.add_widget(self._value_label)
        else:
            self._value_label = None

        if self.show_arrow:
            arrow = Label(text='‹', font_size='20sp', color=theme.text_disabled,
                          size_hint_x=None, width=dp(20))
            self.add_widget(arrow)

        if on_release:
            self.bind(on_touch_up=lambda inst, touch: (
                on_release() if self.collide_point(*touch.pos) else None
            ))

    def on_theme_changed(self):
        super().on_theme_changed()
        if self._icon_label:
            self._icon_label.color = theme.accent
        if self._title_label:
            self._title_label.color = theme.text_primary
        if self._desc_label:
            self._desc_label.color = theme.text_secondary


class FeatureCard(GlassCard):
    """کارت اکشن سریع برای صفحه‌ی خانه (آیکون بزرگ + عنوان کوتاه)"""

    icon = StringProperty('')
    label_text = StringProperty('')

    def __init__(self, on_release=None, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('padding', [dp(10), dp(14), dp(10), dp(10)])
        kwargs.setdefault('spacing', dp(6))
        kwargs.setdefault('radius', 18)
        super().__init__(**kwargs)

        self._icon_label = Label(
            text=self.icon, font_size=f'{IconSize.LG}sp', color=theme.accent,
            size_hint_y=0.6,
        )
        self.add_widget(self._icon_label)

        self._text_label = Label(
            text=self.label_text, font_name=theme.font_name, bold=True,
            font_size='12sp', color=theme.text_primary, size_hint_y=0.4,
        )
        self.add_widget(self._text_label)

        if on_release:
            self.bind(on_touch_up=lambda inst, touch: (
                on_release() if self.collide_point(*touch.pos) else None
            ))

    def on_theme_changed(self):
        super().on_theme_changed()
        self._icon_label.color = theme.accent
        self._text_label.color = theme.text_primary


class ModelCard(GlassCard):
    """کارت نمایش وضعیت مدل هوش مصنوعی فعال (صفحه‌ی خانه/تنظیمات مدل)"""

    model_name = StringProperty('')
    status_text = StringProperty('')
    is_ready = OptionProperty(False, options=[True, False])

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(76))
        kwargs.setdefault('padding', [dp(16), dp(12), dp(16), dp(12)])
        kwargs.setdefault('spacing', dp(12))
        kwargs.setdefault('radius', 18)
        super().__init__(**kwargs)

        dot_wrap = Widget(size_hint_x=None, width=dp(14))
        with dot_wrap.canvas:
            self._dot_color = Color(*self._status_color())
            self._dot = Ellipse(pos=(dot_wrap.x + dp(3), dot_wrap.center_y - dp(4)), size=(dp(8), dp(8)))
        dot_wrap.bind(pos=self._update_dot, size=self._update_dot)
        self.add_widget(dot_wrap)
        self._dot_wrap = dot_wrap

        text_col = BoxLayout(orientation='vertical', spacing=dp(3))
        self._name_label = Label(
            text=self.model_name or 'مدلی بارگذاری نشده', font_name=theme.font_name,
            bold=True, font_size='14sp', color=theme.text_primary,
            halign='right', valign='middle',
        )
        self._name_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(self._name_label)

        self._status_label = Label(
            text=self.status_text, font_name=theme.font_name,
            font_size='11.5sp', color=theme.text_secondary,
            halign='right', valign='middle',
        )
        self._status_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        text_col.add_widget(self._status_label)

        self.add_widget(text_col)
        self.bind(model_name=self._sync_text, status_text=self._sync_text, is_ready=self._sync_dot)

    def _status_color(self):
        return theme.success if self.is_ready else theme.text_disabled

    def _update_dot(self, instance, *args):
        self._dot.pos = (instance.x + dp(3), instance.center_y - dp(4))

    def _sync_text(self, *args):
        self._name_label.text = self.model_name or 'مدلی بارگذاری نشده'
        self._status_label.text = self.status_text

    def _sync_dot(self, *args):
        self._dot_color.rgba = self._status_color()

    def on_theme_changed(self):
        super().on_theme_changed()
        self._name_label.color = theme.text_primary
        self._status_label.color = theme.text_secondary
        self._sync_dot()


class StatisticsCard(GlassCard):
    """کارت آماری کوچک (مثلاً تعداد مکالمات، حجم حافظه) برای صفحه‌ی خانه"""

    value_text = StringProperty('0')
    label_text = StringProperty('')
    icon = StringProperty('')

    def __init__(self, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('padding', [dp(14), dp(12), dp(14), dp(12)])
        kwargs.setdefault('spacing', dp(4))
        kwargs.setdefault('radius', 16)
        super().__init__(**kwargs)

        header = BoxLayout(orientation='horizontal', size_hint_y=0.4)
        self._icon_label = Label(text=self.icon, font_size='16sp', color=theme.accent,
                                  size_hint_x=None, width=dp(24))
        header.add_widget(self._icon_label)
        header.add_widget(Widget())
        self.add_widget(header)

        self._value_label = Label(
            text=self.value_text, font_name=theme.font_name, bold=True,
            font_size='20sp', color=theme.text_primary, size_hint_y=0.35,
            halign='right',
        )
        self.add_widget(self._value_label)

        self._label_label = Label(
            text=self.label_text, font_name=theme.font_name,
            font_size='11sp', color=theme.text_secondary, size_hint_y=0.25,
            halign='right',
        )
        self.add_widget(self._label_label)

        self.bind(value_text=lambda *a: setattr(self._value_label, 'text', self.value_text))
        self.bind(label_text=lambda *a: setattr(self._label_label, 'text', self.label_text))

    def on_theme_changed(self):
        super().on_theme_changed()
        self._icon_label.color = theme.accent
        self._value_label.color = theme.text_primary
        self._label_label.color = theme.text_secondary


# نام مستعار برای وضوح بیشتر در بخش حافظه (همان ساختار StatisticsCard)
class MemoryCard(StatisticsCard):
    pass


# ==========================================================================
# نام‌های مستعار معنایی برای کارت‌های صفحه‌ی خانه (Home Screen Components)
# ==========================================================================
# این کلاس‌ها به‌جای بازنویسی، روی کامپوننت‌های عمومی بالا لایه‌ی معنایی
# مخصوص صفحه‌ی خانه اضافه می‌کنند تا هم کد تکراری نشود و هم نام‌گذاری در
# محل استفاده (src/screens/home.py) گویا و مطابق مستندات طراحی باشد.
# توجه: RecentConversationCard و PinnedChatCard در chat.py تعریف شده‌اند
# (چون به ConversationCard نیاز دارند و از اینجا import کردنشان باعث
# وابستگی چرخه‌ای می‌شود).

class WelcomeCard(GlassCard):
    """کارت خوش‌آمدگویی صفحه‌ی خانه (آواتار هوش مصنوعی + پیام خوشامد)"""
    pass


class QuickActionCard(FeatureCard):
    """کارت اکشن سریع صفحه‌ی خانه (نام مستعار روی FeatureCard)"""
    pass


class ModelStatusCard(ModelCard):
    """کارت وضعیت مدل هوش مصنوعی در صفحه‌ی خانه (نام مستعار روی ModelCard)"""
    pass


class MemoryStatusCard(StatisticsCard):
    """کارت وضعیت حافظه (تعداد مکالمات/یادداشت‌ها) در صفحه‌ی خانه"""
    pass


class StorageStatusCard(StatisticsCard):
    """کارت وضعیت فضای ذخیره‌سازی (حجم مدل‌ها/کش/حافظه) در صفحه‌ی خانه"""
    pass
