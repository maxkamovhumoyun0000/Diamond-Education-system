import sqlite3
import threading
import logging
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import DB_PATH
from logging_config import get_logger

logger = get_logger(__name__)
Path('data').mkdir(parents=True, exist_ok=True)
DB_WRITE_LOCK = threading.Lock()

def get_conn():
    logger.debug("db.get_conn()")
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Birinchi marta ishga tushganda tablelarni yaratadi (sqlite3)."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        password_used INTEGER DEFAULT 0,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT,
        subject TEXT NOT NULL,
        telegram_id TEXT UNIQUE,
        login_type INTEGER DEFAULT 1,
        level TEXT,
        access_enabled INTEGER DEFAULT 0,
        access_expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        failed_logins INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        test_in_progress INTEGER DEFAULT 0,
        test_subject TEXT,
        test_question_index INTEGER DEFAULT 0,
        test_score INTEGER DEFAULT 0,
        test_questions TEXT,
        pending_approval INTEGER DEFAULT 0
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT,
        score INTEGER,
        max_score INTEGER DEFAULT 100,
        level TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # Guruhlar jadvali
    cur.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        teacher_id INTEGER,
        level TEXT,
        lesson_date TEXT,
        lesson_start TEXT,
        lesson_end TEXT,
        tz TEXT DEFAULT 'Asia/Tashkent',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(teacher_id) REFERENCES users(id)
    )
    ''')

    # Davomat jadvali
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT DEFAULT 'Absent',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # User-group join table for multi-group students
    cur.execute('''
    CREATE TABLE IF NOT EXISTS user_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, group_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # Monthly payments with optional group scope
    cur.execute('''
    CREATE TABLE IF NOT EXISTS monthly_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        ym TEXT NOT NULL,
        group_id INTEGER,
        subject TEXT,
        paid INTEGER DEFAULT 0,
        paid_at TEXT,
        notified_days TEXT,
        UNIQUE(user_id, ym, group_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # Migratsiya jadvali
    cur.execute('''
    CREATE TABLE IF NOT EXISTS _migrations (
        name TEXT PRIMARY KEY,
        applied_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Vocabulary tables
    cur.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        subject TEXT NOT NULL,
        language TEXT NOT NULL,
        level TEXT,
        translation_uz TEXT,
        translation_ru TEXT,
        definition TEXT,
        example TEXT,
        added_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(added_by) REFERENCES users(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS vocabulary_imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        added_by INTEGER,
        subject TEXT NOT NULL,
        language TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(added_by) REFERENCES users(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        preferred_translation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()
    logger.info(f"✅ diamond.db yaratildi: {DB_PATH}")
    dedupe_tests()
    apply_migrations()
    ensure_monthly_payments_table()
    ensure_grammar_attempts_table()


def set_pending_approval(user_id, pending=True):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET pending_approval=? WHERE id=?", (1 if pending else 0, user_id))
    conn.commit()
    conn.close()


def apply_migrations():
    """Yangi ustunlarni qo'shish uchun migratsiyani ishga tushirish"""
    conn = get_conn()
    cur = conn.cursor()
    
    # pending_approval ustunini qo'shish
    try:
        cur.execute("ALTER TABLE users ADD COLUMN pending_approval INTEGER DEFAULT 0")
        logger.info("Migrasiya: pending_approval ustuni qo'shildi")
    except Exception:
        pass
    
    # group_id ustunini qo'shish
    try:
        cur.execute("ALTER TABLE users ADD COLUMN group_id INTEGER")
        logger.info("Migrasiya: group_id ustuni qo'shildi")
    except Exception:
        pass  # Agar ustun allaqachon bor bo'lsa, xato chiqmaydi
    
    # diamonds ustunini qo'shish
    try:
        cur.execute("ALTER TABLE users ADD COLUMN diamonds INTEGER DEFAULT 0")
        logger.info("Migrasiya: diamonds ustuni qo'shildi")
    except Exception:
        pass
    
    # last_diamond_update ustunini qo'shish
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_diamond_update TEXT")
        logger.info("Migrasiya: last_diamond_update ustuni qo'shildi")
    except Exception:
        pass

    # language ustunini qo'shish (foydalanuvchi tilini saqlash uchun)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uz'")
        logger.info("Migrasiya: language ustuni qo'shildi")
    except Exception:
        pass
    
    # diamond_history table for tracking D'coin changes
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diamond_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                diamonds_change REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        logger.info("Migrasiya: diamond_history table created")
    except Exception:
        pass
    
    # feedback table for anonymous student feedback
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                feedback_text TEXT NOT NULL,
                is_anonymous BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        logger.info("Migrasiya: feedback table created")
    except Exception:
        pass
    
    # test_history table for tracking test statistics
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                topic_id TEXT,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        logger.info("Migrasiya: test_history table created")
    except Exception:
        pass
    
    # persistent login tracking
    for col, ddl in (
        ("logged_in", "ALTER TABLE users ADD COLUMN logged_in INTEGER DEFAULT 0"),
        ("last_login_at", "ALTER TABLE users ADD COLUMN last_login_at TEXT"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: users.{col} ustuni qo'shildi")
        except Exception:
            pass

    # groups schedule columns
    for col, ddl in (
        ("subject", "ALTER TABLE groups ADD COLUMN subject TEXT"),
        ("lesson_date", "ALTER TABLE groups ADD COLUMN lesson_date TEXT"),
        ("lesson_start", "ALTER TABLE groups ADD COLUMN lesson_start TEXT"),
        ("lesson_end", "ALTER TABLE groups ADD COLUMN lesson_end TEXT"),
        ("tz", "ALTER TABLE groups ADD COLUMN tz TEXT DEFAULT 'Asia/Tashkent'"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: groups.{col} ustuni qo'shildi")
        except Exception:
            pass

    # monthly_payments table columns for per-group payment support
    for col, ddl in (
        ("group_id", "ALTER TABLE monthly_payments ADD COLUMN group_id INTEGER"),
        ("subject", "ALTER TABLE monthly_payments ADD COLUMN subject TEXT"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: monthly_payments.{col} ustuni qo'shildi")
        except Exception:
            pass

    try:
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym_group ON monthly_payments(user_id, ym, group_id)')
        logger.info("Migrasiya: ux_monthly_payments_user_ym_group indeksi qo'shildi")
    except Exception:
        pass

    try:
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym ON monthly_payments(user_id, ym)')
        logger.info("Migrasiya: ux_monthly_payments_user_ym indeksi qo'shildi")
    except Exception:
        pass

    # attendance sessions table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        opened_by TEXT,
        opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
        closed_at TEXT,
        notified_admin INTEGER DEFAULT 0,
        notified_teacher INTEGER DEFAULT 0,
        UNIQUE(group_id, date),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # attendance_sessions: add separate pre/post notification flags
    for col, ddl in (
        ("notified_admin_pre", "ALTER TABLE attendance_sessions ADD COLUMN notified_admin_pre INTEGER DEFAULT 0"),
        ("notified_admin_post", "ALTER TABLE attendance_sessions ADD COLUMN notified_admin_post INTEGER DEFAULT 0"),
        ("notified_teacher_pre", "ALTER TABLE attendance_sessions ADD COLUMN notified_teacher_pre INTEGER DEFAULT 0"),
        ("notified_teacher_post", "ALTER TABLE attendance_sessions ADD COLUMN notified_teacher_post INTEGER DEFAULT 0"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: attendance_sessions.{col} ustuni qo'shildi")
        except Exception:
            pass

    # Backfill new post flags from legacy notified_* so we don't re-notify old sessions
    try:
        cur.execute(
            "UPDATE attendance_sessions SET notified_admin_post=1 WHERE notified_admin=1 AND COALESCE(notified_admin_post,0)=0"
        )
    except Exception:
        pass
    try:
        cur.execute(
            "UPDATE attendance_sessions SET notified_teacher_post=1 WHERE notified_teacher=1 AND COALESCE(notified_teacher_post,0)=0"
        )
    except Exception:
        pass
    
    conn.commit()
    conn.close()


def ensure_monthly_payments_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS monthly_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        ym TEXT NOT NULL, -- YYYY-MM
        group_id INTEGER,
        subject TEXT,
        paid INTEGER DEFAULT 0,
        paid_at TEXT,
        notified_days TEXT, -- comma-separated days e.g. "1,5,15"
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym_group ON monthly_payments(user_id, ym, group_id)')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym ON monthly_payments(user_id, ym)')
    conn.commit()
    conn.close()


def ensure_grammar_attempts_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS grammar_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic_id TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        last_attempt_at TEXT,
        UNIQUE(user_id, topic_id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    conn.commit()
    conn.close()


def dedupe_tests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM tests
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM tests
            GROUP BY subject, question, option_a, option_b, option_c, option_d, correct_option
        )
    ''')
    conn.commit()
    conn.close()


def prepare_user_for_new_test(user_id, subject):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''
            UPDATE users
            SET subject=?, login_type=1, access_enabled=0, password_used=0
            WHERE id=?
        ''', (subject, user_id))
        conn.commit()
        conn.close()


# ====================== ASOSIY FUNKSIYALAR ======================

def create_user(first_name, last_name, phone, subject, login_type):
    logger.info(f"db.create_user(login_type={login_type}, subject={subject}, first_name={first_name}, last_name={last_name})")
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Login ID va parol generatsiya
        import random, string
        while True:
            login_id = 'ST' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            cur.execute("SELECT 1 FROM users WHERE login_id=?", (login_id,))
            if not cur.fetchone(): break

        password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        cur.execute('''
            INSERT INTO users (login_id, password, first_name, last_name, phone, subject, login_type, blocked, access_enabled)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (login_id, password, first_name, last_name, phone, subject, login_type, 1 if login_type == 2 else 0, 1 if login_type == 3 else 0))
        conn.commit()
        return {'id': cur.lastrowid, 'login_id': login_id, 'password': password}
    finally:
        conn.close()

def verify_login(login_id, password):
    logger.info(f"db.verify_login(login_id={login_id})")
    conn = get_conn()
    cur = conn.cursor()
    login_id_clean = login_id.strip().upper()
    cur.execute("SELECT * FROM users WHERE UPPER(login_id)=?", (login_id_clean,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return None, 'not_found'
    if user['blocked']:
        return None, 'blocked'
    if user['password'] != password or user['password_used']:
        return None, 'invalid'
    return dict(user), 'ok'

def activate_user(user_id, telegram_id):
    logger.info(f"db.activate_user(user_id={user_id}, telegram_id={telegram_id})")
    with DB_WRITE_LOCK:
        conn = get_conn()
        try:
            cur = conn.cursor()
            # Remove telegram_id from any other user so UNIQUE is preserved
            cur.execute("UPDATE users SET telegram_id=NULL WHERE telegram_id=? AND id!=?", (telegram_id, user_id))
            cur.execute('''
                UPDATE users SET telegram_id=?, password_used=1, failed_logins=0, logged_in=1, last_login_at=CURRENT_TIMESTAMP, last_activity=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (telegram_id, user_id))
            conn.commit()
        finally:
            conn.close()


def block_user(user_id):
    """Block user by setting blocked=1"""
    logger.info(f"db.block_user(user_id={user_id})")
    with DB_WRITE_LOCK:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET blocked=1 WHERE id=?", (user_id,))
            conn.commit()
        finally:
            conn.close()


def unblock_user(user_id):
    """Unblock user by setting blocked=0"""
    logger.info(f"db.unblock_user(user_id={user_id})")
    with DB_WRITE_LOCK:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET blocked=0 WHERE id=?", (user_id,))
            conn.commit()
        finally:
            conn.close()


def logout_user_by_telegram(telegram_id: str):
    """User-initiated logout: unlink telegram_id so they can login again."""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        # Clear telegram link and allow re-login with the same login/password if needed
        cur.execute(
            "UPDATE users SET telegram_id=NULL, is_logged_in=0, password_used=0 WHERE telegram_id=?",
            (telegram_id,)
        )
        conn.commit()
        conn.close()


def update_user_telegram_id(user_id: int, telegram_id: str):
    """Update user's telegram_id"""
    import sqlite3
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET telegram_id=? WHERE id=?", (telegram_id, user_id))
            conn.commit()
            logger.info(f"db.update_user_telegram_id: set telegram_id={telegram_id} for user_id={user_id}")
        except sqlite3.IntegrityError:
            # This happens when telegram_id UNIQUE constraint is violated
            logger.warning(f"db.update_user_telegram_id: telegram_id {telegram_id} already used by another user")
            conn.rollback()
            raise
        except Exception:
            logger.exception("db.update_user_telegram_id: unexpected error")
            conn.rollback()
            raise
        finally:
            conn.close()

def enable_access(user_id, days=None):
    logger.info(f"db.enable_access(user_id={user_id}, days={days})")
    conn = get_conn()
    cur = conn.cursor()
    if days is None:
        cur.execute("UPDATE users SET access_enabled=1, access_expires_at=NULL, blocked=0 WHERE id=?", (user_id,))
    else:
        from datetime import datetime, timedelta
        expires = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("UPDATE users SET access_enabled=1, access_expires_at=?, blocked=0 WHERE id=?", (expires, user_id))
    conn.commit()
    conn.close()

def disable_access(user_id):
    logger.info(f"db.disable_access(user_id={user_id})")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET access_enabled=0, access_expires_at=NULL, blocked=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

def is_access_active(user):
    if not user or not user.get('access_enabled'):
        return False
    expires = user.get('access_expires_at')
    if not expires:
        return True
    from datetime import datetime
    try:
        expires_dt = datetime.strptime(expires, '%Y-%m-%d %H:%M:%S')
        return datetime.utcnow() <= expires_dt
    except Exception:
        return False

def reset_user_password(user_id, password):
    logger.info(f"db.reset_user_password(user_id={user_id})")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password=?, password_used=0 WHERE id=?", (password, user_id))
    conn.commit()
    conn.close()


def update_user_language(user_id, lang):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET language=? WHERE id=?", (lang, user_id))
    conn.commit()
    conn.close()


def update_user_subjects(user_id: int, subjects_list: list):
    """Update user's subjects as comma separated string"""
    subjects_str = ','.join(subjects_list)
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET subject=? WHERE id=?", (subjects_str, user_id))
        conn.commit()
        conn.close()


def update_user_subject(user_id: int, subject: str):
    """Update user's subject"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET subject=? WHERE id=?", (subject, user_id))
        conn.commit()
        conn.close()


def set_user_language(user_id: int, lang: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET language=? WHERE id=?", (lang, user_id))
    conn.commit()
    conn.close()


def update_user_level(user_id: int, level: str):
    """Update user's level"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET level=? WHERE id=?", (level, user_id))
        conn.commit()
        conn.close()

def set_user_language_by_telegram(telegram_id, lang):
    conn = get_conn()
    cur = conn.cursor()
    # Try matching stored telegram_id as given
    cur.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
    row = cur.fetchone()
    # If not found, try integer version (some records may store integers)
    if not row:
        try:
            maybe_int = int(telegram_id)
            cur.execute("SELECT id FROM users WHERE telegram_id=?", (maybe_int,))
            row = cur.fetchone()
        except Exception:
            row = None

    if not row:
        conn.close()
        return False
    uid = row['id']
    cur.execute("UPDATE users SET language=? WHERE id=?", (lang, uid))
    conn.commit()
    conn.close()
    return True

def get_user_by_telegram(telegram_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    row = cur.fetchone()
    # Fallback: maybe telegram_id stored as integer in some rows
    if not row:
        try:
            maybe_int = int(telegram_id)
            cur.execute("SELECT * FROM users WHERE telegram_id=?", (maybe_int,))
            row = cur.fetchone()
        except Exception:
            row = None
    conn.close()
    return dict(row) if row else None

def get_user_by_login(login_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE UPPER(login_id)=?", (login_id.strip().upper(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_login_id(login_id):
    return get_user_by_login(login_id)

def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_placement_session(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT test_in_progress, test_subject, test_question_index, test_score, test_questions FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    questions = []
    if row['test_questions']:
        try:
            import json
            questions = json.loads(row['test_questions'])
        except Exception:
            questions = []
    return {
        'active': bool(row['test_in_progress']),
        'subject': row['test_subject'],
        'question_index': row['test_question_index'] or 0,
        'score': row['test_score'] or 0,
        'questions': questions,
    }


def save_placement_session(user_id, session):
    conn = get_conn()
    cur = conn.cursor()
    import json
    questions_json = json.dumps(session.get('questions', []))
    cur.execute('''
        UPDATE users SET test_in_progress=?, test_subject=?, test_question_index=?, test_score=?, test_questions=?
        WHERE id=?
    ''', (
        1 if session.get('active') else 0,
        session.get('subject'),
        session.get('question_index', 0),
        session.get('score', 0),
        questions_json,
        user_id,
    ))
    conn.commit()
    conn.close()


def clear_placement_session(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        UPDATE users SET test_in_progress=0, test_subject=NULL, test_question_index=0, test_score=0, test_questions=NULL
        WHERE id=?
    ''', (user_id,))
    conn.commit()
    conn.close()


def get_tests_by_subject(subject):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tests WHERE subject=?", (subject,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
def delete_all_tests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tests")
    conn.commit()
    conn.close()

def delete_tests_by_subject(subject: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM tests WHERE subject=?", (subject,))
    conn.commit()
    conn.close()
def get_test_by_id(test_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tests WHERE id=?", (test_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_test_by_subject_and_question(subject, question):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tests WHERE subject=? AND question=?", (subject, question))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def save_test_result(user_id, subject, score, level):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO test_results (user_id, subject, score, level)
            VALUES (?,?,?,?)
        ''', (user_id, subject, score, level))
        conn.commit()
        conn.close()

def insert_test(subject, question, option_a, option_b, option_c, option_d, correct_option):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO tests (subject, question, option_a, option_b, option_c, option_d, correct_option)
        VALUES (?,?,?,?,?,?,?)
    ''', (subject, question, option_a, option_b, option_c, option_d, correct_option))
    conn.commit()
    conn.close()

def has_tests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tests LIMIT 1")
    result = cur.fetchone()
    conn.close()
    return result is not None


def get_test_count():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tests")
    row = cur.fetchone()
    conn.close()
    return row['c'] if row else 0


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_all_teachers():
    """Get all users with login_type=3 (teachers)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE login_type=3 ORDER BY created_at DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_all_students():
    """Get all users with login_type=2 (students)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE login_type=2 ORDER BY created_at DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_recent_results():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM test_results ORDER BY created_at DESC LIMIT 20")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_recent_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 50")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


# ====================== GURUHLAR BOSHQARUVI ======================

def create_group(name, teacher_id, level='All', subject=None, lesson_date=None, lesson_start=None, lesson_end=None, tz='Asia/Tashkent'):
    """Yangi guruhi yaratish"""
    logger.info(f"create_group called with: name={name}, teacher_id={teacher_id}, level={level}, subject={subject}, lesson_date={lesson_date}, lesson_start={lesson_start}, lesson_end={lesson_end}, tz={tz}")
    
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO groups (name, teacher_id, level, subject, lesson_date, lesson_start, lesson_end, tz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, teacher_id, level, subject, lesson_date, lesson_start, lesson_end, tz))
        conn.commit()
        group_id = cur.lastrowid
        conn.close()
        
        logger.info(f"Group created successfully with ID={group_id}")
        return group_id

def get_group(group_id):
    """Guruhni ID bo'yicha olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM groups WHERE id=?", (group_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_groups_by_teacher(teacher_id):
    """O'qituvchining barcha guruhlarini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM groups WHERE teacher_id=? ORDER BY name", (teacher_id,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_all_groups():
    """Barcha guruhlarni olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM groups ORDER BY name")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def add_user_to_group(user_id, group_id):
    """O'quvchini guruhga qo'shish (multi-group support)"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        
        # Add to user_groups table
        try:
            cur.execute("INSERT INTO user_groups (user_id, group_id) VALUES (?, ?)", (user_id, group_id))
        except sqlite3.IntegrityError:
            # User already in this group
            conn.close()
            return
        
        # Legacy support (old column)
        cur.execute("UPDATE users SET group_id=? WHERE id=?", (group_id, user_id))
        
        # Update user's level based on this group (keep highest level)
        cur.execute("SELECT level FROM groups WHERE id=?", (group_id,))
        gr = cur.fetchone()
        group_level = (gr["level"] if gr else None)
        
        if group_level:
            # Get current user level
            cur.execute("SELECT level FROM users WHERE id=?", (user_id,))
            user = cur.fetchone()
            current_level = user["level"] if user and user["level"] else None
            
            # Update if this is a higher level or user has no level
            if not current_level or is_higher_level(group_level, current_level):
                cur.execute("UPDATE users SET level=? WHERE id=?", (group_level, user_id))
        
        conn.commit()
        conn.close()


def add_user_to_group_legacy(user_id, group_id):
    """Eski usul - faqat bitta guruh (backward compatibility)"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        # group determines student's current level
        cur.execute("SELECT level FROM groups WHERE id=?", (group_id,))
        gr = cur.fetchone()
        group_level = (gr["level"] if gr else None)
        if group_level:
            cur.execute("UPDATE users SET group_id=?, level=? WHERE id=?", (group_id, group_level, user_id))
        else:
            cur.execute("UPDATE users SET group_id=? WHERE id=?", (group_id, user_id))
        conn.commit()
        conn.close()


def update_group_days(group_id, days):
    """Update group lesson days"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE groups SET lesson_days=? WHERE id=?", (days, group_id))
        conn.commit()
        conn.close()


def is_higher_level(new_level, current_level):
    """Yangi level avvalgisidan yuqorimi"""
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1']
    try:
        new_idx = level_order.index(new_level)
        current_idx = level_order.index(current_level)
        return new_idx > current_idx
    except ValueError:
        return True


def get_user_groups(user_id):
    """Foydalanuvchining barcha guruhlarini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT g.* FROM groups g
        JOIN user_groups ug ON g.id = ug.group_id
        WHERE ug.user_id = ?
    ''', (user_id,))
    groups = [dict(row) for row in cur.fetchall()]
    conn.close()
    return groups


def check_user_group_access(user_id: int) -> bool:
    """Check if user is in any group"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) as count FROM user_groups ug
        JOIN groups g ON ug.group_id = g.id
        WHERE ug.user_id = ?
    ''', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result['count'] > 0 if result else False


def auto_block_users_not_in_groups():
    """Automatically block users who are not in any active group"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Find users who are logged in but not in any active group
    cur.execute('''
        UPDATE users 
        SET blocked = 1, last_activity = CURRENT_TIMESTAMP
        WHERE login_type = 2 
        AND blocked = 0 
        AND logged_in = 1
        AND id NOT IN (
            SELECT DISTINCT ug.user_id 
            FROM user_groups ug 
            JOIN groups g ON ug.group_id = g.id 
            WHERE g.active = 1
        )
    ''')
    
    blocked_count = cur.rowcount
    conn.commit()
    conn.close()
    
    logger.info(f"Auto-blocked {blocked_count} users not in active groups")
    return blocked_count


def auto_unblock_users_in_groups():
    """Automatically unblock users who are in active groups (only if manually unblocked by admin first)"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Only unblock users who were manually unblocked by admin (blocked = 0) and are in active groups
    cur.execute('''
        UPDATE users 
        SET last_activity = CURRENT_TIMESTAMP
        WHERE login_type = 2 
        AND blocked = 0 
        AND logged_in = 1
        AND id IN (
            SELECT DISTINCT ug.user_id 
            FROM user_groups ug 
            JOIN groups g ON ug.group_id = g.id 
            WHERE g.active = 1
        )
    ''')
    
    unblocked_count = cur.rowcount
    conn.commit()
    conn.close()
    
    logger.info(f"Auto-updated activity for {unblocked_count} users in active groups")
    return unblocked_count


def get_user_subjects(user_id):
    """Foydalanuvchining barcha fanlarini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT g.subject FROM groups g
        JOIN user_groups ug ON g.id = ug.group_id
        WHERE ug.user_id = ? AND g.subject IS NOT NULL
    """, (user_id,))
    subjects = [row["subject"] for row in cur.fetchall()]
    conn.close()
    return subjects


def remove_user_from_group(user_id: int, group_id: int):
    """Foydalanuvchini guruhdan olib tashlash (multi-group)"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_groups WHERE user_id=? AND group_id=?", (user_id, group_id))
        
        # Legacy support: clear old column if removing from this specific group
        cur.execute("UPDATE users SET group_id=NULL WHERE id=? AND group_id=?", (user_id, group_id))
        
        # If user has no more groups, recalculate level
        cur.execute("SELECT COUNT(*) as count FROM user_groups WHERE user_id=?", (user_id,))
        count = cur.fetchone()["count"]
        
        if count == 0:
            # User has no more groups, level can be kept as is or cleared based on preference
            pass
        else:
            # Update to highest remaining group level
            cur.execute("""
                SELECT g.level FROM groups g
                JOIN user_groups ug ON g.id = ug.group_id
                WHERE ug.user_id = ?
                ORDER BY 
                    CASE g.level
                        WHEN 'A1' THEN 1
                        WHEN 'A2' THEN 2
                        WHEN 'B1' THEN 3
                        WHEN 'B2' THEN 4
                        WHEN 'C1' THEN 5
                    END DESC
                LIMIT 1
            """, (user_id,))
            result = cur.fetchone()
            if result:
                cur.execute("UPDATE users SET level=? WHERE id=?", (result["level"], user_id))
        
        conn.commit()
        conn.close()


def update_group_name(group_id: int, name: str):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE groups SET name=? WHERE id=?", (name, group_id))
        conn.commit()
        conn.close()


def update_group_level(group_id: int, level: str, sync_students: bool = True):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE groups SET level=? WHERE id=?", (level, group_id))
        if sync_students:
            cur.execute("UPDATE users SET level=? WHERE group_id=?", (level, group_id))
        conn.commit()
        conn.close()


def update_group_teacher(group_id: int, teacher_id: int):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE groups SET teacher_id=? WHERE id=?", (teacher_id, group_id))
        conn.commit()
        conn.close()


def update_group_schedule(group_id: int, lesson_date: str | None, lesson_start: str | None, lesson_end: str | None, tz: str | None = None):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE groups SET lesson_date=?, lesson_start=?, lesson_end=?, tz=COALESCE(?, tz) WHERE id=?",
            (lesson_date, lesson_start, lesson_end, tz, group_id),
        )
        conn.commit()
        conn.close()


def update_group_subject(group_id: int, subject: str | None):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE groups SET subject=? WHERE id=?", (subject, group_id))
        conn.commit()
        conn.close()


def delete_group(group_id: int):
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        # Unlink students first
        cur.execute("UPDATE users SET group_id=NULL WHERE group_id=?", (group_id,))
        cur.execute("DELETE FROM groups WHERE id=?", (group_id,))
        conn.commit()
        conn.close()


def _ym_now():
    from datetime import datetime
    import pytz
    return datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%Y-%m")


def _cleanup_old_monthly_payments(retention_months: int = 4):
    from datetime import datetime
    now = datetime.now()
    year = now.year
    month = now.month - retention_months
    while month <= 0:
        month += 12
        year -= 1
    ym_cutoff = f"{year:04d}-{month:02d}"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM monthly_payments WHERE ym < ?', (ym_cutoff,))
    conn.commit()
    conn.close()


def set_month_paid(user_id: int, ym: str | None = None, group_id: int | None = None, subject: str | None = None, paid: bool = True):
    """Mark monthly payment status per user-group for a given month."""
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        if paid:
            cur.execute(
                '''
                INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                VALUES(?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, ym, group_id) DO UPDATE SET paid=1, paid_at=CURRENT_TIMESTAMP, subject=COALESCE(excluded.subject, subject)
                ''',
                (user_id, ym, group_id, subject),
            )
        else:
            cur.execute(
                '''
                INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                VALUES(?, ?, ?, ?, 0, NULL)
                ON CONFLICT(user_id, ym, group_id) DO UPDATE SET paid=0, paid_at=NULL, subject=COALESCE(excluded.subject, subject)
                ''',
                (user_id, ym, group_id, subject),
            )
        conn.commit()
        conn.close()
    _cleanup_old_monthly_payments(retention_months=4)


def is_month_paid(user_id: int, ym: str | None = None, group_id: int | None = None) -> bool:
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    conn = get_conn()
    cur = conn.cursor()
    if group_id is None:
        cur.execute("SELECT paid FROM monthly_payments WHERE user_id=? AND ym=?", (user_id, ym))
    else:
        cur.execute("SELECT paid FROM monthly_payments WHERE user_id=? AND ym=? AND group_id=?", (user_id, ym, group_id))
    row = cur.fetchone()
    conn.close()
    return bool(row["paid"]) if row else False


def was_notified_on_day(user_id: int, day: int, ym: str | None = None) -> bool:
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT notified_days FROM monthly_payments WHERE user_id=? AND ym=?", (user_id, ym))
    row = cur.fetchone()
    conn.close()
    if not row or not row["notified_days"]:
        return False
    days = {d.strip() for d in str(row["notified_days"]).split(",") if d.strip()}
    return str(day) in days


def mark_notified_day(user_id: int, day: int, ym: str | None = None):
    ym = ym or _ym_now()
    ensure_monthly_payments_table()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT notified_days FROM monthly_payments WHERE user_id=? AND ym=?", (user_id, ym))
        row = cur.fetchone()
        cur_days = ""
        if row and row["notified_days"]:
            cur_days = str(row["notified_days"])
        days = {d.strip() for d in cur_days.split(",") if d.strip()}
        days.add(str(day))
        new_days = ",".join(sorted(days, key=lambda x: int(x)))
        cur.execute(
            '''
            INSERT INTO monthly_payments(user_id, ym, paid, notified_days)
            VALUES(?, ?, 0, ?)
            ON CONFLICT(user_id, ym) DO UPDATE SET notified_days=?
            ''',
            (user_id, ym, new_days, new_days),
        )
        conn.commit()
        conn.close()


def get_grammar_attempts(user_id: int, topic_id: str) -> int:
    ensure_grammar_attempts_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT attempts FROM grammar_attempts WHERE user_id=? AND topic_id=?", (user_id, topic_id))
    row = cur.fetchone()
    conn.close()
    return int(row["attempts"]) if row and row["attempts"] is not None else 0


def increment_grammar_attempt(user_id: int, topic_id: str) -> int:
    """Increments attempts and returns new value."""
    ensure_grammar_attempts_table()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO grammar_attempts(user_id, topic_id, attempts, last_attempt_at)
            VALUES(?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, topic_id) DO UPDATE SET
              attempts=COALESCE(attempts,0)+1,
              last_attempt_at=CURRENT_TIMESTAMP
            ''',
            (user_id, topic_id),
        )
        conn.commit()
        cur.execute("SELECT attempts FROM grammar_attempts WHERE user_id=? AND topic_id=?", (user_id, topic_id))
        row = cur.fetchone()
        conn.close()
        return int(row["attempts"]) if row and row["attempts"] is not None else 0

def get_group_users(group_id):
    """Guruh a'zolarini olish (user_groups table orqali)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.* 
        FROM user_groups ug
        JOIN users u ON ug.user_id = u.id
        WHERE ug.group_id = ?
        ORDER BY u.first_name, u.last_name
    """, (group_id,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

# ====================== DAVOMAT BOSHQARUVI ======================

def add_attendance(user_id, group_id, date, status='Present'):
    """Davomatni qo'shish"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        # Ilogaritmada mavjud bo'lsa yangilash, yo'q bo'lsa qo'shish
        cur.execute('''
            INSERT OR REPLACE INTO attendance (user_id, group_id, date, status)
            VALUES (?, ?, ?, ?)
        ''', (user_id, group_id, date, status))
        conn.commit()
        conn.close()

def get_attendance(user_id, group_id, date):
    """Konkret davomat yozuvini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM attendance WHERE user_id=? AND group_id=? AND date=?
    ''', (user_id, group_id, date))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_attendance_by_group(group_id, date):
    """Guruhnning muayyan kuni davomatini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM attendance WHERE group_id=? AND date=? ORDER BY user_id
    ''', (group_id, date))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

# ====================== DIAMOND BOSHQARUVI ======================

def add_diamonds(user_id, amount):
    """Talabaga Diamond qo'shish"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        from datetime import datetime
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update user balance
        cur.execute('''
            UPDATE users SET diamonds = COALESCE(diamonds, 0) + ?, last_diamond_update = ?
            WHERE id=?
        ''', (amount, now, user_id))
        
        # Add to history
        cur.execute('''
            INSERT INTO diamond_history (user_id, diamonds_change, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, amount, now))
        
        conn.commit()
        conn.close()

def get_diamonds(user_id):
    """Talabaning Diamond sonini olish"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT diamonds FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row['diamonds'] or 0 if row else 0

def get_leaderboard_global(limit=10, offset=0):
    """Global reyting (butun markaz boyicha)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, first_name, last_name, diamonds FROM users
        WHERE diamonds > 0 AND access_enabled=1
        ORDER BY diamonds DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_leaderboard_by_group(group_id, limit=10, offset=0):
    """GuruH bo'yicha reyting"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT id, first_name, last_name, diamonds FROM users
        WHERE group_id=? AND diamonds > 0
        ORDER BY diamonds DESC
        LIMIT ? OFFSET ?
    ''', (group_id, limit, offset))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_leaderboard_count():
    """Global reytingdagi umumiy foydalanuvchi soni"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM users WHERE diamonds > 0 AND access_enabled=1")
    row = cur.fetchone()
    conn.close()
    return row['count'] if row else 0

def get_teacher_groups_count(teacher_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM groups WHERE teacher_id = ?", (teacher_id,))
    row = cur.fetchone()
    conn.close()
    return row['cnt'] if row else 0


def get_teacher_students_count(teacher_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT u.id) as cnt 
        FROM users u
        JOIN groups g ON u.group_id = g.id
        WHERE g.teacher_id = ? AND u.login_type IN (1,2)
    """, (teacher_id,))
    row = cur.fetchone()
    conn.close()
    return row['cnt'] if row else 0


def get_teacher_total_students(teacher_id: int) -> int:
    """O'qituvchining barcha guruhlaridagi jami talabalar soni (multi-group tizimi uchun)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT ug.user_id) as total_students
        FROM user_groups ug
        JOIN groups g ON ug.group_id = g.id
        WHERE g.teacher_id = ? 
          AND g.active = 1
    """, (teacher_id,))
    row = cur.fetchone()
    conn.close()
    return row['total_students'] if row and row['total_students'] is not None else 0


def get_student_teachers(user_id: int):
    """Studentning barcha guruhlaridagi o'qituvchilarni qaytaradi (ism + guruh nomi bilan)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT 
            t.id as teacher_id,
            t.first_name,
            t.last_name,
            g.name as group_name,
            g.subject
        FROM user_groups ug
        JOIN groups g ON ug.group_id = g.id
        JOIN users t ON g.teacher_id = t.id
        WHERE ug.user_id = ? 
          AND t.login_type = 3
        ORDER BY g.name
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_student_subjects(user_id: int) -> list:
    """Studentning barcha guruhlaridagi UNIQUE fanlarni qaytaradi"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT g.subject 
        FROM user_groups ug
        JOIN groups g ON ug.group_id = g.id
        WHERE ug.user_id = ? 
          AND g.subject IS NOT NULL
        ORDER BY g.subject
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [row['subject'] for row in rows if row['subject']]


def get_user_groups_with_counts(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            g.id, g.name, g.level, 
            (SELECT COUNT(*) FROM users u2 
             WHERE u2.group_id = g.id AND u2.login_type IN (1,2)) as student_count
        FROM groups g
        JOIN users u ON u.group_id = g.id
        WHERE u.id = ?
        ORDER BY g.name
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_leaderboard_count_by_group(group_id):
    """Guruhdagi Diamond bilan foydalanuvchi soni"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM users WHERE group_id=? AND diamonds > 0", (group_id,))
    row = cur.fetchone()
    conn.close()
    return row['count'] if row else 0


def get_user_rating_info(user_id):
    """Foydalanuvchining reyting ma'lumotlarini olish"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Global rank
    cur.execute("""
        SELECT COUNT(*) + 1 as global_rank 
        FROM users 
        WHERE diamonds > (SELECT diamonds FROM users WHERE id = ?)
    """, (user_id,))
    global_rank_row = cur.fetchone()
    global_rank = global_rank_row['global_rank'] if global_rank_row else None
    
    # Group rank
    cur.execute("""
        SELECT COUNT(*) + 1 as group_rank 
        FROM users 
        WHERE group_id = (SELECT group_id FROM users WHERE id = ?) 
        AND diamonds > (SELECT diamonds FROM users WHERE id = ?)
    """, (user_id, user_id))
    group_rank_row = cur.fetchone()
    group_rank = group_rank_row['group_rank'] if group_rank_row else None
    
    conn.close()
    
    return {
        'global_rank': global_rank,
        'group_rank': group_rank
    }


def get_rating_leaderboard(user_id, period):
    """Reyting jadvalini olish (daily, weekly, monthly)"""
    conn = get_conn()
    cur = conn.cursor()
    
    if period == 'daily':
        # Kunlik reyting - bugungi kun olgan D'coinlar
        cur.execute("""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(CASE 
                       WHEN DATE(h.last_diamond_update) = DATE('now') THEN diamonds_change 
                       ELSE 0 END), 0) as score,
                   COALESCE(SUM(CASE 
                       WHEN DATE(h.last_diamond_update) = DATE('now') THEN diamonds_change 
                       ELSE 0 END), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE DATE(dh.created_at) = DATE('now')
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """)
    elif period == 'weekly':
        # Haftalik reyting - oxirgi 7 kun
        cur.execute("""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(diamonds_change), 0) as score,
                   COALESCE(SUM(diamonds_change), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE dh.created_at >= DATE('now', '-7 days')
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """)
    elif period == 'monthly':
        # Oylik reyting - oxirgi 30 kun
        cur.execute("""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(diamonds_change), 0) as score,
                   COALESCE(SUM(diamonds_change), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE dh.created_at >= DATE('now', '-30 days')
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """)
    else:
        return []
    
    rows = cur.fetchall()
    conn.close()
    
    leaderboard = []
    for row in rows:
        name = f"{row[0] or ''} {row[1] or ''}".strip()
        score = row[2] or 0
        dcoin = row[3] or 0
        
        leaderboard.append({
            'name': name,
            'score': score,
            'dcoin': dcoin
        })
    
    return leaderboard


def add_feedback(user_id, feedback_text, is_anonymous=True):
    """Add student feedback to database"""
    conn = get_conn()
    cur = conn.cursor()
    from datetime import datetime
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    cur.execute('''
        INSERT INTO feedback (user_id, feedback_text, is_anonymous, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, feedback_text, is_anonymous, now))
    
    conn.commit()
    conn.close()


def get_student_monthly_stats(user_id):
    """Get student's monthly statistics"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get current month start
    cur.execute("SELECT DATE('now', 'start of month') as month_start")
    month_start = cur.fetchone()['month_start']
    
    # === WORDS LEARNED — tuzatilgan versiya ===
    cur.execute('''
        SELECT COUNT(*) as words_learned
        FROM diamond_history 
        WHERE user_id = ? 
          AND diamonds_change > 0 
          AND created_at >= ?
    ''', (user_id, month_start))
    
    words_result = cur.fetchone()
    words_learned = words_result['words_learned'] if words_result else 0
    
    # Count grammar topics completed
    cur.execute('''
        SELECT COUNT(DISTINCT topic_id) as topics_completed
        FROM grammar_attempts ga
        WHERE ga.user_id = ?
        AND ga.created_at >= ?
    ''', (user_id, month_start))
    
    topics_result = cur.fetchone()
    topics_completed = topics_result['topics_completed'] if topics_result else 0
    
    # Count tests taken
    cur.execute('''
        SELECT COUNT(*) as tests_taken,
               SUM(CASE WHEN correct_count > 0 THEN 1 ELSE 0 END) as tests_completed,
               SUM(correct_count) as total_correct,
               SUM(wrong_count) as total_wrong,
               SUM(skipped_count) as total_skipped
        FROM test_history th
        WHERE th.user_id = ?
        AND th.created_at >= ?
    ''', (user_id, month_start))
    
    tests_result = cur.fetchone()
    if tests_result:
        tests_taken = tests_result['tests_taken'] or 0
        tests_completed = tests_result['tests_completed'] or 0
        total_correct = tests_result['total_correct'] or 0
        total_wrong = tests_result['total_wrong'] or 0
        total_skipped = tests_result['total_skipped'] or 0
    else:
        tests_taken = 0
        tests_completed = 0
        total_correct = 0
        total_wrong = 0
        total_skipped = 0
    
    conn.close()
    
    return {
        'words_learned': words_learned,
        'topics_completed': topics_completed,
        'tests_taken': tests_taken,
        'tests_completed': tests_completed,
        'total_correct': total_correct,
        'total_wrong': total_wrong,
        'total_skipped': total_skipped
    }


def add_test_history(user_id, test_type, topic_id, correct_count, wrong_count, skipped_count):
    """Add test record to history"""
    conn = get_conn()
    cur = conn.cursor()
    from datetime import datetime
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    cur.execute('''
        INSERT INTO test_history (user_id, test_type, topic_id, correct_count, wrong_count, skipped_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, test_type, topic_id, correct_count, wrong_count, skipped_count, now))
    
    conn.commit()
    conn.close()
