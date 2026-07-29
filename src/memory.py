# -*- coding: utf-8 -*-
"""
ماژول حافظه دائمی وینا
مدیریت SQLite برای ذخیره مکالمات، اطلاعات، یادآوری‌ها و الگوها
"""

import os
import sqlite3
import hashlib
import hmac
import binascii
import json
from datetime import datetime, timedelta


PBKDF2_ITERATIONS = 200_000


class VinaMemory:
    """کلاس حافظه دائمی وینا"""

    def __init__(self):
        self.db_path = self._get_db_path()
        self.current_user = None
        self.conn = None
        self.init_database()

    def _get_db_path(self):
        """مسیر دیتابیس"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'memory', 'vina_memory.db'),
            '/data/data/org.vinabot/files/memory/vina_memory.db',
        ]
        for path in possible_paths:
            parent = os.path.dirname(path)
            if os.path.exists(parent) or self._create_dir(parent):
                return path
        return possible_paths[0]

    def _create_dir(self, path):
        """ایجاد پوشه"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False

    def init_database(self):
        """ایجاد جداول دیتابیس"""
        try:
            parent = os.path.dirname(self.db_path)
            if not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")

            cursor = self.conn.cursor()

            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                role TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                note TEXT,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                message TEXT,
                time TIMESTAMP,
                is_done INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                key TEXT,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                key TEXT,
                value TEXT,
                confidence REAL DEFAULT 1.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS behavioral_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_user ON reminders(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_user ON behavioral_patterns(username)')

            self.conn.commit()
        except Exception as e:
            print(f"خطا در ایجاد دیتابیس: {e}")

    def _hash_password(self, password, salt=None):
        """هش امن رمز عبور با PBKDF2-HMAC-SHA256 و نمک تصادفی اختصاصی هر کاربر.

        نسخه‌ی قبلی از یک نمک ثابت و یکسان برای همه‌ی کاربران با یک دور
        SHA-256 استفاده می‌کرد که در برابر حملات rainbow table و brute-force
        بسیار ضعیف است. این نسخه از PBKDF2 با ۲۰۰٬۰۰۰ تکرار و نمک تصادفی
        ۱۶ بایتی مخصوص هر کاربر استفاده می‌کند (هم‌راستا با توصیه‌های OWASP).
        """
        if salt is None:
            salt = os.urandom(16)
        derived = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS
        )
        return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(derived).decode()}"

    def _verify_password(self, password, stored_hash):
        """بررسی رمز عبور در برابر هش ذخیره‌شده.

        از هش‌های قدیمی (SHA-256 با نمک ثابت، بدون کاراکتر '$') نیز برای
        سازگاری با کاربران موجود قبل از ارتقا پشتیبانی می‌شود.
        """
        if not stored_hash:
            return False
        if '$' not in stored_hash:
            # سازگاری با فرمت قدیمی و ناامن (فقط برای مهاجرت داده‌های موجود)
            legacy_salt = "vina_ai_salt_2026"
            legacy_hash = hashlib.sha256(f"{legacy_salt}{password}".encode()).hexdigest()
            return hmac.compare_digest(legacy_hash, stored_hash)
        try:
            salt_hex, hash_hex = stored_hash.split('$', 1)
            salt = binascii.unhexlify(salt_hex)
            expected = binascii.unhexlify(hash_hex)
        except (ValueError, binascii.Error):
            return False
        derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
        return hmac.compare_digest(derived, expected)

    def verify_user(self, username, password):
        """بررسی اطلاعات ورود؛ در صورت موفقیت با فرمت قدیمی، هش را به‌روزرسانی می‌کند"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username=?",
                (username,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            stored_hash = row[0]
            if not self._verify_password(password, stored_hash):
                return False

            if '$' not in stored_hash:
                # ارتقای خودکار هش قدیمی و ناامن به فرمت جدید PBKDF2
                new_hash = self._hash_password(password)
                cursor.execute(
                    "UPDATE users SET password_hash=? WHERE username=?",
                    (new_hash, username)
                )
                self.conn.commit()

            return True
        except Exception:
            return False

    def user_exists(self, username):
        """بررسی وجود کاربر"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
            return cursor.fetchone() is not None
        except Exception:
            return False

    def create_user(self, username, password):
        """ایجاد کاربر جدید"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, self._hash_password(password))
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def set_current_user(self, username):
        """تنظیم کاربر فعلی"""
        self.current_user = username

    def get_user_name(self):
        """دریافت نام نمایشی کاربر"""
        if not self.current_user:
            return ""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT value FROM user_info WHERE username=? AND key='name'",
                (self.current_user,)
            )
            row = cursor.fetchone()
            return row[0] if row else ""
        except Exception:
            return ""

    def save_conversation(self, role, message):
        """ذخیره مکالمه"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (username, role, message) VALUES (?, ?, ?)",
                (self.current_user or 'guest', role, message)
            )
            self.conn.commit()
        except Exception:
            pass

    def get_recent_conversations(self, limit=50):
        """دریافت مکالمات اخیر"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """SELECT role, message, timestamp FROM conversations
                   WHERE username=? ORDER BY id DESC LIMIT ?""",
                (self.current_user or 'guest', limit)
            )
            rows = cursor.fetchall()
            return [{'role': r[0], 'message': r[1], 'time': r[2]} for r in reversed(rows)]
        except Exception:
            return []

    def remember(self, key, value):
        """ذخیره اطلاعات شخصی"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO user_info (username, key, value, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (self.current_user or 'guest', key, value, datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception:
            pass

    def recall(self, key):
        """یادآوری اطلاعات"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT value FROM user_info WHERE username=? AND key=?",
                (self.current_user or 'guest', key)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def save_note(self, note, category='general'):
        """ذخیره یادداشت"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO notes (username, note, category) VALUES (?, ?, ?)",
                (self.current_user or 'guest', note, category)
            )
            self.conn.commit()
        except Exception:
            pass

    def get_notes(self, category=None):
        """دریافت یادداشت‌ها"""
        try:
            cursor = self.conn.cursor()
            if category:
                cursor.execute(
                    "SELECT note, category, created_at FROM notes WHERE username=? AND category=? ORDER BY id DESC",
                    (self.current_user or 'guest', category)
                )
            else:
                cursor.execute(
                    "SELECT note, category, created_at FROM notes WHERE username=? ORDER BY id DESC",
                    (self.current_user or 'guest',)
                )
            return [{'note': r[0], 'category': r[1], 'time': r[2]} for r in cursor.fetchall()]
        except Exception:
            return []

    def add_reminder(self, message, reminder_time=None):
        """افزودن یادآوری"""
        try:
            if reminder_time is None:
                reminder_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
            elif isinstance(reminder_time, datetime):
                reminder_time = reminder_time.strftime('%Y-%m-%d %H:%M')

            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (username, message, time) VALUES (?, ?, ?)",
                (self.current_user or 'guest', message, reminder_time)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_pending_reminders(self):
        """دریافت یادآوری‌های انجام‌نشده"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            cursor.execute(
                """SELECT id, message, time FROM reminders
                   WHERE username=? AND is_done=0 AND time<=?""",
                (self.current_user or 'guest', now)
            )
            return [{'id': r[0], 'message': r[1], 'time': r[2]} for r in cursor.fetchall()]
        except Exception:
            return []

    def mark_reminder_done(self, reminder_id):
        """علامت یادآوری به عنوان انجام شده"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE reminders SET is_done=1 WHERE id=?", (reminder_id,))
            self.conn.commit()
        except Exception:
            pass

    def save_pattern(self, pattern_type, pattern_data):
        """ذخیره الگوی رفتاری"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO behavioral_patterns (username, pattern_type, pattern_data)
                   VALUES (?, ?, ?)""",
                (self.current_user or 'guest', pattern_type, json.dumps(pattern_data, ensure_ascii=False))
            )
            self.conn.commit()
        except Exception:
            pass

    def get_patterns(self, pattern_type=None):
        """دریافت الگوهای رفتاری"""
        try:
            cursor = self.conn.cursor()
            if pattern_type:
                cursor.execute(
                    "SELECT pattern_type, pattern_data, frequency FROM behavioral_patterns WHERE username=? AND pattern_type=?",
                    (self.current_user or 'guest', pattern_type)
                )
            else:
                cursor.execute(
                    "SELECT pattern_type, pattern_data, frequency FROM behavioral_patterns WHERE username=?",
                    (self.current_user or 'guest',)
                )
            return [{'type': r[0], 'data': json.loads(r[1]), 'freq': r[2]} for r in cursor.fetchall()]
        except Exception:
            return []

    def save_preference(self, key, value, confidence=1.0):
        """ذخیره ترجیح"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO preferences (username, key, value, confidence, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.current_user or 'guest', key, value, confidence, datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception:
            pass

    def get_preferences(self):
        """دریافت تمام ترجیحات"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT key, value, confidence FROM preferences WHERE username=?",
                (self.current_user or 'guest',)
            )
            return {r[0]: {'value': r[1], 'confidence': r[2]} for r in cursor.fetchall()}
        except Exception:
            return {}

    def analyze_and_store_preferences(self, text):
        """تحلیل و ذخیره ترجیحات از متن کاربر"""
        text_lower = text.lower()

        name_patterns = ['اسم من', 'من اسمم', 'نام من']
        for p in name_patterns:
            if p in text_lower:
                idx = text_lower.index(p) + len(p)
                name = text[idx:].strip().split()[0] if text[idx:].strip() else ""
                if name:
                    self.remember('name', name)
                    return

        favorite_patterns = ['دوست دارم', 'علاقه دارم', 'می‌پسندم', 'عاشق']
        for p in favorite_patterns:
            if p in text_lower:
                idx = text_lower.index(p) + len(p)
                item = text[idx:].strip()
                if item:
                    self.save_preference('likes', item)
                    return

        dislike_patterns = ['دوست ندارم', 'بیزارم', 'نفرت دارم']
        for p in dislike_patterns:
            if p in text_lower:
                idx = text_lower.index(p) + len(p)
                item = text[idx:].strip()
                if item:
                    self.save_preference('dislikes', item)
                    return

    def get_context(self):
        """دریافت زمینه برای مدل"""
        context_parts = []

        name = self.get_user_name()
        if name:
            context_parts.append(f"نام کاربر: {name}")

        prefs = self.get_preferences()
        if prefs:
            prefs_text = ", ".join([f"{k}: {v['value']}" for k, v in prefs.items()])
            context_parts.append(f"ترجیحات: {prefs_text}")

        recent = self.get_recent_conversations(10)
        if recent:
            history_text = "\n".join([f"{'کاربر' if r['role'] == 'user' else 'وینا'}: {r['message']}" for r in recent])
            context_parts.append(f"آخرین مکالمات:\n{history_text}")

        return "\n".join(context_parts)

    def get_personality(self):
        """دریافت اطلاعات شخصیتی"""
        return {
            'name': self.get_user_name(),
            'preferences': self.get_preferences(),
            'notes_count': len(self.get_notes()),
            'patterns_count': len(self.get_patterns()),
        }

    def get_stats(self):
        """آمار حافظه"""
        try:
            cursor = self.conn.cursor()
            stats = {}
            for table in ['conversations', 'notes', 'reminders', 'user_info', 'preferences']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            return stats
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # تنظیمات سراسری برنامه (مستقل از کاربر) - مثلاً وضعیت مشاهده‌ی onboarding
    # ------------------------------------------------------------------
    def set_flag(self, key, value):
        """ذخیره‌ی یک تنظیم سراسری برنامه (نه مختص یک کاربر خاص)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_flag(self, key, default=None):
        """خواندن یک تنظیم سراسری برنامه"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key=?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default
        except Exception:
            return default

    # ------------------------------------------------------------------
    # مدیریت حافظه (برای صفحه‌ی «تنظیمات > حافظه») - مشاهده، پاک‌سازی،
    # خروجی‌گیری (export) و وارد کردن (import) داده‌های کاربر
    # ------------------------------------------------------------------
    def get_memory_summary(self):
        """خلاصه‌ی وضعیت حافظه برای نمایش در صفحه‌ی تنظیمات"""
        stats = self.get_stats()
        return {
            'conversations_count': stats.get('conversations', 0),
            'notes_count': stats.get('notes', 0),
            'reminders_count': stats.get('reminders', 0),
            'preferences_count': stats.get('preferences', 0),
            'db_size_kb': self._get_db_size_kb(),
        }

    def _get_db_size_kb(self):
        try:
            return round(os.path.getsize(self.db_path) / 1024, 1)
        except OSError:
            return 0

    def clear_conversation_history(self, username=None):
        """پاک کردن تاریخچه‌ی مکالمات یک کاربر (یا کاربر فعلی)"""
        target_user = username or self.current_user or 'guest'
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE username=?", (target_user,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def clear_all_memory(self, username=None):
        """پاک کردن کامل حافظه‌ی یک کاربر: مکالمات، یادداشت‌ها، یادآوری‌ها،
        اطلاعات شخصی و ترجیحات (برای «پاک کردن کامل حافظه» در تنظیمات)"""
        target_user = username or self.current_user or 'guest'
        try:
            cursor = self.conn.cursor()
            for table in ('conversations', 'notes', 'reminders', 'user_info',
                          'preferences', 'behavioral_patterns'):
                cursor.execute(f"DELETE FROM {table} WHERE username=?", (target_user,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def export_memory(self, username=None):
        """خروجی‌گیری از تمام داده‌های یک کاربر به‌صورت دیکشنری قابل تبدیل به JSON"""
        target_user = username or self.current_user or 'guest'
        try:
            cursor = self.conn.cursor()
            data = {'username': target_user, 'exported_at': datetime.now().isoformat()}

            cursor.execute(
                "SELECT role, message, timestamp FROM conversations WHERE username=? ORDER BY id",
                (target_user,)
            )
            data['conversations'] = [
                {'role': r[0], 'message': r[1], 'time': r[2]} for r in cursor.fetchall()
            ]

            cursor.execute(
                "SELECT note, category, created_at FROM notes WHERE username=? ORDER BY id",
                (target_user,)
            )
            data['notes'] = [
                {'note': r[0], 'category': r[1], 'time': r[2]} for r in cursor.fetchall()
            ]

            cursor.execute(
                "SELECT key, value FROM user_info WHERE username=?", (target_user,)
            )
            data['user_info'] = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute(
                "SELECT key, value, confidence FROM preferences WHERE username=?", (target_user,)
            )
            data['preferences'] = [
                {'key': r[0], 'value': r[1], 'confidence': r[2]} for r in cursor.fetchall()
            ]

            return data
        except Exception as exc:
            print(f"خطا در خروجی‌گیری از حافظه: {exc}")
            return None

    def export_memory_to_file(self, file_path, username=None):
        """ذخیره‌ی خروجی حافظه در یک فایل JSON"""
        data = self.export_memory(username)
        if data is None:
            return False
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError as exc:
            print(f"خطا در نوشتن فایل خروجی: {exc}")
            return False

    def import_memory_from_file(self, file_path, username=None):
        """وارد کردن داده‌های حافظه از یک فایل JSON که قبلاً export شده"""
        target_user = username or self.current_user or 'guest'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"خطا در خواندن فایل ورودی: {exc}")
            return False

        try:
            for conv in data.get('conversations', []):
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO conversations (username, role, message) VALUES (?, ?, ?)",
                    (target_user, conv.get('role', 'user'), conv.get('message', ''))
                )
            for note in data.get('notes', []):
                self.save_note(note.get('note', ''), note.get('category', 'general'))
            for key, value in data.get('user_info', {}).items():
                self.remember(key, value)
            for pref in data.get('preferences', []):
                self.save_preference(
                    pref.get('key', ''), pref.get('value', ''), pref.get('confidence', 1.0)
                )
            self.conn.commit()
            return True
        except Exception as exc:
            print(f"خطا در وارد کردن حافظه: {exc}")
            return False
