# -*- coding: utf-8 -*-
"""
وارد کردن فایل مدل GGUF از طریق انتخاب‌گر فایل اندروید (SAF)

چرا لازم است؟
--------------------------------------------------------------------------
از اندروید ۱۱ (API 30) به بعد گوگل دسترسی برنامه‌ها به پوشه‌ی
``Android/data/`` را محدود کرده و از طرفی مجوز قدیمی
``READ_EXTERNAL_STORAGE`` هم دیگر برای خواندن فایل‌های دلخواه کافی نیست
(Scoped Storage). تنها راه *تضمین‌شده* و سازگار با سیاست‌های گوگل برای
اینکه کاربر بتواند یک فایل دلخواه را به برنامه بدهد، استفاده از
Storage Access Framework است:

    Intent(ACTION_OPEN_DOCUMENT) → کاربر فایل را انتخاب می‌کند →
    برنامه یک URI موقت با اجازه‌ی خواندن می‌گیرد → محتوا را کپی می‌کنیم.

مزیت مهم: این روش **هیچ مجوز runtime لازم ندارد**، چون خود کاربر صریحاً
فایل را انتخاب کرده است.

محدودیت صادقانه: فایل باید *کپی* شود، چون URI موقت است و بعد از بستن
برنامه معتبر نمی‌ماند. برای مدل ۸۰۰ مگابایتی یعنی به همان اندازه فضای
اضافه نیاز است و کپی چند ده ثانیه طول می‌کشد. به همین دلیل در رابط
کاربری هم پیشرفت کپی نمایش داده می‌شود و هم به کاربر گفته می‌شود که
گذاشتن مستقیم فایل در پوشه‌ی مدل‌ها (بدون کپی) سریع‌تر است.
"""

import os
import threading

from src.model_paths import MODEL_EXT, get_models_dir

# کد درخواست دلخواه برای onActivityResult
_REQUEST_CODE = 0x5645  # "VE"

# اندازه‌ی بافر کپی. ۴ مگابایت تعادل خوبی بین سرعت و مصرف حافظه است.
_CHUNK = 4 * 1024 * 1024


class ModelImportError(Exception):
    pass


def is_supported():
    """آیا انتخاب فایل روی این پلتفرم در دسترس است؟"""
    try:
        from kivy.utils import platform
        if platform != 'android':
            return False
        # فقط بررسی می‌کنیم که pyjnius واقعاً در دسترس باشد. از
        # importlib استفاده می‌شود تا یک import بلااستفاده نداشته باشیم
        # (که هم هشدار lint می‌دهد و هم نیت کد را مبهم می‌کند).
        import importlib.util
        return importlib.util.find_spec('jnius') is not None
    except Exception:
        return False


def pick_and_import(on_progress=None, on_done=None, on_error=None):
    """انتخاب‌گر فایل را باز می‌کند و فایل انتخاب‌شده را کپی می‌کند.

    همه‌ی callbackها ممکن است از ترد پس‌زمینه صدا زده شوند؛ صدازننده
    باید خودش با Clock.schedule_once به ترد UI برگردد.

    on_progress(copied_bytes, total_bytes)  - total ممکن است 0 باشد
    on_done(final_path)
    on_error(message)
    """
    if not is_supported():
        if on_error:
            on_error('انتخاب فایل فقط روی اندروید در دسترس است.')
        return False

    try:
        from jnius import autoclass
        from android import activity as android_activity  # type: ignore

        Intent = autoclass('android.content.Intent')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        current = PythonActivity.mActivity

        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        # نوع MIME مخصوصی برای GGUF ثبت نشده، پس همه‌ی فایل‌ها را نشان
        # می‌دهیم و خودمان پسوند را بررسی می‌کنیم.
        intent.setType('*/*')

        def _on_activity_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE:
                return
            try:
                android_activity.unbind(on_activity_result=_on_activity_result)
            except Exception:
                pass

            if result_code != -1 or data is None:  # RESULT_OK == -1
                if on_error:
                    on_error('انتخاب فایل لغو شد.')
                return

            uri = data.getData()
            if uri is None:
                if on_error:
                    on_error('فایلی انتخاب نشد.')
                return

            threading.Thread(
                target=_copy_uri_to_models,
                args=(uri, on_progress, on_done, on_error),
                daemon=True,
            ).start()

        android_activity.bind(on_activity_result=_on_activity_result)
        current.startActivityForResult(intent, _REQUEST_CODE)
        return True

    except Exception as exc:
        if on_error:
            on_error(f'باز کردن انتخاب‌گر فایل ناموفق بود: {exc}')
        return False


def _query_display_name(resolver, uri):
    """نام اصلی فایل را از ContentResolver می‌گیرد."""
    try:
        from jnius import autoclass
        OpenableColumns = autoclass('android.provider.OpenableColumns')
        cursor = resolver.query(uri, None, None, None, None)
        if cursor is not None:
            try:
                if cursor.moveToFirst():
                    idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if idx >= 0:
                        return cursor.getString(idx)
            finally:
                cursor.close()
    except Exception:
        pass
    return None


def _query_size(resolver, uri):
    try:
        from jnius import autoclass
        OpenableColumns = autoclass('android.provider.OpenableColumns')
        cursor = resolver.query(uri, None, None, None, None)
        if cursor is not None:
            try:
                if cursor.moveToFirst():
                    idx = cursor.getColumnIndex(OpenableColumns.SIZE)
                    if idx >= 0 and not cursor.isNull(idx):
                        return int(cursor.getLong(idx))
            finally:
                cursor.close()
    except Exception:
        pass
    return 0


def _copy_uri_to_models(uri, on_progress, on_done, on_error):
    """محتوای URI را داخل پوشه‌ی مدل‌ها کپی می‌کند."""
    temp_path = None
    try:
        from jnius import autoclass

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()

        name = _query_display_name(resolver, uri) or 'model.gguf'
        if not name.lower().endswith(MODEL_EXT):
            raise ModelImportError(
                f'فایل انتخاب‌شده «{name}» پسوند {MODEL_EXT} ندارد. '
                'لطفاً یک فایل مدل GGUF انتخاب کنید.')

        total = _query_size(resolver, uri)
        models_dir = get_models_dir(create=True)

        free = _free_space(models_dir)
        if total and free and free < total * 1.05:
            raise ModelImportError(
                f'فضای کافی نیست: مدل {_human(total)} است ولی فقط '
                f'{_human(free)} فضای خالی وجود دارد.')

        dest = os.path.join(models_dir, name)
        temp_path = dest + '.importing'

        stream = resolver.openInputStream(uri)
        if stream is None:
            raise ModelImportError('خواندن فایل انتخاب‌شده ممکن نشد.')

        copied = 0
        try:
            # خواندن از جاوا به پایتون: از آرایه‌ی بایت جاوا استفاده
            # می‌کنیم تا کپی بدون واسطه و سریع باشد.
            buf = bytearray(_CHUNK)
            with open(temp_path, 'wb') as out:
                while True:
                    chunk = stream.read(len(buf))
                    if chunk is None or len(chunk) == 0:
                        break
                    data = bytes(bytearray(chunk))
                    out.write(data)
                    copied += len(data)
                    if on_progress:
                        on_progress(copied, total)
        finally:
            try:
                stream.close()
            except Exception:
                pass

        if copied == 0:
            raise ModelImportError('فایل خالی بود یا خواندن آن ممکن نشد.')

        os.replace(temp_path, dest)
        temp_path = None

        if on_done:
            on_done(dest)

    except Exception as exc:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if on_error:
            on_error(str(exc))


def _free_space(path):
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
    except Exception:
        return 0


def _human(num):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if num < 1024:
            return f'{num:.0f} {unit}'
        num /= 1024.0
    return f'{num:.1f} TB'
