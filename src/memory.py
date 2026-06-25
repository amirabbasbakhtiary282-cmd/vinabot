# -*- coding: utf-8 -*-
"""
ماژول حافظه دائمی وینا
مدیریت SQLite برای ذخیره مکالمات، اطلاعات، یادآوری‌ها و الگوها
"""

import os
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta


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

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_user ON reminders(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_user ON behavioral_patterns(username)')

            self.conn.commit()
        except Exception as e:
            print(f"خطا در ایجاد دیتابیس: {e}")

    def _hash_password(self, password):
        """هش کردن رمز عبور"""
        salt = "vina_ai_salt_2026"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_user(self, username, password):
        """بررسی اطلاعات ورود"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username=?",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return row[0] == self._hash_password(password)
            return False
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
