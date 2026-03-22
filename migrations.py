"""
Diamond Bot Migrations (huddi siz yuborgan koddek)
Har safar bot ishga tushganda pending migratsiyalarni bajaradi.
"""

import sqlite3
import logging
from typing import Callable, List, Tuple

from config import DB_PATH

logger = logging.getLogger(__name__)

# Global migration ro‘yxati
MIGRATIONS: List[Tuple[str, Callable]] = []


def register_migration(name: str, migrate_func: Callable):
    MIGRATIONS.append((name, migrate_func))


def get_applied_migrations() -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'")
        if not cur.fetchone():
            cur.execute('''
                CREATE TABLE IF NOT EXISTS _migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            return []
        
        cur.execute('SELECT name FROM _migrations ORDER BY applied_at')
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def mark_migration_applied(name: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO _migrations(name) VALUES (?)', (name,))
        conn.commit()
        logger.info(f'✅ Migration "{name}" applied')
    finally:
        conn.close()


def run_all_migrations():
    """Har safar bot ishga tushganda chaqiriladi"""
    applied = get_applied_migrations()
    pending = [(name, func) for name, func in MIGRATIONS if name not in applied]
    
    if not pending:
        logger.info('✅ Barcha migratsiyalar allaqachon qo‘llanilgan')
        return
    
    logger.info(f'🔄 {len(pending)} ta yangi migratsiya bajarilmoqda...')
    
    for name, func in pending:
        try:
            logger.info(f'📝 {name} migratsiyasi bajarilmoqda...')
            func()
            mark_migration_applied(name)
            logger.info(f'✅ {name} muvaffaqiyatli bajarildi')
        except Exception as e:
            logger.error(f'❌ {name} xato: {e}', exc_info=True)
            raise


# ====================== SIZNING Diamond bot uchun migratsiyalar ======================

def migration_001_add_failed_logins_and_blocked():
    """users jadvaliga failed_logins va blocked columnlarini qo‘shadi"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'failed_logins' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN failed_logins INTEGER DEFAULT 0')
        if 'blocked' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN blocked BOOLEAN DEFAULT FALSE')
        
        conn.commit()
        logger.info('✅ failed_logins va blocked columnlari qo‘shildi')
    finally:
        conn.close()


def migration_002_add_full_name_and_reminder_pref():
    """Agar kerak bo‘lsa qo‘shimcha columnlar"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'full_name' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
        if 'reminder_pref' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN reminder_pref TEXT DEFAULT "1h"')
        
        conn.commit()
    finally:
        conn.close()


def migration_003_add_access_expires_and_placement_fields():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        if 'access_expires_at' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN access_expires_at TEXT')
        if 'test_in_progress' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN test_in_progress INTEGER DEFAULT 0')
        if 'test_subject' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN test_subject TEXT')
        if 'test_question_index' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN test_question_index INTEGER DEFAULT 0')
        if 'test_score' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN test_score INTEGER DEFAULT 0')
        if 'test_questions' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN test_questions TEXT')
        conn.commit()
    finally:
        conn.close()


def migration_004_add_user_groups_table():
    """Create user_groups table for many-to-many relationship between users and groups"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        
        # Create user_groups table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
                UNIQUE(user_id, group_id)
            )
        ''')
        
        # Ensure joined_at column exists if table was created earlier without it
        cur.execute("PRAGMA table_info(user_groups)")
        existing_cols = [r[1] for r in cur.fetchall()]
        if 'joined_at' not in existing_cols:
            try:
                cur.execute("ALTER TABLE user_groups ADD COLUMN joined_at TEXT DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                # If adding fails, continue; we'll insert without joined_at
                pass

        # Migrate existing group_id relationships to user_groups
        # If joined_at exists, include it in INSERT, otherwise insert only user_id and group_id
        cur.execute("PRAGMA table_info(user_groups)")
        existing_cols = [r[1] for r in cur.fetchall()]
        try:
            if 'joined_at' in existing_cols:
                cur.execute('''
                    INSERT OR IGNORE INTO user_groups (user_id, group_id, joined_at)
                    SELECT id, group_id, COALESCE(created_at, CURRENT_TIMESTAMP)
                    FROM users 
                    WHERE group_id IS NOT NULL
                ''')
            else:
                cur.execute('''
                    INSERT OR IGNORE INTO user_groups (user_id, group_id)
                    SELECT id, group_id
                    FROM users 
                    WHERE group_id IS NOT NULL
                ''')
        except Exception:
            # If migration insert fails for any reason, log and continue
            logger.exception('user_groups backfill failed')
        
        conn.commit()
        logger.info('✅ Created user_groups table and migrated existing relationships')
    finally:
        conn.close()


def migration_005_add_session_management():
    """Add session management fields to users table"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'telegram_id' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN telegram_id TEXT UNIQUE')
        if 'is_logged_in' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN is_logged_in INTEGER DEFAULT 0')
        if 'last_activity' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN last_activity TEXT')
        if 'session_started' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN session_started TEXT')
        
        conn.commit()
        logger.info('✅ Added session management fields')
    finally:
        conn.close()


def migration_006_add_active_column_to_groups():
    """Add active column to groups table"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(groups)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'active' not in cols:
            cur.execute('ALTER TABLE groups ADD COLUMN active BOOLEAN DEFAULT 1')
        
        conn.commit()
        logger.info('✅ active column added to groups table')
    finally:
        conn.close()


def migration_007_enable_teacher_access():
    """Enable access for all teachers (login_type=3)"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET access_enabled=1 WHERE login_type=3 AND access_enabled=0")
        updated_count = cur.rowcount
        conn.commit()
        logger.info(f'✅ Enabled access for {updated_count} teachers')
    finally:
        conn.close()


# Migratsiyalarni ro'yxatga qo'shish (tartib muhim!)
register_migration('001_add_failed_logins_and_blocked', migration_001_add_failed_logins_and_blocked)
register_migration('002_add_full_name_and_reminder_pref', migration_002_add_full_name_and_reminder_pref)
register_migration('003_add_access_expires_and_placement_fields', migration_003_add_access_expires_and_placement_fields)
register_migration('004_add_user_groups_table', migration_004_add_user_groups_table)
register_migration('005_add_session_management', migration_005_add_session_management)
register_migration('006_add_active_column_to_groups', migration_006_add_active_column_to_groups)
register_migration('007_enable_teacher_access', migration_007_enable_teacher_access)


def migration_008_add_lesson_days_column():
    """Eski kod uchun lesson_days ustuni (agar kerak bo'lsa)"""
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(groups)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'lesson_days' not in cols:
            cur.execute('ALTER TABLE groups ADD COLUMN lesson_days TEXT')
            logger.info('✅ lesson_days column qo‘shildi')
        
        conn.commit()
    finally:
        conn.close()


register_migration('008_add_lesson_days_column', migration_008_add_lesson_days_column)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_all_migrations()
    print('✅ Barcha migratsiyalar tugadi!')
