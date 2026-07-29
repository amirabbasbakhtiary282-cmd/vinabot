# -*- coding: utf-8 -*-
"""
مرجع واحد مسیر مدل‌ها (GGUF)

چرا این ماژول ساخته شد؟
--------------------------------------------------------------------------
قبلاً سه جای مختلف (src/brain.py، src/model_downloader.py و صفحه‌ی
تنظیمات) هرکدام منطق جداگانه‌ی خودشان را برای پیدا کردن پوشه‌ی مدل‌ها
داشتند و لیست مسیرهایشان هم *یکسان نبود*. نتیجه: ممکن بود دانلودکننده
مدل را در یک پوشه بگذارد ولی موتور از پوشه‌ی دیگری دنبالش بگردد.

مهم‌تر از آن، هر سه فقط مسیرهای زیر را می‌شناختند:

    <ریشه‌ی پروژه>/models
    /data/data/org.vinabot/files/models
    ~/.vina/models

که روی اندروید یک مشکل اساسی دارد: مسیر ``/data/data/<package>/files``
حافظه‌ی **خصوصی** برنامه است. کاربر روی گوشی روت‌نشده اصلاً نمی‌تواند با
هیچ فایل‌منیجری یا از طریق USB فایلی را آنجا کپی کند. یعنی خواسته‌ی
«کاربر مدل را در پوشه‌ی Models برنامه می‌گذارد» عملاً غیرممکن بود.

راه‌حل درست روی اندروید مدرن (۸ تا ۱۵)
--------------------------------------------------------------------------
پوشه‌ی «external files dir» مخصوص برنامه:

    /sdcard/Android/data/org.vinabot/files/models/

ویژگی‌های این مسیر:
  • از طریق USB و اکثر فایل‌منیجرها قابل دسترسی است.
  • برای *نوشتن توسط خود برنامه* به هیچ مجوزی نیاز ندارد
    (از اندروید ۴.۴ به بعد، برای مسیر مخصوص همان برنامه).
  • با حذف برنامه پاک می‌شود (رفتار تمیز و مورد انتظار).

نکته‌ی مهم درباره‌ی اندروید ۱۱+ (API 30):
گوگل در اندروید ۱۱ دسترسی *سایر برنامه‌ها* (از جمله برخی فایل‌منیجرها)
به ``Android/data/`` را محدود کرد. کپی از طریق کابل USB/MTP و همچنین
فایل‌منیجر خود سازنده‌ی گوشی معمولاً هنوز کار می‌کند، اما تضمینی نیست.
برای همین دو راه پشتیبان هم داریم:
  ۱) پوشه‌ی ``Download/Vina`` در حافظه‌ی مشترک هم اسکن می‌شود (کاربر
     می‌تواند مدل را آنجا بگذارد که همیشه در دسترس همه هست).
  ۲) انتخاب فایل با Storage Access Framework از داخل برنامه
     (src/model_import.py) که اصلاً محدودیت مسیر ندارد.

ترتیب جستجو عمداً از «قابل‌دسترس‌ترین برای کاربر» شروع می‌شود.
"""

import os

MODEL_EXT = '.gguf'

# نام مدل پیش‌فرض پروژه. صرفاً برای *اولویت‌دهی* در انتخاب خودکار و نمایش
# پیام راهنما استفاده می‌شود؛ هیچ‌جای کد به این نام وابسته نیست و هر فایل
# GGUF معتبری کار می‌کند.
DEFAULT_MODEL_NAME = 'gemma-3-1b-it-Q4_K_M.gguf'

_ANDROID_PACKAGE = 'org.vinabot'


def is_android():
    """آیا روی اندروید اجرا می‌شویم؟"""
    return 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_STORAGE' in os.environ


def _android_dirs():
    """مسیرهای مخصوص اندروید، به ترتیب اولویت."""
    dirs = []

    # ۱) پوشه‌ی external مخصوص برنامه - مسیری که کاربر واقعاً می‌تواند
    #    فایل را در آن بگذارد. این اولویت اول است.
    try:
        from jnius import autoclass  # type: ignore
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        if activity is not None:
            ext = activity.getExternalFilesDir(None)
            if ext is not None:
                dirs.append(os.path.join(ext.getAbsolutePath(), 'models'))
    except Exception:
        # pyjnius در دسترس نیست یا هنوز Activity ساخته نشده؛ به مسیر
        # قراردادی برمی‌گردیم که روی عملاً همه‌ی گوشی‌ها همین است.
        pass

    try:
        from android.storage import primary_external_storage_path  # type: ignore
        base = primary_external_storage_path()
        dirs.append(os.path.join(
            base, 'Android', 'data', _ANDROID_PACKAGE, 'files', 'models'))
        # ۲) پوشه‌ی Download/Vina - همیشه برای کاربر قابل دسترسی است،
        #    حتی در اندروید ۱۱+ که Android/data محدود شده.
        dirs.append(os.path.join(base, 'Download', 'Vina'))
    except Exception:
        dirs.append(os.path.join(
            '/sdcard', 'Android', 'data', _ANDROID_PACKAGE, 'files', 'models'))
        dirs.append('/sdcard/Download/Vina')

    # ۳) حافظه‌ی خصوصی برنامه - کاربر نمی‌تواند اینجا فایل بگذارد، ولی
    #    وقتی مدل از طریق «انتخاب فایل» داخل برنامه وارد شود اینجا
    #    ذخیره می‌شود، و همیشه قابل نوشتن است.
    try:
        from android.storage import app_storage_path  # type: ignore
        dirs.append(os.path.join(app_storage_path(), 'models'))
    except Exception:
        dirs.append(f'/data/data/{_ANDROID_PACKAGE}/files/models')

    return dirs


def _desktop_dirs():
    """مسیرهای دسکتاپ (توسعه و تست)."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [
        os.environ.get('VINA_MODELS_DIR', ''),
        os.path.join(project_root, 'models'),
        os.path.expanduser('~/.vina/models'),
    ]


def candidate_dirs():
    """همه‌ی پوشه‌هایی که برای پیدا کردن مدل بررسی می‌شوند (به ترتیب اولویت)."""
    dirs = _android_dirs() if is_android() else _desktop_dirs()
    # حذف مقادیر خالی و تکراری، با حفظ ترتیب
    seen = set()
    result = []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            result.append(d)
    return result


def get_models_dir(create=True):
    """پوشه‌ی «اصلی» مدل‌ها؛ جایی که به کاربر نشان می‌دهیم و در آن می‌نویسیم.

    اولین مسیری که بتوان در آن نوشت برگردانده می‌شود. اگر هیچ‌کدام قابل
    نوشتن نبود، آخرین گزینه (حافظه‌ی خصوصی که همیشه قابل نوشتن است)
    برگردانده می‌شود تا تابع هرگز None برنگرداند و کد صدازننده کرش نکند.
    """
    dirs = candidate_dirs()
    for path in dirs:
        try:
            if create:
                os.makedirs(path, exist_ok=True)
            if os.path.isdir(path) and os.access(path, os.W_OK):
                return path
        except Exception:
            continue
    return dirs[-1] if dirs else os.path.abspath('models')


def ensure_models_dir():
    """ساخت پوشه‌ی مدل‌ها. مسیر ساخته‌شده را برمی‌گرداند.

    این تابع هنگام شروع برنامه صدا زده می‌شود تا حتی وقتی هیچ مدلی وجود
    ندارد، پوشه از قبل ساخته شده باشد و کاربر بتواند فایل را داخلش کپی
    کند (خواسته‌ی صریح: «برنامه باید پوشه‌ی Models را خودکار بسازد»).
    """
    path = get_models_dir(create=True)
    # یک فایل راهنما کنار پوشه می‌گذاریم تا کاربر وقتی با فایل‌منیجر
    # آنجا را باز می‌کند بداند چه فایلی باید کپی کند.
    try:
        readme = os.path.join(path, 'README.txt')
        if not os.path.exists(readme):
            with open(readme, 'w', encoding='utf-8') as f:
                f.write(
                    'پوشه‌ی مدل‌های زبانی وینا\n'
                    '=========================\n\n'
                    'فایل مدل با پسوند .gguf را در همین پوشه کپی کنید.\n\n'
                    f'مدل پیشنهادی: {DEFAULT_MODEL_NAME}\n\n'
                    'پس از کپی کردن، برنامه را باز کنید و از بخش\n'
                    '«تنظیمات ← مدل هوش مصنوعی» گزینه‌ی «جستجوی مجدد مدل»\n'
                    'را بزنید (نیازی به نصب مجدد برنامه نیست).\n'
                )
    except Exception:
        pass
    return path


def find_models():
    """لیست همه‌ی فایل‌های GGUF پیدا شده در همه‌ی مسیرها.

    خروجی: لیستی از مسیرهای کامل، بدون تکرار. مدل پیش‌فرض پروژه (اگر
    وجود داشته باشد) همیشه اول لیست قرار می‌گیرد.
    """
    found = []
    seen = set()
    for directory in candidate_dirs():
        try:
            if not os.path.isdir(directory):
                continue
            for entry in sorted(os.listdir(directory)):
                if not entry.lower().endswith(MODEL_EXT):
                    continue
                full = os.path.join(directory, entry)
                if not os.path.isfile(full):
                    continue
                real = os.path.realpath(full)
                if real in seen:
                    continue
                seen.add(real)
                found.append(full)
        except Exception:
            # یک پوشه‌ی غیرقابل خواندن نباید کل جستجو را خراب کند
            continue

    # مدل پیش‌فرض اولویت دارد
    found.sort(key=lambda p: (os.path.basename(p).lower()
                              != DEFAULT_MODEL_NAME.lower()))
    return found


def find_model():
    """اولین مدل مناسب، یا None اگر هیچ مدلی نبود."""
    models = find_models()
    return models[0] if models else None


def describe_search_locations():
    """متن راهنما برای نمایش به کاربر وقتی هیچ مدلی پیدا نشد."""
    lines = []
    for d in candidate_dirs():
        marker = '✓' if os.path.isdir(d) else '×'
        lines.append(f'{marker} {d}')
    return '\n'.join(lines)
