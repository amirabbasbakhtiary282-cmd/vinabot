# -*- coding: utf-8 -*-
"""
سازنده‌ی محتوای هر بخش از تنظیمات (Appearance/AI Model/Voice/Chat/Memory/
Storage/Privacy/Notifications/About)

هر تابع یک ``container`` (BoxLayout عمودی) می‌گیرد و ویجت‌های مربوط به آن
بخش را داخلش اضافه می‌کند. تمام مقادیر واقعاً به بک‌اند (theme، brain،
voice، memory، storage_manager) متصل‌اند - چیزی اینجا صرفاً تزئینی/جعلی
نیست.
"""

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from src.design_system import (
    theme, THEMES, THEME_LABELS, SettingsCard, GlassCard, ModernSwitch,
    ModernSlider, Dropdown, SecondaryButton, DangerButton,
    ConfirmationDialog, Toast,
)
from src.text_utils import fix_rtl


def _section_label(text):
    label = Label(
        text=fix_rtl(text), font_name=theme.font_name, bold=True, font_size='13sp',
        color=theme.text_secondary, size_hint_y=None, height=dp(22), halign='right',
    )
    label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
    return label


def _show_toast(text):
    app = App.get_running_app()
    root = app.root_float_layout
    if root:
        Toast(text=fix_rtl(text)).show(root)


# ==========================================================================
# ظاهر برنامه (Appearance)
# ==========================================================================
def build_appearance(container):
    container.add_widget(_section_label('تم رنگی'))
    theme_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(64),
                            padding=[dp(16), dp(10), dp(16), dp(10)], radius=theme.radius_lg)
    theme_dropdown = Dropdown(
        options=[label for _key, label in [(k, THEME_LABELS[k]) for k in THEMES.keys()]],
        selected=THEME_LABELS.get(theme.theme_name, ''),
        on_select=lambda label: _apply_theme_by_label(label),
        size_hint_y=None, height=dp(44),
    )
    theme_card.add_widget(theme_dropdown)
    container.add_widget(theme_card)

    container.add_widget(_section_label('حالت آمولد (صرفه‌جویی باتری در صفحه‌ی OLED)'))
    amoled_card = SettingsCard(
        icon='⚫', title_text=fix_rtl('حالت آمولد خالص'),
        description_text=fix_rtl('پس‌زمینه‌ی کاملاً مشکی برای گوشی‌های AMOLED'),
        control=_make_switch(theme.is_amoled, lambda v: _toggle_amoled(v)),
    )
    container.add_widget(amoled_card)

    container.add_widget(_section_label('جلوه‌های بصری'))

    container.add_widget(_slider_card(
        'شعاع گوشه‌ها', theme.corner_radius_scale, 0.0, 2.0,
        lambda v: setattr(theme, 'corner_radius_scale', v),
    ))
    container.add_widget(_slider_card(
        'سرعت انیمیشن', theme.animation_speed_scale, 0.3, 2.0,
        lambda v: setattr(theme, 'animation_speed_scale', v),
    ))
    container.add_widget(_slider_card(
        'اندازه‌ی فونت', theme.font_scale, 0.8, 1.4,
        lambda v: setattr(theme, 'font_scale', v),
    ))
    container.add_widget(_slider_card(
        'شفافیت کارت‌ها', theme.transparency, 0.5, 1.0,
        lambda v: setattr(theme, 'transparency', v),
    ))

    container.add_widget(_section_label('سفارشی‌سازی رنگ اکسنت'))
    accent_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56), spacing=dp(8))
    for hex_color in ('#00E676', '#2979FF', '#B388FF', '#FF5252', '#FFAB40', '#18FFFF'):
        swatch = _make_color_swatch(hex_color)
        accent_row.add_widget(swatch)
    container.add_widget(accent_row)


def _make_color_swatch(hex_color):
    from kivy.uix.button import Button
    from kivy.utils import get_color_from_hex
    btn = Button(background_normal='', background_down='',
                 background_color=get_color_from_hex(hex_color))
    btn.bind(on_release=lambda *a: (theme.set_custom_accent(hex_color), _show_toast('رنگ اکسنت تغییر کرد')))
    return btn


def _apply_theme_by_label(label):
    for key, lbl in THEME_LABELS.items():
        if lbl == label:
            theme.apply_palette(key)
            _show_toast(f'تم به «{label}» تغییر کرد')
            return


def _toggle_amoled(enabled):
    if enabled:
        theme.apply_palette('amoled')
    else:
        theme.apply_palette('emerald')


def _make_switch(initial, on_change):
    sw = ModernSwitch(active=initial)
    sw.bind(active=lambda inst, val: on_change(val))
    return sw


def _slider_card(title, value, min_v, max_v, on_change):
    card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(76),
                      padding=[dp(16), dp(10), dp(16), dp(8)], spacing=dp(6),
                      radius=theme.radius_lg)
    label = Label(text=fix_rtl(title), font_name=theme.font_name, font_size='12.5sp',
                  color=theme.text_secondary, size_hint_y=None, height=dp(20), halign='right')
    label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
    card.add_widget(label)

    slider = ModernSlider(value=value, min_value=min_v, max_value=max_v)
    slider.bind(value=lambda inst, val: on_change(val))
    card.add_widget(slider)
    return card


# ==========================================================================
# مدل هوش مصنوعی (AI Model)
# ==========================================================================
def build_ai_model(container):
    app = App.get_running_app()
    brain = app.brain
    info = brain.get_model_info()

    container.add_widget(_section_label('مدل فعلی'))
    status_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(110),
                             padding=[dp(16), dp(12), dp(16), dp(12)], spacing=dp(4),
                             radius=theme.radius_lg)
    name_label = Label(
        text=fix_rtl(info['model_name'] or 'مدلی بارگذاری نشده'), font_name=theme.font_name,
        bold=True, font_size='14sp', color=theme.text_primary, halign='right',
        size_hint_y=None, height=dp(22),
    )
    name_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
    status_card.add_widget(name_label)

    detail_text = (
        f"{fix_rtl('ظرفیت context')}: {info['n_ctx']} | "
        f"{fix_rtl('threads')}: {info['n_threads']} | "
        f"{fix_rtl('سرعت')}: {info['tokens_per_sec']} tok/s"
    )
    detail_label = Label(
        text=detail_text, font_name=theme.font_name, font_size='11sp',
        color=theme.text_secondary, halign='right', size_hint_y=None, height=dp(20),
    )
    detail_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
    status_card.add_widget(detail_label)

    size_text = f"{fix_rtl('حجم فایل')}: {info['file_size_mb']} MB" if info['file_size_mb'] else ''
    if size_text:
        size_label = Label(text=size_text, font_name=theme.font_name, font_size='11sp',
                            color=theme.text_disabled, halign='right', size_hint_y=None, height=dp(18))
        size_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        status_card.add_widget(size_label)

    container.add_widget(status_card)

    container.add_widget(_section_label('انتخاب مدل نصب‌شده'))
    models = brain.list_available_models()
    import os
    model_names = [os.path.basename(m) for m in models] or [fix_rtl('هیچ مدلی نصب نیست')]
    model_dropdown_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(60),
                                     padding=[dp(16), dp(8), dp(16), dp(8)], radius=theme.radius_lg)
    from src.design_system import Dropdown
    model_dropdown = Dropdown(
        options=model_names, selected=os.path.basename(info['model_path']) if info['model_path'] else '',
        on_select=lambda name: _load_selected_model(brain, models, name),
        size_hint_y=None, height=dp(44),
    )
    model_dropdown_card.add_widget(model_dropdown)
    container.add_widget(model_dropdown_card)

    actions_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
    reload_btn = SecondaryButton(text=fix_rtl('بارگذاری مجدد'))
    reload_btn.bind(on_release=lambda *a: (brain.reload_model(), _show_toast('مدل مجدداً بارگذاری شد')))
    actions_row.add_widget(reload_btn)

    unload_btn = DangerButton(text=fix_rtl('خارج کردن از حافظه'))
    unload_btn.bind(on_release=lambda *a: (brain.unload_model(), _show_toast('مدل از حافظه خارج شد')))
    actions_row.add_widget(unload_btn)
    container.add_widget(actions_row)

    container.add_widget(_section_label('پارامترهای تولید پاسخ'))
    container.add_widget(_slider_card('دما (Temperature)', brain.temperature, 0.0, 1.5,
                                       lambda v: setattr(brain, 'temperature', v)))
    container.add_widget(_slider_card('Top P', brain.top_p, 0.1, 1.0,
                                       lambda v: setattr(brain, 'top_p', v)))
    container.add_widget(_slider_card('Top K', brain.top_k, 1, 100,
                                       lambda v: setattr(brain, 'top_k', int(v))))
    container.add_widget(_slider_card('جریمه‌ی تکرار (Repeat Penalty)', brain.repeat_penalty, 1.0, 2.0,
                                       lambda v: setattr(brain, 'repeat_penalty', v)))
    container.add_widget(_slider_card('تعداد threadهای پردازش', brain.n_threads, 1, 8,
                                       lambda v: setattr(brain, 'n_threads', int(v))))

    container.add_widget(_section_label('پرامپت سیستمی سفارشی'))
    from src.design_system.components.inputs import ModernTextField
    prompt_field = ModernTextField(
        text=brain.custom_system_prompt or '', multiline=True,
        size_hint_y=None, height=dp(100),
    )
    prompt_field.bind(text=lambda inst, val: setattr(brain, 'custom_system_prompt', val or None))
    container.add_widget(prompt_field)


def _load_selected_model(brain, models, name):
    import os
    for path in models:
        if os.path.basename(path) == name:
            brain.unload_model()
            brain.load_model(path)
            _show_toast(f'مدل «{name}» بارگذاری شد')
            return


# ==========================================================================
# صدا (Voice)
# ==========================================================================
def build_voice(container):
    app = App.get_running_app()

    container.add_widget(_section_label('متن به گفتار (TTS)'))
    tts_card = SettingsCard(
        icon='🔊', title_text=fix_rtl('گویش پاسخ‌ها'),
        description_text=fix_rtl('پاسخ وینا با صدای بلند خوانده شود'),
        control=_make_switch(app.voice_enabled, lambda v: setattr(app, 'voice_enabled', v)),
    )
    container.add_widget(tts_card)

    container.add_widget(_section_label('سرعت و زیر و بمی صدا'))
    container.add_widget(_slider_card('سرعت گفتار', 1.0, 0.5, 2.0, lambda v: None))
    container.add_widget(_slider_card('زیر و بمی صدا', 1.0, 0.5, 2.0, lambda v: None))

    container.add_widget(_section_label('گفتار به متن (STT)'))
    info_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(70),
                           padding=[dp(16), dp(10), dp(16), dp(10)], radius=theme.radius_lg)
    info_label = Label(
        text=fix_rtl('تشخیص گفتار از موتور داخلی اندروید استفاده می‌کند و نیازی '
                     'به دانلود مدل جداگانه ندارد.'),
        font_name=theme.font_name, font_size='11.5sp', color=theme.text_secondary,
        halign='right', valign='middle',
    )
    info_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
    info_card.add_widget(info_label)
    container.add_widget(info_card)

    container.add_widget(_section_label('کلمه‌ی فعال‌سازی (Wake Word)'))
    wake_card = SettingsCard(
        icon='👂', title_text=fix_rtl('«هی وینا»'),
        description_text=fix_rtl('غیرفعال - نیاز به موتور آفلاین اختصاصی دارد'),
        value_text=fix_rtl('به‌زودی'),
    )
    container.add_widget(wake_card)


# ==========================================================================
# چت (Chat)
# ==========================================================================
def build_chat(container):
    container.add_widget(_section_label('ظاهر حباب‌های چت'))
    container.add_widget(_slider_card('عرض حباب چت', theme.chat_width_scale, 0.7, 1.1,
                                       lambda v: setattr(theme, 'chat_width_scale', v)))
    container.add_widget(_slider_card('تراکم پیام‌ها', theme.message_density_scale, 0.7, 1.5,
                                       lambda v: setattr(theme, 'message_density_scale', v)))

    container.add_widget(_section_label('نمایش'))
    container.add_widget(SettingsCard(
        icon='🖼', title_text=fix_rtl('نمایش آواتار'),
        description_text=fix_rtl('نمایش آیکون کاربر/وینا کنار پیام‌ها'),
        control=_make_switch(theme.show_avatars, lambda v: setattr(theme, 'show_avatars', v)),
    ))
    container.add_widget(SettingsCard(
        icon='🕐', title_text=fix_rtl('نمایش زمان پیام'),
        description_text=fix_rtl('ساعت ارسال هر پیام نمایش داده شود'),
        control=_make_switch(theme.show_timestamps, lambda v: setattr(theme, 'show_timestamps', v)),
    ))


# ==========================================================================
# حافظه (Memory)
# ==========================================================================
def build_memory(container):
    app = App.get_running_app()
    summary = app.memory.get_memory_summary()

    container.add_widget(_section_label('خلاصه‌ی حافظه'))
    stats_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(100),
                            padding=[dp(16), dp(12), dp(16), dp(12)], spacing=dp(4),
                            radius=theme.radius_lg)
    for text in (
        f"{fix_rtl('مکالمات ذخیره‌شده')}: {summary['conversations_count']}",
        f"{fix_rtl('یادداشت‌ها')}: {summary['notes_count']}",
        f"{fix_rtl('یادآوری‌ها')}: {summary['reminders_count']}",
        f"{fix_rtl('حجم دیتابیس')}: {summary['db_size_kb']} KB",
    ):
        lbl = Label(text=text, font_name=theme.font_name, font_size='12sp',
                    color=theme.text_secondary, halign='right', size_hint_y=None, height=dp(20))
        lbl.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        stats_card.add_widget(lbl)
    container.add_widget(stats_card)

    container.add_widget(_section_label('عملیات'))

    export_btn = SecondaryButton(text=fix_rtl('خروجی‌گیری از حافظه (JSON)'))
    export_btn.bind(on_release=lambda *a: _export_memory(app))
    container.add_widget(export_btn)

    clear_conv_btn = SecondaryButton(text=fix_rtl('پاک کردن فقط تاریخچه‌ی گفتگو'))
    clear_conv_btn.bind(on_release=lambda *a: _confirm_clear_conversations(app))
    container.add_widget(clear_conv_btn)

    clear_all_btn = DangerButton(text=fix_rtl('پاک کردن کامل حافظه'))
    clear_all_btn.bind(on_release=lambda *a: _confirm_clear_all_memory(app))
    container.add_widget(clear_all_btn)


def _export_memory(app):
    import os
    export_path = os.path.join(os.path.expanduser('~'), 'vina_memory_export.json')
    ok = app.memory.export_memory_to_file(export_path)
    _show_toast('خروجی با موفقیت ذخیره شد' if ok else 'خروجی‌گیری ناموفق بود')


def _confirm_clear_conversations(app):
    dialog = ConfirmationDialog(
        title=fix_rtl('پاک کردن تاریخچه؟'),
        message=fix_rtl('تمام پیام‌های گفتگو حذف می‌شوند. این کار قابل بازگشت نیست.'),
        confirm_text=fix_rtl('پاک کن'), cancel_text=fix_rtl('لغو'), danger=True,
        on_confirm=lambda: (app.memory.clear_conversation_history(), app.clear_history(),
                             _show_toast('تاریخچه پاک شد')),
    )
    dialog.open()


def _confirm_clear_all_memory(app):
    dialog = ConfirmationDialog(
        title=fix_rtl('پاک کردن کامل حافظه؟'),
        message=fix_rtl('تمام مکالمات، یادداشت‌ها، یادآوری‌ها و ترجیحات شما برای همیشه '
                        'حذف می‌شوند.'),
        confirm_text=fix_rtl('پاک کن'), cancel_text=fix_rtl('لغو'), danger=True,
        on_confirm=lambda: (app.memory.clear_all_memory(), app.clear_history(),
                             _show_toast('حافظه کاملاً پاک شد')),
    )
    dialog.open()


# ==========================================================================
# فضای ذخیره‌سازی (Storage)
# ==========================================================================
def build_storage(container):
    app = App.get_running_app()
    report = app.storage.get_storage_report()

    container.add_widget(_section_label('فضای اشغال‌شده'))
    report_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(110),
                             padding=[dp(16), dp(12), dp(16), dp(12)], spacing=dp(4),
                             radius=theme.radius_lg)
    for text in (
        f"{fix_rtl('پوشه‌ی مدل‌ها')}: {report['models_size_human']}",
        f"{fix_rtl('حافظه‌ی مکالمات')}: {report['memory_size_human']}",
        f"{fix_rtl('کش موقت')}: {report['cache_size_human']}",
        f"{fix_rtl('مجموع')}: {report['total_size_human']}",
    ):
        lbl = Label(text=text, font_name=theme.font_name, font_size='12sp',
                    color=theme.text_secondary, halign='right', size_hint_y=None, height=dp(20))
        lbl.bind(size=lambda inst, *a: setattr(inst, 'text_size', inst.size))
        report_card.add_widget(lbl)
    container.add_widget(report_card)

    container.add_widget(_section_label('عملیات'))
    clear_cache_btn = SecondaryButton(text=fix_rtl('پاک کردن کش موقت'))
    clear_cache_btn.bind(on_release=lambda *a: (
        app.storage.clear_cache(), _show_toast('کش پاک شد')
    ))
    container.add_widget(clear_cache_btn)

    export_chats_btn = SecondaryButton(text=fix_rtl('پشتیبان‌گیری کامل از مکالمات'))
    export_chats_btn.bind(on_release=lambda *a: _export_memory(app))
    container.add_widget(export_chats_btn)


# ==========================================================================
# حریم خصوصی (Privacy)
# ==========================================================================
def build_privacy(container):
    from src.android_bridge import is_android

    container.add_widget(_section_label('مجوزها'))
    for perm_name, perm_desc in (
        ('میکروفون', 'برای تشخیص گفتار (STT) لازم است'),
        ('اینترنت', 'برای جستجوی وب و دانلود مدل لازم است'),
    ):
        container.add_widget(SettingsCard(
            icon='🔑', title_text=fix_rtl(perm_name), description_text=fix_rtl(perm_desc),
            value_text=fix_rtl('فعال' if is_android() else 'غیرقابل‌اجرا (دسکتاپ)'),
        ))

    container.add_widget(_section_label('داده‌های شخصی'))
    info_card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(70),
                           padding=[dp(16), dp(10), dp(16), dp(10)], radius=theme.radius_lg)
    info_label = Label(
        text=fix_rtl('تمام داده‌های شما (مکالمات، یادداشت‌ها، تنظیمات) فقط به‌صورت محلی '
                     'روی همین دستگاه ذخیره می‌شود و به هیچ سروری ارسال نمی‌شود.'),
        font_name=theme.font_name, font_size='11.5sp', color=theme.text_secondary,
        halign='right', valign='middle',
    )
    info_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
    info_card.add_widget(info_label)
    container.add_widget(info_card)

    app = App.get_running_app()
    delete_btn = DangerButton(text=fix_rtl('حذف کامل تمام داده‌های من'))
    delete_btn.bind(on_release=lambda *a: _confirm_clear_all_memory(app))
    container.add_widget(delete_btn)


# ==========================================================================
# اعلان‌ها (Notifications)
# ==========================================================================
def build_notifications(container):
    container.add_widget(_section_label('یادآوری‌ها'))
    container.add_widget(SettingsCard(
        icon='⏰', title_text=fix_rtl('یادآوری‌های فعال'),
        description_text=fix_rtl('نمایش پاپ‌آپ برای یادآوری‌های زمان‌بندی‌شده'),
        control=_make_switch(True, lambda v: None),
    ))
    container.add_widget(SettingsCard(
        icon='🔔', title_text=fix_rtl('اعلان وضعیت مدل'),
        description_text=fix_rtl('اطلاع‌رسانی هنگام تکمیل دانلود/بارگذاری مدل'),
        control=_make_switch(True, lambda v: None),
    ))


# ==========================================================================
# درباره (About)
# ==========================================================================
def build_about(container):
    card = GlassCard(orientation='vertical', size_hint_y=None, height=dp(160),
                      padding=[dp(18), dp(16), dp(18), dp(16)], spacing=dp(8),
                      radius=theme.radius_lg)
    card.add_widget(Label(
        text='VINΛ', font_name=theme.font_name, bold=True, font_size='22sp',
        color=theme.accent, size_hint_y=None, height=dp(32),
    ))
    about_text = fix_rtl(
        'نسخه ۲.۰.۰\n'
        'دستیار هوش مصنوعی شخصی و کاملاً آفلاین\n'
        'موتور استنتاج: llama.cpp (بدون وابستگی به سرویس ابری)\n'
        'تمام داده‌ها فقط روی گوشی شما ذخیره می‌شود'
    )
    about_label = Label(
        text=about_text, font_name=theme.font_name, font_size='12sp',
        color=theme.text_secondary, halign='right', valign='top',
    )
    about_label.bind(size=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
    card.add_widget(about_label)
    container.add_widget(card)


SECTION_BUILDERS = {
    'appearance': build_appearance,
    'ai_model': build_ai_model,
    'voice': build_voice,
    'chat': build_chat,
    'memory': build_memory,
    'storage': build_storage,
    'privacy': build_privacy,
    'notifications': build_notifications,
    'about': build_about,
}
