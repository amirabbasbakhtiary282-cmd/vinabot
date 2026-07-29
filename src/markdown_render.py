# -*- coding: utf-8 -*-
"""
موتور نمایش Markdown و کدبلاک‌های رنگی برای پیام‌های چت

Kivy Label بومی از HTML/Markdown پشتیبانی نمی‌کند اما زبان markup داخلی
خودش را دارد (``[b]``, ``[i]``, ``[color=#RRGGBB]``...). این ماژول یک
مبدل سبک Markdown → Kivy-markup می‌نویسد و برای بلوک‌های کد از Pygments
(کتابخانه‌ی خالص پایتون، بدون وابستگی native) برای syntax highlighting
واقعی استفاده می‌کند.
"""

import re

try:
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.util import ClassNotFound
    _PYGMENTS_AVAILABLE = True
except Exception:
    _PYGMENTS_AVAILABLE = False


_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _escape_markup(text):
    """جلوگیری از تداخل کاراکترهای [ ] کاربر با Kivy markup"""
    return text.replace('[', '&bl;').replace(']', '&br;').replace('&', '&amp;')


def highlight_code(code, language, accent_hex):
    """تبدیل یک بلوک کد به رشته‌ی Kivy markup با رنگ‌های واقعی نحو (syntax)"""
    code = code.rstrip('\n')
    if not _PYGMENTS_AVAILABLE:
        return _escape_markup(code)

    try:
        lexer = get_lexer_by_name(language) if language else guess_lexer(code)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            return _escape_markup(code)

    out = []
    try:
        for token, value in lexer.get_tokens(code):
            color = _token_color(token)
            value = _escape_markup(value)
            if value == '':
                continue
            if color:
                # خطوط جدید نباید داخل تگ [color] بشکنند؛ مشکلی ندارد چون
                # Kivy markup تگ‌های چندخطی را هم پشتیبانی می‌کند.
                out.append(f'[color={color}]{value}[/color]')
            else:
                out.append(value)
    except Exception:
        return _escape_markup(code)

    return ''.join(out)


def _token_color(token):
    """رنگ‌بندی ساده و خوانا برای توکن‌های رایج (مستقل از استایل خاص pygments)"""
    name = str(token)
    if 'Keyword' in name:
        return 'C792EA'
    if 'Name.Function' in name or 'Name.Class' in name:
        return '82AAFF'
    if 'String' in name:
        return 'C3E88D'
    if 'Number' in name:
        return 'F78C6C'
    if 'Comment' in name:
        return '6B7089'
    if 'Operator' in name:
        return '89DDFF'
    if 'Name.Builtin' in name:
        return 'FFCB6B'
    return None


def parse_message_segments(text):
    """پیام را به بخش‌های متن ساده و بلوک‌های کد تفکیک می‌کند.

    خروجی: لیستی از دیکشنری‌ها با کلید ``type`` (``text`` یا ``code``).
    """
    segments = []
    last_end = 0
    for match in _CODE_BLOCK_RE.finditer(text):
        if match.start() > last_end:
            segments.append({'type': 'text', 'content': text[last_end:match.start()]})
        language = match.group(1).strip()
        code = match.group(2)
        segments.append({'type': 'code', 'language': language, 'content': code})
        last_end = match.end()
    if last_end < len(text):
        segments.append({'type': 'text', 'content': text[last_end:]})
    if not segments:
        segments.append({'type': 'text', 'content': text})
    return segments


def markdown_text_to_kivy_markup(text):
    """تبدیل یک بخش متنی (بدون کدبلاک) به Kivy markup: **بولد**، `کد درون‌خطی`، *ایتالیک*"""
    text = _escape_markup(text)
    text = _INLINE_CODE_RE.sub(lambda m: f'[b][color=FFCB6B]{m.group(1)}[/color][/b]', text)
    text = _BOLD_RE.sub(lambda m: f'[b]{m.group(1)}[/b]', text)
    text = _ITALIC_RE.sub(lambda m: f'[i]{m.group(1)}[/i]', text)
    return text
