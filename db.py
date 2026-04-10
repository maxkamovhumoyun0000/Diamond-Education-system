import threading
import logging
import random
import string
import os
import sqlite3
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import ADMIN_CHAT_IDS, ALL_ADMIN_IDS, DB_PATH, DATABASE_URL
from logging_config import get_logger
import psycopg
from psycopg.rows import dict_row
import time

logger = get_logger(__name__)
Path('data').mkdir(parents=True, exist_ok=True)
DB_WRITE_LOCK = threading.Lock()
_PG_CONNECT_MAX_ATTEMPTS = int(os.getenv("PG_CONNECT_MAX_ATTEMPTS", "4"))
_PG_CONNECT_BACKOFF_SEC = float(os.getenv("PG_CONNECT_BACKOFF_SEC", "0.5"))




def _to_postgres_sql(sql: str) -> str:
    """
    Minimal SQL compatibility for existing sqlite-style queries.
    - legacy placeholders `?` -> postgres `%s`
    """
    q = (sql or "").replace("?", "%s")
    return q


class _PgCursorCompat:
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=None):
        q = _to_postgres_sql(sql)
        if params is None:
            return self._cur.execute(q)
        return self._cur.execute(q, params)

    def executemany(self, sql, seq_of_params):
        q = _to_postgres_sql(sql)
        return self._cur.executemany(q, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _PgConnCompat:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _PgCursorCompat(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._conn.__exit__(exc_type, exc_val, exc_tb)

def _is_postgres_enabled() -> bool:
    return bool(DATABASE_URL and str(DATABASE_URL).strip())


def get_conn():
    if _is_postgres_enabled():
        last_error = None
        for attempt in range(1, max(1, _PG_CONNECT_MAX_ATTEMPTS) + 1):
            try:
                conn = psycopg.connect(
                    DATABASE_URL,
                    row_factory=dict_row,
                    connect_timeout=8,
                    keepalives=1,
                    keepalives_idle=20,
                    keepalives_interval=5,
                    keepalives_count=3,
                )
                return _PgConnCompat(conn)
            except Exception as e:
                last_error = e
                if attempt >= max(1, _PG_CONNECT_MAX_ATTEMPTS):
                    break
                sleep_s = _PG_CONNECT_BACKOFF_SEC * (2 ** (attempt - 1))
                logger.warning(
                    "Postgres connect failed attempt=%s/%s; retrying in %.2fs: %s",
                    attempt,
                    _PG_CONNECT_MAX_ATTEMPTS,
                    sleep_s,
                    e,
                )
                time.sleep(sleep_s)
        raise last_error

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_postgres_db():
    logger.info("Initializing PostgreSQL database...")
    conn = None
    try:
        conn = get_conn()
        logger.info("PostgreSQL connection established successfully")
        cur = conn.cursor()
        
        # Test the connection
        cur.execute("SELECT version()")
        version = cur.fetchone()
        logger.info(f"PostgreSQL version: {version}")
        
        # Check if bot_runtime_state table exists and its schema
        try:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'bot_runtime_state'
                ORDER BY ordinal_position
            """)
            existing_schema = cur.fetchall()
            if existing_schema:
                logger.info(f"Existing bot_runtime_state schema: {existing_schema}")
            else:
                logger.info("bot_runtime_state table does not exist yet")
        except Exception as schema_e:
            logger.warning(f"Could not check existing schema: {schema_e}")
        
        # Create all tables
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                telegram_id TEXT UNIQUE,
                login_id TEXT UNIQUE,
                password TEXT,
                password_used INTEGER DEFAULT 0,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                subject TEXT,
                login_type INTEGER DEFAULT 1,
                level TEXT,
                access_enabled INTEGER DEFAULT 0,
                access_expires_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failed_logins INTEGER DEFAULT 0,
                blocked INTEGER DEFAULT 0,
                test_in_progress INTEGER DEFAULT 0,
                test_subject TEXT,
                test_question_index INTEGER DEFAULT 0,
                test_score INTEGER DEFAULT 0,
                test_questions TEXT,
                pending_approval INTEGER DEFAULT 0,
                owner_admin_id BIGINT,
                group_id BIGINT,
                language TEXT DEFAULT 'uz',
                logged_in INTEGER DEFAULT 0,
                last_login_at TIMESTAMP,
                last_activity TEXT,
                session_started TEXT,
                logout_time TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                id BIGSERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                teacher_id BIGINT,
                level TEXT,
                subject TEXT,
                lesson_date TEXT,
                lesson_days TEXT,
                lesson_start TEXT,
                lesson_end TEXT,
                tz TEXT DEFAULT 'Asia/Tashkent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_admin_id BIGINT,
                active INTEGER DEFAULT 1
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                subject TEXT,
                score INTEGER,
                max_score INTEGER DEFAULT 100,
                level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL,
                date TEXT NOT NULL,
                status TEXT DEFAULT 'Absent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, group_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_payments (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                ym TEXT NOT NULL,
                group_id BIGINT,
                subject TEXT,
                paid INTEGER DEFAULT 0,
                paid_at TEXT,
                notified_days TEXT,
                UNIQUE(user_id, ym, group_id)
            )
        """)
        
        cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym_group ON monthly_payments(user_id, ym, group_id)')
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id BIGSERIAL PRIMARY KEY,
                group_id BIGINT NOT NULL,
                date TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                closed_by TEXT,
                notified_admin INTEGER DEFAULT 0,
                notified_teacher INTEGER DEFAULT 0,
                notified_admin_pre INTEGER DEFAULT 0,
                notified_admin_post INTEGER DEFAULT 0,
                notified_teacher_pre INTEGER DEFAULT 0,
                notified_teacher_post INTEGER DEFAULT 0,
                admin_panel_chat_id BIGINT,
                admin_panel_message_id BIGINT,
                teacher_panel_chat_id BIGINT,
                teacher_panel_message_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, date)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id BIGSERIAL PRIMARY KEY,
                word TEXT NOT NULL,
                subject TEXT NOT NULL,
                language TEXT NOT NULL,
                level TEXT,
                translation_uz TEXT,
                translation_ru TEXT,
                definition TEXT,
                example TEXT,
                added_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_imports (
                id BIGSERIAL PRIMARY KEY,
                file_name TEXT NOT NULL,
                added_by BIGINT,
                subject TEXT NOT NULL,
                language TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_preferences (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                preferred_translation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diamond_history (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                dcoin_change DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subject TEXT,
                change_type TEXT
            )
        """)

        # Critical D'coin source-of-truth table (must exist before bot startup).
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_subject_dcoins (
                user_id BIGINT NOT NULL,
                subject TEXT NOT NULL,
                balance DOUBLE PRECISION NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject)
            )
            """
        )
        # Compatibility: some old/manual schemas used `dcoin` column name.
        if _is_postgres_enabled():
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='user_subject_dcoins' AND column_name='dcoin'
                LIMIT 1
                """
            )
            if cur.fetchone():
                cur.execute("ALTER TABLE user_subject_dcoins RENAME COLUMN dcoin TO balance")
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_subject_dcoins_user_id
            ON user_subject_dcoins(user_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_subject_dcoins_subject
            ON user_subject_dcoins(subject)
            """
        )
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                feedback_text TEXT NOT NULL,
                is_anonymous INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_history (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                test_type TEXT NOT NULL,
                topic_id TEXT,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grammar_attempts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                topic_id TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                last_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, topic_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS overdue_penalty_log (
                user_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL,
                ym TEXT NOT NULL,
                penalty_date TEXT NOT NULL,
                PRIMARY KEY (user_id, group_id, ym, penalty_date)
            )
        """)

        # Shared daily question set per calendar day (bootstrap; see also ensure_daily_tests_schema).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_test_day_question_sets (
                id BIGSERIAL PRIMARY KEY,
                test_date DATE NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                bank_ids_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(test_date, subject, level)
            )
        """)
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_test_day_sets_lookup
                ON daily_test_day_question_sets (test_date, subject, level)
                """
            )
        except Exception:
            pass
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_test_day_sets_date
                ON daily_test_day_question_sets (test_date)
                """
            )
        except Exception:
            pass

        # Handle bot_runtime_state table with proper schema migration
        try:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'bot_runtime_state'
            """)
            runtime_cols = {r["column_name"] for r in cur.fetchall()}
            # Legacy schema detected (key/value/updated_at etc.) -> recreate clean table.
            if runtime_cols and "started_at" not in runtime_cols:
                logger.warning(
                    f"Legacy bot_runtime_state schema detected ({sorted(runtime_cols)}); recreating table"
                )
                cur.execute("DROP TABLE IF EXISTS bot_runtime_state")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_runtime_state (
                    id BIGSERIAL PRIMARY KEY,
                    started_at TIMESTAMP NOT NULL
                )
            """)
        except Exception as e:
            # Table might exist with different schema, try to drop and recreate
            logger.warning(f"bot_runtime_state table issue: {e}, attempting to recreate...")
            try:
                cur.execute("DROP TABLE IF EXISTS bot_runtime_state")
                cur.execute("""
                    CREATE TABLE bot_runtime_state (
                        id BIGSERIAL PRIMARY KEY,
                        started_at TIMESTAMP NOT NULL
                    )
                """)
            except Exception as drop_e:
                logger.error(f"Failed to recreate bot_runtime_state: {drop_e}")
                raise drop_e
        
        # Ensure row exists - let BIGSERIAL handle the ID automatically
        try:
            cur.execute('''
                INSERT INTO bot_runtime_state (started_at)
                VALUES (CURRENT_TIMESTAMP)
                ON CONFLICT DO NOTHING
            ''')
        except Exception as insert_e:
            # If INSERT fails due to schema issues, try a simpler approach
            logger.warning(f"INSERT failed: {insert_e}, trying alternative...")
            # psycopg keeps transaction aborted after failed query; rollback first.
            conn.rollback()
            try:
                cur.execute('''
                    INSERT INTO bot_runtime_state (id, started_at)
                    VALUES (1, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET started_at = CURRENT_TIMESTAMP
                ''')
            except Exception as final_e:
                logger.error(f"Failed to initialize bot_runtime_state: {final_e}")
                # If all else fails, just continue without this table
                logger.warning("Continuing without bot_runtime_state table")
        
        logger.info("PostgreSQL database initialization completed successfully")
        conn.commit()
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL database: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def _bootstrap_postgres_after_base_tables() -> None:
    """ensure_* migrations after _init_postgres_db (startup and after full schema wipe)."""
    print("[STARTUP][DB] ensure_overdue_penalty_log_table()")
    ensure_overdue_penalty_log_table()
    print("[STARTUP][DB] ensure_overdue_penalty_log_table() done")

    print("[STARTUP][DB] ensure_attendance_sessions_schema()")
    ensure_attendance_sessions_schema()
    print("[STARTUP][DB] ensure_attendance_sessions_schema() done")

    print("[STARTUP][DB] ensure_temporary_group_assignments_schema()")
    ensure_temporary_group_assignments_schema()
    print("[STARTUP][DB] ensure_temporary_group_assignments_schema() done")

    print("[STARTUP][DB] ensure_admin_student_shares_schema()")
    ensure_admin_student_shares_schema()
    print("[STARTUP][DB] ensure_admin_student_shares_schema() done")

    print("[STARTUP][DB] ensure_daily_tests_schema()")
    ensure_daily_tests_schema()
    print("[STARTUP][DB] ensure_daily_tests_schema() done")

    print("[STARTUP][DB] ensure_arena_questions_schema()")
    ensure_arena_questions_schema()
    print("[STARTUP][DB] ensure_arena_questions_schema() done")

    print("[STARTUP][DB] ensure_arena_group_schema()")
    ensure_arena_group_schema()
    print("[STARTUP][DB] ensure_arena_group_schema() done")

    print("[STARTUP][DB] ensure_arena_group_extended_schema()")
    ensure_arena_group_extended_schema()
    print("[STARTUP][DB] ensure_arena_group_extended_schema() done")

    print("[STARTUP][DB] ensure_arena_other_sessions_schema()")
    ensure_arena_other_sessions_schema()
    print("[STARTUP][DB] ensure_arena_other_sessions_schema() done")

    print("[STARTUP][DB] ensure_student_ai_chat_schema()")
    ensure_student_ai_chat_schema()
    print("[STARTUP][DB] ensure_student_ai_chat_schema() done")

    print("[STARTUP][DB] ensure_subject_dcoin_schema()")
    ensure_subject_dcoin_schema()
    print("[STARTUP][DB] ensure_subject_dcoin_schema() done")

    print("[STARTUP][DB] ensure_dcoin_schema_migrations()")
    ensure_dcoin_schema_migrations()
    print("[STARTUP][DB] ensure_dcoin_schema_migrations() done")

    print("[STARTUP][DB] ensure_duel_matchmaking_schema()")
    ensure_duel_matchmaking_schema()
    print("[STARTUP][DB] ensure_duel_matchmaking_schema() done")

    print("[STARTUP][DB] ensure_arena_extras_schema()")
    ensure_arena_extras_schema()
    print("[STARTUP][DB] ensure_arena_extras_schema() done")

    print("[STARTUP][DB] ensure_support_lessons_schema()")
    ensure_support_lessons_schema()
    print("[STARTUP][DB] ensure_support_lessons_schema() done")

    print("[STARTUP][DB] ensure_lesson_otmen_requests_schema()")
    ensure_lesson_otmen_requests_schema()
    print("[STARTUP][DB] ensure_lesson_otmen_requests_schema() done")

    print("[STARTUP][DB] ensure_diamondvoy_history_table()")
    ensure_diamondvoy_history_table()
    print("[STARTUP][DB] ensure_diamondvoy_history_table() done")


def wipe_postgresql_database_and_reinit() -> None:
    """
    DROP public schema and recreate all application tables. Irreversible.
    Caller must enforce admin + secret checks. Uses DB_WRITE_LOCK.
    """
    if not _is_postgres_enabled():
        raise RuntimeError("PostgreSQL only: DATABASE_URL required for wipe")
    with DB_WRITE_LOCK:
        raw = psycopg.connect(DATABASE_URL, autocommit=True)
        try:
            with raw.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
                cur.execute("CREATE SCHEMA public")
                cur.execute("GRANT ALL ON SCHEMA public TO PUBLIC")
        finally:
            raw.close()
        logger.critical("PostgreSQL public schema dropped; reinitializing all tables")
        print("[WIPE][DB] _init_postgres_db() starting")
        _init_postgres_db()
        print("[WIPE][DB] _init_postgres_db() done")
        _bootstrap_postgres_after_base_tables()
        logger.info("PostgreSQL wipe + reinit completed")


def init_db():
    """Birinchi marta ishga tushganda tablelarni yaratadi."""
    if _is_postgres_enabled():
        print("[STARTUP][DB] _init_postgres_db() starting")
        _init_postgres_db()
        print("[STARTUP][DB] _init_postgres_db() done")
        logger.info("✅ PostgreSQL tables initialized")
        _bootstrap_postgres_after_base_tables()
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE,
        login_id TEXT UNIQUE,
        password TEXT,
        password_used INTEGER DEFAULT 0,
        first_name TEXT,
        last_name TEXT,
        phone TEXT,
        subject TEXT,
        login_type INTEGER DEFAULT 1,
        level TEXT,
        access_enabled INTEGER DEFAULT 0,
        access_expires_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        failed_logins INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        test_in_progress INTEGER DEFAULT 0,
        test_subject TEXT,
        test_question_index INTEGER DEFAULT 0,
        test_score INTEGER DEFAULT 0,
        test_questions TEXT,
        pending_approval INTEGER DEFAULT 0,
        owner_admin_id INTEGER,
        group_id INTEGER,
        language TEXT DEFAULT 'uz',
        logged_in INTEGER DEFAULT 0,
        last_login_at TEXT,
        last_activity TEXT,
        session_started TEXT,
        logout_time TEXT,
        active INTEGER DEFAULT 1
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS test_results (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT,
        subject TEXT,
        score INTEGER,
        max_score INTEGER DEFAULT 100,
        level TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # Guruhlar jadvali
    cur.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        teacher_id BIGINT,
        level TEXT,
        lesson_date TIMESTAMP,
        lesson_start TIMESTAMP,
        lesson_end TIMESTAMP,
        tz TEXT DEFAULT 'Asia/Tashkent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(teacher_id) REFERENCES users(id)
    )
    ''')

    # Davomat jadvali
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        group_id BIGINT NOT NULL,
        date TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'Absent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # User-group join table for multi-group students
    cur.execute('''
    CREATE TABLE IF NOT EXISTS user_groups (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        group_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, group_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # Monthly payments with optional group scope
    cur.execute('''
    CREATE TABLE IF NOT EXISTS monthly_payments (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        ym TEXT NOT NULL,
        group_id BIGINT,
        subject TEXT,
        paid INTEGER DEFAULT 0,
        paid_at TIMESTAMP,
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
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Vocabulary tables
    cur.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id BIGSERIAL PRIMARY KEY,
        word TEXT NOT NULL,
        subject TEXT NOT NULL,
        language TEXT NOT NULL,
        level TEXT,
        translation_uz TEXT,
        translation_ru TEXT,
        definition TEXT,
        example TEXT,
        added_by BIGINT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(added_by) REFERENCES users(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS vocabulary_imports (
        id BIGSERIAL PRIMARY KEY,
        file_name TEXT NOT NULL,
        added_by BIGINT,
        subject TEXT NOT NULL,
        language TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(added_by) REFERENCES users(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_preferences (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        preferred_translation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()
    logger.info(f"✅ diamond.db yaratildi: {DB_PATH}")
    dedupe_tests()
    apply_migrations()
    ensure_monthly_payments_table()
    ensure_overdue_penalty_log_table()
    ensure_grammar_attempts_table()
    ensure_temporary_group_assignments_schema()
    ensure_admin_student_shares_schema()
    ensure_daily_tests_schema()
    ensure_student_ai_chat_schema()
    ensure_subject_dcoin_schema()
    ensure_dcoin_schema_migrations()
    ensure_duel_matchmaking_schema()
    ensure_arena_extras_schema()
    ensure_support_lessons_schema()
    ensure_lesson_otmen_requests_schema()
    ensure_diamondvoy_history_table()


def set_pending_approval(user_id, pending=True):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET pending_approval=? WHERE id=?", (1 if pending else 0, user_id))
    conn.commit()
    conn.close()


def set_user_login_type(user_id: int, login_type: int) -> None:
    """
    Update user's login type.
    Used to convert temporary "new student" (placement-test) accounts into regular students.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET login_type=? WHERE id=?", (int(login_type), user_id))
    conn.commit()
    conn.close()


# =========================
# Support lessons (bookings)
# =========================

def is_lesson_holiday(date_iso: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM lesson_holidays WHERE date=? LIMIT 1", (date_iso,))
        return bool(cur.fetchone())
    except Exception:
        return False
    finally:
        conn.close()


def lesson_is_slot_free(start_ts: str) -> bool:
    """
    Slot is free if there is no booking in pending/approved state with same start_ts.
    """
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM lesson_bookings
            WHERE start_ts=? AND status IN ('pending','approved')
            LIMIT 1
            """,
            (start_ts,),
        )
        return not bool(cur.fetchone())
    except Exception:
        return True
    finally:
        conn.close()


def generate_lesson_booking_id() -> str:
    """Unique alphanumeric booking id (uppercase letters + digits)."""
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    ensure_support_lessons_schema()
    for _ in range(40):
        bid = "".join(secrets.choice(alphabet) for _ in range(9))
        if get_lesson_booking(bid) is None:
            return bid
    return bid + secrets.token_hex(2).upper()


def create_lesson_booking_request(
    booking_id: str,
    student_user_id: int,
    student_telegram_id: str | None,
    branch: str,
    date_iso: str,
    time_hhmm: str,
    start_ts: str | None,
    end_ts: str | None,
    purpose: str,
) -> bool:
    ensure_support_lessons_schema()
    # DB-level guard: prevent duplicate active bookings and enforce 6h cooldown
    # even if callbacks are pressed back-to-back.
    from datetime import datetime, timezone

    if not start_ts:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    if student_has_active_upcoming_booking(int(student_user_id), now_iso):
        return False

    unlock_iso = get_next_lesson_booking_allowed_after_utc_iso(int(student_user_id), now_iso)
    if unlock_iso:
        return False

    # Slot/date-level guard (best-effort; UI already checks too).
    if is_lesson_holiday(str(date_iso)) or is_branch_date_closed_for_booking(str(branch), str(date_iso)):
        return False
    if not lesson_is_slot_free(start_ts):
        return False

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_bookings(id, student_user_id, student_telegram_id, branch, date, time, start_ts, end_ts, purpose, status)
            VALUES (?,?,?,?,?,?,?,?,?, 'approved')
            """,
            (booking_id, int(student_user_id), student_telegram_id, branch, date_iso, time_hhmm, start_ts, end_ts, purpose),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception(
            "create_lesson_booking_request failed booking_id=%s student_user_id=%s branch=%s date=%s time=%s",
            booking_id,
            student_user_id,
            branch,
            date_iso,
            time_hhmm,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_lesson_bookings_for_student(student_user_id: int, active_only: bool = True) -> list[dict]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if active_only:
            from datetime import datetime, timezone

            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(
                """
                SELECT * FROM lesson_bookings
                WHERE student_user_id=? AND status IN ('pending','approved')
                  AND (end_ts IS NULL OR end_ts > ?)
                ORDER BY date ASC, time ASC
                """,
                (int(student_user_id), now_iso),
            )
        else:
            cur.execute(
                """
                SELECT * FROM lesson_bookings
                WHERE student_user_id=?
                ORDER BY created_at DESC
                """,
                (int(student_user_id),),
            )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_pending_lesson_bookings(page: int = 1, per_page: int = 10) -> tuple[list[dict], int]:
    ensure_support_lessons_schema()
    page = max(1, int(page or 1))
    per_page = max(1, min(50, int(per_page or 10)))
    offset = (page - 1) * per_page
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM lesson_bookings WHERE status='pending'")
        total = int((cur.fetchone() or {}).get("cnt") or 0)
        total_pages = max(1, (total + per_page - 1) // per_page)
        cur.execute(
            """
            SELECT * FROM lesson_bookings
            WHERE status='pending'
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows], total_pages
    except Exception:
        return [], 1
    finally:
        conn.close()


def set_lesson_booking_status(booking_id: str, status: str, admin_id: int | None = None, admin_note: str | None = None) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE lesson_bookings
            SET status=?, handled_by_admin_id=?, admin_note=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, admin_id, admin_note, booking_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
        if ok and str(status).lower() in ("canceled", "cancelled", "rejected"):
            delete_lesson_reminders_unsent_for_booking(str(booking_id))
        return ok
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def reschedule_lesson_booking(booking_id: str, date_iso: str, time_hhmm: str, start_ts: str | None, admin_id: int | None = None) -> bool:
    from support_booking_time import normalize_time_hhmm, support_make_end_ts, support_make_start_ts

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    st = start_ts or support_make_start_ts(date_iso, tm)
    if not st:
        return False
    et = support_make_end_ts(st)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE lesson_bookings
            SET date=?, time=?, start_ts=?, end_ts=?, status='approved', handled_by_admin_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (date_iso, tm, st, et, admin_id, booking_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
        if ok:
            refresh_lesson_reminders_for_booking(str(booking_id))
        return ok
    except Exception:
        logger.exception(
            "reschedule_lesson_booking failed booking_id=%s date=%s time=%s admin_id=%s",
            booking_id,
            date_iso,
            tm,
            admin_id,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def get_lesson_booking(booking_id: str) -> dict | None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM lesson_bookings WHERE id=? LIMIT 1", (str(booking_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def list_lesson_bookings(status: str | None = None, page: int = 1, per_page: int = 10) -> tuple[list[dict], int]:
    ensure_support_lessons_schema()
    page = max(1, int(page or 1))
    per_page = max(1, min(50, int(per_page or 10)))
    offset = (page - 1) * per_page
    conn = get_conn()
    cur = conn.cursor()
    try:
        if status:
            cur.execute("SELECT COUNT(*) as cnt FROM lesson_bookings WHERE status=?", (status,))
            total = int((cur.fetchone() or {}).get("cnt") or 0)
            total_pages = max(1, (total + per_page - 1) // per_page)
            cur.execute(
                """
                SELECT * FROM lesson_bookings
                WHERE status=?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, per_page, offset),
            )
        else:
            cur.execute("SELECT COUNT(*) as cnt FROM lesson_bookings")
            total = int((cur.fetchone() or {}).get("cnt") or 0)
            total_pages = max(1, (total + per_page - 1) // per_page)
            cur.execute(
                """
                SELECT * FROM lesson_bookings
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (per_page, offset),
            )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows], total_pages
    except Exception:
        return [], 1
    finally:
        conn.close()


def list_lesson_holidays() -> list[str]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT date FROM lesson_holidays ORDER BY date ASC")
        rows = cur.fetchall() or []
        return [str(r["date"]) if isinstance(r, dict) else str(r[0]) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def add_lesson_holiday(date_iso: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO lesson_holidays(date) VALUES (?)", (date_iso,))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def remove_lesson_holiday(date_iso: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM lesson_holidays WHERE date=?", (date_iso,))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def get_pending_lesson_otmen_request_by_date(date_str: str) -> dict | None:
    ensure_lesson_otmen_requests_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM lesson_otmen_requests
            WHERE date_str=? AND status='pending'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (date_str,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def create_lesson_otmen_request(request_id: str, date_str: str, reason: str | None, expires_at_iso: str) -> bool:
    ensure_lesson_otmen_requests_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_otmen_requests(id, date_str, reason, status, expires_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (str(request_id), str(date_str), reason, expires_at_iso),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def get_lesson_otmen_request(request_id: str) -> dict | None:
    ensure_lesson_otmen_requests_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM lesson_otmen_requests WHERE id=? LIMIT 1", (str(request_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def list_cancelled_lesson_otmen_requests(limit: int = 20) -> list[dict]:
    ensure_lesson_otmen_requests_schema()
    tz = pytz.timezone("Asia/Tashkent")
    today_iso = datetime.now(tz).date().isoformat()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM lesson_otmen_requests
            WHERE status='cancelled'
              AND date_str >= ?
            ORDER BY date_str DESC, cancelled_at DESC
            LIMIT ?
            """,
            (today_iso, int(limit)),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def mark_lesson_otmen_request_status(
    request_id: str,
    status: str,
    admin_id: int | None = None,
) -> bool:
    ensure_lesson_otmen_requests_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE lesson_otmen_requests
            SET status=?,
                cancelled_by_admin_id=?,
                cancelled_at=CASE WHEN ?='cancelled' THEN CURRENT_TIMESTAMP ELSE cancelled_at END
            WHERE id=?
            """,
            (status, admin_id, status, str(request_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_lesson_bookings_by_date(date_str: str, statuses: tuple[str, ...] = ("pending", "approved")) -> list[dict]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        placeholders = ",".join(["?"] * len(statuses))
        cur.execute(
            f"""
            SELECT *
            FROM lesson_bookings
            WHERE date=? AND status IN ({placeholders})
            ORDER BY time ASC, created_at ASC
            """,
            (date_str, *statuses),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def list_lesson_extra_slots_for_date(date_iso: str, branch: str | None = None) -> list[str]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if branch:
            cur.execute(
                """
                SELECT time FROM lesson_extra_slots
                WHERE date=? AND (branch IS NULL OR branch=?)
                ORDER BY time ASC
                """,
                (date_iso, branch),
            )
        else:
            cur.execute("SELECT time FROM lesson_extra_slots WHERE date=? ORDER BY time ASC", (date_iso,))
        rows = cur.fetchall() or []
        out: list[str] = []
        for r in rows:
            if isinstance(r, dict):
                out.append(str(r.get("time")))
            else:
                out.append(str(r[0]))
        return out
    except Exception:
        return []
    finally:
        conn.close()


def add_lesson_extra_slot(slot_id: str, date_iso: str, time_hhmm: str, branch: str | None = None) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO lesson_extra_slots(id, date, time, branch) VALUES (?,?,?,?)",
            (slot_id, date_iso, tm, branch),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception("add_lesson_extra_slot failed slot_id=%s date=%s time=%s branch=%s", slot_id, date_iso, tm, branch)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def remove_lesson_extra_slot(date_iso: str, time_hhmm: str, branch: str | None = None) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        if branch:
            cur.execute(
                "DELETE FROM lesson_extra_slots WHERE date=? AND time=? AND (branch IS NULL OR branch=?)",
                (date_iso, tm, branch),
            )
        else:
            cur.execute("DELETE FROM lesson_extra_slots WHERE date=? AND time=?", (date_iso, tm))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def get_lesson_user(telegram_id: str) -> dict | None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM lesson_users WHERE telegram_id=? LIMIT 1", (str(telegram_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def upsert_lesson_user(telegram_id: str, lang: str | None = None, first_name: str | None = None, username: str | None = None, full_name: str | None = None) -> None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_users(telegram_id, lang, first_name, full_name, username)
            VALUES (?,?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET
              lang=COALESCE(excluded.lang, lesson_users.lang),
              first_name=COALESCE(excluded.first_name, lesson_users.first_name),
              full_name=COALESCE(excluded.full_name, lesson_users.full_name),
              username=COALESCE(excluded.username, lesson_users.username)
            """,
            (str(telegram_id), lang, first_name, full_name, username),
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def set_lesson_user_lang(telegram_id: str, lang: str) -> None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE lesson_users SET lang=? WHERE telegram_id=?", (lang, str(telegram_id)))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def get_lesson_user_reminder_pref(telegram_id: str) -> str | None:
    u = get_lesson_user(str(telegram_id)) or {}
    pref = (u.get("reminder_pref") or "").strip()
    return pref or None


def set_lesson_user_reminder_pref(telegram_id: str, pref: str) -> None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE lesson_users SET reminder_pref=? WHERE telegram_id=?", (pref, str(telegram_id)))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def create_lesson_reminder(reminder_id: str, booking_id: str, telegram_id: str, reminder_target: str, reminder_type: str, scheduled_time: str, admin_id: int | None = None) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_reminders(id, booking_id, telegram_id, admin_id, reminder_target, reminder_type, scheduled_time, sent)
            VALUES (?,?,?,?,?,?,?,0)
            """,
            (reminder_id, str(booking_id), str(telegram_id), admin_id, reminder_target, reminder_type, scheduled_time),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_due_unsent_lesson_reminders(now_iso_utc: str, limit: int = 200) -> list[dict]:
    """
    Fetch due reminders. For SQLite TEXT timestamps we rely on ISO ordering.
    """
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM lesson_reminders
            WHERE sent=0 AND scheduled_time IS NOT NULL AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            LIMIT ?
            """,
            (now_iso_utc, int(limit)),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def mark_lesson_reminder_sent(reminder_id: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE lesson_reminders SET sent=1 WHERE id=?", (str(reminder_id),))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def delete_lesson_reminders_unsent_for_booking(booking_id: str) -> None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM lesson_reminders WHERE booking_id=? AND sent=0", (str(booking_id),))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def list_teacher_telegram_ids_for_student(student_user_id: int) -> list[str]:
    """Distinct teacher telegram_ids linked to student via active group membership."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT t.telegram_id
            FROM user_groups ug
            JOIN groups g ON ug.group_id = g.id
            JOIN users t ON g.teacher_id = t.id
            WHERE ug.user_id = ?
              AND t.login_type = 3
              AND t.telegram_id IS NOT NULL
              AND CAST(t.telegram_id AS TEXT) != ''
            """,
            (int(student_user_id),),
        )
        out: list[str] = []
        for row in cur.fetchall() or []:
            tid = (dict(row) if isinstance(row, dict) else {"telegram_id": row[0]}).get("telegram_id")
            if tid is not None:
                out.append(str(tid))
        return sorted(set(out))
    except Exception:
        return []
    finally:
        conn.close()


def refresh_lesson_reminders_for_booking(booking_id: str) -> None:
    """Rebuild unsent reminders: student 1h + 10m, admin 10m + start + end flows."""
    from datetime import datetime, timedelta, timezone

    import uuid

    b = get_lesson_booking(str(booking_id))
    if not b:
        return
    if str(b.get("status") or "") not in ("pending", "approved"):
        return
    st_raw = b.get("start_ts")
    stu_tg = b.get("student_telegram_id")
    if not st_raw or not stu_tg:
        return
    dt = _parse_iso_utc(str(st_raw))
    if not dt:
        return
    tz_tashkent = pytz.timezone("Asia/Tashkent")
    start_tashkent = dt.astimezone(tz_tashkent)
    now_tashkent = datetime.now(tz_tashkent)
    now = now_tashkent.astimezone(timezone.utc)
    delete_lesson_reminders_unsent_for_booking(str(booking_id))

    rem_1h_tashkent = start_tashkent - timedelta(hours=1)
    rem_1h = rem_1h_tashkent.astimezone(timezone.utc)
    if rem_1h > now:
        create_lesson_reminder(
            uuid.uuid4().hex[:16],
            str(booking_id),
            str(stu_tg),
            "student",
            "1h_before",
            rem_1h.isoformat(),
            None,
        )

    rem_10m_tashkent = start_tashkent - timedelta(minutes=10)
    rem_10m = rem_10m_tashkent.astimezone(timezone.utc)
    if rem_10m > now:
        create_lesson_reminder(
            uuid.uuid4().hex[:16],
            str(booking_id),
            str(stu_tg),
            "student",
            "10m_before",
            rem_10m.isoformat(),
            None,
        )
        for aid in list(dict.fromkeys(ALL_ADMIN_IDS or [])):
            try:
                aid_int = int(aid)
                if aid_int <= 0:
                    continue
                atg = str(aid_int)
            except Exception:
                continue
            create_lesson_reminder(
                uuid.uuid4().hex[:16],
                str(booking_id),
                atg,
                "admin",
                "10m_before",
                rem_10m.isoformat(),
                aid_int,
            )

    # Admin: lesson start attendance prompt (at lesson start).
    if dt > now:
        for aid in list(dict.fromkeys(ALL_ADMIN_IDS or [])):
            try:
                aid_int = int(aid)
                if aid_int <= 0:
                    continue
                atg = str(aid_int)
            except Exception:
                continue
            create_lesson_reminder(
                uuid.uuid4().hex[:16],
                str(booking_id),
                atg,
                "admin",
                "lesson_start_attendance",
                dt.isoformat(),
                aid_int,
            )

    # Admin: lesson end bonus prompt (at lesson end).
    end_raw = b.get("end_ts")
    end_dt = _parse_iso_utc(str(end_raw)) if end_raw else None
    if end_dt and end_dt > now:
        for aid in list(dict.fromkeys(ALL_ADMIN_IDS or [])):
            try:
                aid_int = int(aid)
                if aid_int <= 0:
                    continue
                atg = str(aid_int)
            except Exception:
                continue
            create_lesson_reminder(
                uuid.uuid4().hex[:16],
                str(booking_id),
                atg,
                "admin",
                "lesson_end_bonus",
                end_dt.isoformat(),
                aid_int,
            )


def set_support_booking_attendance(booking_id: str, status: str) -> bool:
    """Set support attendance status for booking (present/late/absent)."""
    st = (status or "").strip().lower()
    if st not in ("present", "late", "absent"):
        return False
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE lesson_bookings
            SET support_attendance_status=?,
                support_attendance_marked_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (st, str(booking_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def apply_support_attendance_penalty_if_needed(booking_id: str, amount: float) -> tuple[bool, int | None]:
    """
    Apply attendance penalty once per booking.
    Returns (applied_now, student_user_id).
    """
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT student_user_id, support_attendance_penalty_applied FROM lesson_bookings WHERE id=? LIMIT 1",
            (str(booking_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, None
        uid = int((row or {}).get("student_user_id") or 0)
        already = int((row or {}).get("support_attendance_penalty_applied") or 0)
        if already == 1:
            return False, uid
        cur.execute(
            """
            UPDATE lesson_bookings
            SET support_attendance_penalty_applied=1, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (str(booking_id),),
        )
        conn.commit()
        return True, uid
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, None
    finally:
        conn.close()


def support_booking_bonus_allowed(booking_id: str) -> bool:
    ensure_support_lessons_schema()
    b = get_lesson_booking(str(booking_id))
    if not b:
        return False
    st = str(b.get("support_attendance_status") or "").lower()
    bonus_awarded = int(b.get("support_bonus_awarded") or 0)
    return st in ("present", "late") and bonus_awarded == 0


def apply_support_bonus_if_needed(booking_id: str, amount: float) -> tuple[bool, int | None]:
    """
    Apply support lesson bonus once per booking.
    Returns (applied_now, student_user_id).
    """
    amt = float(amount or 0)
    if amt <= 0:
        return False, None
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT student_user_id, support_attendance_status, support_bonus_awarded
            FROM lesson_bookings
            WHERE id=?
            LIMIT 1
            """,
            (str(booking_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, None
        uid = int((row or {}).get("student_user_id") or 0)
        st = str((row or {}).get("support_attendance_status") or "").lower()
        awarded = int((row or {}).get("support_bonus_awarded") or 0)
        if st not in ("present", "late") or awarded == 1:
            return False, uid
        cur.execute(
            """
            UPDATE lesson_bookings
            SET support_bonus_awarded=1,
                support_bonus_amount=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (amt, str(booking_id)),
        )
        conn.commit()
        return True, uid
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, None
    finally:
        conn.close()


def refresh_student_1h_reminder_for_booking(booking_id: str) -> None:
    """Backward-compatible alias."""
    refresh_lesson_reminders_for_booking(str(booking_id))


def add_lesson_waitlist(wait_id: str, date_iso: str, time_hhmm: str, branch: str, telegram_id: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_waitlist(id, date, time, branch, telegram_id)
            VALUES (?,?,?,?,?)
            """,
            (str(wait_id), date_iso, time_hhmm, branch, str(telegram_id)),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def pop_lesson_waitlist_for_slot(date_iso: str, time_hhmm: str, branch: str) -> dict | None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM lesson_waitlist
            WHERE date=? AND time=? AND branch=?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (date_iso, time_hhmm, branch),
        )
        row = cur.fetchone()
        if not row:
            return None
        entry = dict(row)
        cur.execute("DELETE FROM lesson_waitlist WHERE id=?", (str(entry.get("id")),))
        conn.commit()
        return entry
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def count_lesson_users() -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM lesson_users")
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def count_lesson_today_bookings(date_iso: str) -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt
            FROM lesson_bookings
            WHERE date=? AND status IN ('pending','approved')
            """,
            (date_iso,),
        )
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def count_lesson_completed_bookings(now_iso_utc: str) -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt
            FROM lesson_bookings
            WHERE start_ts IS NOT NULL AND start_ts < ? AND status IN ('approved','done')
            """,
            (now_iso_utc,),
        )
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


_DEFAULT_BRANCH_WEEKDAYS = {"branch_1": [1, 3, 5], "branch_2": [0, 2, 4]}


def get_lesson_branch_weekdays(branch: str) -> list[int]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT weekdays FROM lesson_branch_weekdays WHERE branch=? LIMIT 1", (str(branch),))
        row = cur.fetchone()
        if not row:
            return list(_DEFAULT_BRANCH_WEEKDAYS.get(str(branch), [1, 3, 5]))
        raw = (dict(row) if isinstance(row, dict) else {"weekdays": row[0]}).get("weekdays") or ""
        parts = [int(x.strip()) for x in str(raw).split(",") if x.strip().isdigit()]
        return sorted(set(parts)) if parts else list(_DEFAULT_BRANCH_WEEKDAYS.get(str(branch), [1, 3, 5]))
    except Exception:
        return list(_DEFAULT_BRANCH_WEEKDAYS.get(str(branch), [1, 3, 5]))
    finally:
        conn.close()


def set_lesson_branch_weekdays(branch: str, weekdays: list[int]) -> bool:
    ensure_support_lessons_schema()
    wcsv = ",".join(str(int(d)) for d in sorted(set(weekdays)))
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_branch_weekdays(branch, weekdays)
            VALUES (?,?)
            ON CONFLICT(branch) DO UPDATE SET weekdays=excluded.weekdays
            """,
            (str(branch), wcsv),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception("set_lesson_branch_weekdays failed branch=%s weekdays=%s", branch, wcsv)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def is_branch_date_closed_for_booking(branch: str, date_iso: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM lesson_branch_date_closed
            WHERE date=? AND (branch=? OR branch='all')
            LIMIT 1
            """,
            (date_iso, str(branch)),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()


def set_branch_date_closed(branch: str, date_iso: str, reason: str | None) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_branch_date_closed(branch, date, reason)
            VALUES (?,?,?)
            ON CONFLICT(branch, date) DO UPDATE SET reason=excluded.reason
            """,
            (str(branch), date_iso, reason or ""),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception("set_branch_date_closed failed branch=%s date=%s", branch, date_iso)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def open_branch_date_for_booking(branch: str, date_iso: str) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM lesson_branch_date_closed WHERE branch=? AND date=?", (str(branch), date_iso))
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("open_branch_date_for_booking failed branch=%s date=%s", branch, date_iso)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_branch_dates_closed(branch: str | None = None) -> list[dict]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if branch:
            cur.execute(
                "SELECT * FROM lesson_branch_date_closed WHERE branch=? OR branch='all' ORDER BY date ASC",
                (str(branch),),
            )
        else:
            cur.execute("SELECT * FROM lesson_branch_date_closed ORDER BY branch ASC, date ASC")
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_branch_date_closed_reason(branch: str, date_iso: str) -> str | None:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT reason FROM lesson_branch_date_closed
            WHERE date=? AND (branch=? OR branch='all')
            ORDER BY CASE WHEN branch='all' THEN 1 ELSE 0 END ASC
            LIMIT 1
            """,
            (date_iso, str(branch)),
        )
        row = cur.fetchone()
        if not row:
            return None
        rs = (dict(row) if isinstance(row, dict) else {"reason": row[0]}).get("reason")
        return str(rs or "").strip() or None
    except Exception:
        return None
    finally:
        conn.close()


def is_slot_blocked(branch: str, date_iso: str, time_hhmm: str) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM lesson_blocked_slots
            WHERE branch=? AND date=? AND time=?
            LIMIT 1
            """,
            (str(branch), date_iso, tm),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()


def add_blocked_slot(
    slot_id: str, branch: str, date_iso: str, time_hhmm: str, reason: str | None, created_by: int | None
) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM lesson_blocked_slots WHERE branch=? AND date=? AND time=?",
            (str(branch), date_iso, tm),
        )
        cur.execute(
            """
            INSERT INTO lesson_blocked_slots(id, branch, date, time, reason, created_by)
            VALUES (?,?,?,?,?,?)
            """,
            (str(slot_id), str(branch), date_iso, tm, reason or "", created_by),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception(
            "add_blocked_slot failed slot_id=%s branch=%s date=%s time=%s created_by=%s",
            slot_id,
            branch,
            date_iso,
            tm,
            created_by,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def remove_blocked_slot(branch: str, date_iso: str, time_hhmm: str) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM lesson_blocked_slots WHERE branch=? AND date=? AND time=?",
            (str(branch), date_iso, tm),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("remove_blocked_slot failed branch=%s date=%s time=%s", branch, date_iso, tm)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_blocked_slots_for_date(branch: str, date_iso: str) -> list[dict]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM lesson_blocked_slots WHERE branch=? AND date=? ORDER BY time ASC",
            (str(branch), date_iso),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def add_recurring_slot_rule(
    rule_id: str,
    branch: str,
    weekday: int,
    time_hhmm: str,
    mode: str,
    reason: str | None,
    created_by: int | None,
    active: int = 1,
) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    md = (mode or "").strip().lower()
    if not tm or md not in ("open", "close"):
        return False
    if weekday < 0 or weekday > 6:
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO lesson_recurring_slot_rules(id, branch, weekday, time, mode, reason, created_by, active)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(branch, weekday, time, mode)
            DO UPDATE SET reason=excluded.reason, created_by=excluded.created_by, active=excluded.active
            """,
            (str(rule_id), str(branch), int(weekday), tm, md, reason or "", created_by, int(active)),
        )
        conn.commit()
        return True
    except Exception:
        logger.exception(
            "add_recurring_slot_rule failed branch=%s weekday=%s time=%s mode=%s active=%s",
            branch,
            weekday,
            tm,
            md,
            active,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def remove_recurring_slot_rule(branch: str, weekday: int, time_hhmm: str, mode: str) -> bool:
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    md = (mode or "").strip().lower()
    if not tm or md not in ("open", "close"):
        return False
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM lesson_recurring_slot_rules WHERE branch=? AND weekday=? AND time=? AND mode=?",
            (str(branch), int(weekday), tm, md),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception(
            "remove_recurring_slot_rule failed branch=%s weekday=%s time=%s mode=%s",
            branch,
            weekday,
            tm,
            md,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def list_recurring_slot_rules(branch: str | None = None, weekday: int | None = None, mode: str | None = None) -> list[dict]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        where = ["active=1"]
        vals: list = []
        if branch:
            where.append("branch=?")
            vals.append(str(branch))
        if weekday is not None:
            where.append("weekday=?")
            vals.append(int(weekday))
        if mode:
            where.append("mode=?")
            vals.append(str(mode).strip().lower())
        q = "SELECT * FROM lesson_recurring_slot_rules"
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY branch ASC, weekday ASC, time ASC"
        cur.execute(q, tuple(vals))
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def list_recurring_open_times_for_date(branch: str, date_iso: str) -> list[str]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        from datetime import datetime

        wd = datetime.strptime(date_iso, "%Y-%m-%d").date().weekday()
        cur.execute(
            """
            SELECT time FROM lesson_recurring_slot_rules
            WHERE active=1 AND branch=? AND weekday=? AND mode='open'
            ORDER BY time ASC
            """,
            (str(branch), int(wd)),
        )
        rows = cur.fetchall() or []
        out: list[str] = []
        for r in rows:
            out.append(str((dict(r) if isinstance(r, dict) else {"time": r[0]}).get("time") or ""))
        return [x for x in out if x]
    except Exception:
        return []
    finally:
        conn.close()


def get_slot_block_reason(branch: str, date_iso: str, time_hhmm: str) -> str | None:
    from datetime import datetime
    from support_booking_time import normalize_time_hhmm

    ensure_support_lessons_schema()
    tm = normalize_time_hhmm(time_hhmm)
    if not tm:
        return None
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Highest priority: date closed
        cur.execute(
            """
            SELECT reason FROM lesson_branch_date_closed
            WHERE date=? AND (branch=? OR branch='all')
            ORDER BY CASE WHEN branch='all' THEN 1 ELSE 0 END ASC
            LIMIT 1
            """,
            (date_iso, str(branch)),
        )
        r0 = cur.fetchone()
        if r0:
            rs = (dict(r0) if isinstance(r0, dict) else {"reason": r0[0]}).get("reason")
            return str(rs or "").strip() or None

        wd = datetime.strptime(date_iso, "%Y-%m-%d").date().weekday()
        # Recurring close
        cur.execute(
            """
            SELECT reason FROM lesson_recurring_slot_rules
            WHERE active=1 AND branch=? AND weekday=? AND time=? AND mode='close'
            LIMIT 1
            """,
            (str(branch), int(wd), tm),
        )
        r1 = cur.fetchone()
        if r1:
            rs = (dict(r1) if isinstance(r1, dict) else {"reason": r1[0]}).get("reason")
            return str(rs or "").strip() or None

        # Date-specific close
        cur.execute(
            """
            SELECT reason FROM lesson_blocked_slots
            WHERE branch=? AND date=? AND time=?
            LIMIT 1
            """,
            (str(branch), date_iso, tm),
        )
        r2 = cur.fetchone()
        if r2:
            rs = (dict(r2) if isinstance(r2, dict) else {"reason": r2[0]}).get("reason")
            return str(rs or "").strip() or None
        return None
    except Exception:
        return None
    finally:
        conn.close()


def is_slot_closed_effective(branch: str, date_iso: str, time_hhmm: str) -> bool:
    return get_slot_block_reason(str(branch), str(date_iso), str(time_hhmm)) is not None


def update_lesson_booking_branch(booking_id: str, branch: str, admin_id: int | None = None) -> bool:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE lesson_bookings
            SET branch=?, handled_by_admin_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (str(branch), admin_id, str(booking_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("update_lesson_booking_branch failed booking_id=%s branch=%s admin_id=%s", booking_id, branch, admin_id)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def is_lesson_otmen_date_cancelled(date_str: str) -> bool:
    """True when admin otmen request for date is already marked cancelled."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1
            FROM lesson_otmen_requests
            WHERE date_str=? AND status='cancelled'
            LIMIT 1
            """,
            (str(date_str),),
        )
        return cur.fetchone() is not None
    except Exception:
        logger.exception("is_lesson_otmen_date_cancelled failed date=%s", date_str)
        return False
    finally:
        conn.close()


def list_lesson_upcoming_bookings(page: int = 1, per_page: int = 10, now_iso_utc: str | None = None) -> tuple[list[dict], int]:
    from datetime import datetime, timezone

    ensure_support_lessons_schema()
    if now_iso_utc is None:
        now_iso_utc = datetime.now(timezone.utc).isoformat()
    page = max(1, int(page or 1))
    per_page = max(1, min(50, int(per_page or 10)))
    offset = (page - 1) * per_page
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt FROM lesson_bookings
            WHERE status IN ('pending','approved')
              AND (
                (end_ts IS NOT NULL AND end_ts != '' AND end_ts > ?)
                OR ((end_ts IS NULL OR end_ts = '') AND start_ts IS NOT NULL AND start_ts != '' AND start_ts > ?)
              )
            """,
            (now_iso_utc, now_iso_utc),
        )
        total = int((cur.fetchone() or {}).get("cnt") or 0)
        total_pages = max(1, (total + per_page - 1) // per_page)
        cur.execute(
            """
            SELECT * FROM lesson_bookings
            WHERE status IN ('pending','approved')
              AND (
                (end_ts IS NOT NULL AND end_ts != '' AND end_ts > ?)
                OR ((end_ts IS NULL OR end_ts = '') AND start_ts IS NOT NULL AND start_ts != '' AND start_ts > ?)
              )
            ORDER BY COALESCE(start_ts, '9999-12-31T23:59:59+00:00') ASC
            LIMIT ? OFFSET ?
            """,
            (now_iso_utc, now_iso_utc, per_page, offset),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows], total_pages
    except Exception:
        return [], 1
    finally:
        conn.close()


def count_lesson_bookings_total() -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM lesson_bookings")
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def count_lesson_active_upcoming(now_iso_utc: str) -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt FROM lesson_bookings
            WHERE status IN ('pending','approved')
              AND (
                (end_ts IS NOT NULL AND end_ts != '' AND end_ts > ?)
                OR ((end_ts IS NULL OR end_ts = '') AND start_ts IS NOT NULL AND start_ts != '' AND start_ts > ?)
              )
            """,
            (now_iso_utc, now_iso_utc),
        )
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def count_lesson_past_ended(now_iso_utc: str) -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt FROM lesson_bookings
            WHERE end_ts IS NOT NULL AND end_ts != '' AND end_ts <= ?
            """,
            (now_iso_utc,),
        )
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def _count_bookings_created_between(t0_iso: str, t1_iso: str) -> int:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) as cnt FROM lesson_bookings
            WHERE created_at >= ? AND created_at < ?
            """,
            (t0_iso, t1_iso),
        )
        return int((cur.fetchone() or {}).get("cnt") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def support_dashboard_metrics(today_date_iso: str, now_utc_iso: str) -> dict:
    """
    today_date_iso: YYYY-MM-DD in Asia/Tashkent.
    Returns counts and simple MoM % for bookings created in calendar month windows (SQLite created_at).
    """
    from calendar import monthrange
    from datetime import date, datetime, timedelta, timezone

    ensure_support_lessons_schema()
    today = datetime.strptime(today_date_iso, "%Y-%m-%d").date()
    y, m = today.year, today.month
    start_this = date(y, m, 1)
    if m == 1:
        start_prev = date(y - 1, 12, 1)
        end_prev = date(y, 1, 1)
    else:
        start_prev = date(y, m - 1, 1)
        end_prev = start_this
    _, last_day = monthrange(y, m)
    end_this_exclusive = start_this + timedelta(days=last_day)

    def d_iso(d: date) -> str:
        return d.isoformat() + " 00:00:00"

    c_this = _count_bookings_created_between(d_iso(start_this), d_iso(end_this_exclusive))
    c_prev = _count_bookings_created_between(d_iso(start_prev), d_iso(end_prev))

    def pct_change(cur: int, prev: int) -> str | None:
        if prev <= 0:
            return None if cur == 0 else "+100%"
        p = round((cur - prev) * 100.0 / prev, 1)
        return f"{p:+.1f}%"

    today_n = count_lesson_today_bookings(today_date_iso)
    # MoM for "today" vs same metric on same day-of-month last month is noisy; compare month-to-date totals instead.
    mtd_start = d_iso(start_this)
    mtd_now = today_date_iso + " 23:59:59"
    prev_month_same_span_end = min(today.replace(year=start_prev.year, month=start_prev.month, day=min(today.day, monthrange(start_prev.year, start_prev.month)[1])), end_prev - timedelta(days=1))
    mtd_prev_start = d_iso(start_prev)
    mtd_prev_end = prev_month_same_span_end.isoformat() + " 23:59:59"
    mtd_cur = _count_bookings_created_between(mtd_start, mtd_now)
    mtd_prev = _count_bookings_created_between(mtd_prev_start, mtd_prev_end)

    return {
        "lesson_users": count_lesson_users(),
        "active_upcoming": count_lesson_active_upcoming(now_utc_iso),
        "past_ended": count_lesson_past_ended(now_utc_iso),
        "today_bookings": today_n,
        "total_bookings": count_lesson_bookings_total(),
        "bookings_created_this_month": c_this,
        "bookings_created_last_month": c_prev,
        "mom_created_month_pct": pct_change(c_this, c_prev),
        "mtd_bookings": mtd_cur,
        "mtd_prev_month_bookings": mtd_prev,
        "mom_mtd_pct": pct_change(mtd_cur, mtd_prev),
    }


def list_student_telegram_ids_with_upcoming_bookings(now_iso_utc: str) -> list[str]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT student_telegram_id FROM lesson_bookings
            WHERE status IN ('pending','approved')
              AND student_telegram_id IS NOT NULL AND student_telegram_id != ''
              AND (
                (end_ts IS NOT NULL AND end_ts != '' AND end_ts > ?)
                OR ((end_ts IS NULL OR end_ts = '') AND start_ts IS NOT NULL AND start_ts != '' AND start_ts > ?)
              )
            """,
            (now_iso_utc, now_iso_utc),
        )
        out: list[str] = []
        for r in cur.fetchall() or []:
            tg = (dict(r) if isinstance(r, dict) else {"student_telegram_id": r[0]}).get("student_telegram_id")
            if tg:
                out.append(str(tg))
        return sorted(set(out))
    except Exception:
        return []
    finally:
        conn.close()


def list_student_telegram_ids_had_bookings() -> list[str]:
    ensure_support_lessons_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT student_telegram_id FROM lesson_bookings
            WHERE student_telegram_id IS NOT NULL AND student_telegram_id != ''
            """
        )
        out: list[str] = []
        for r in cur.fetchall() or []:
            tg = (dict(r) if isinstance(r, dict) else {"student_telegram_id": r[0]}).get("student_telegram_id")
            if tg:
                out.append(str(tg))
        return sorted(set(out))
    except Exception:
        return []
    finally:
        conn.close()


def list_all_student_telegram_ids() -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT telegram_id FROM users
            WHERE login_type IN (1, 2)
              AND telegram_id IS NOT NULL AND CAST(telegram_id AS TEXT) != ''
            """
        )
        out: list[str] = []
        for r in cur.fetchall() or []:
            tg = (dict(r) if isinstance(r, dict) else {"telegram_id": r[0]}).get("telegram_id")
            if tg is not None:
                out.append(str(tg))
        return sorted(set(out))
    except Exception:
        return []
    finally:
        conn.close()


def set_daily_test_upload_permission(teacher_id: int, allowed: bool):
    """Allow/restrict a teacher from uploading daily tests."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET can_upload_daily_tests=? WHERE id=?",
        (1 if allowed else 0, teacher_id),
    )
    conn.commit()
    conn.close()


def get_daily_test_upload_permission(teacher_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT can_upload_daily_tests FROM users WHERE id=?", (teacher_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row["can_upload_daily_tests"]) if row else False


def set_teacher_ai_generation_permission(teacher_id: int, allowed: bool) -> None:
    """Allow/restrict a teacher from using AI generator for vocab/daily-tests."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET can_generate_ai=? WHERE id=?",
        (1 if allowed else 0, teacher_id),
    )
    conn.commit()
    conn.close()


def get_teacher_ai_generation_permission(teacher_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT login_type, can_generate_ai FROM users WHERE id=?", (teacher_id,))
        row = cur.fetchone()
        if not row:
            return False
        # New policy: all teachers can use AI generator.
        if int(row.get("login_type") or 0) == 3:
            return True
        return bool(row["can_generate_ai"])
    except Exception:
        return False
    finally:
        conn.close()


def ensure_student_ai_chat_schema() -> None:
    """Track daily student AI chat quota usage."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS student_ai_chat_usage (
                user_id BIGINT NOT NULL,
                usage_date DATE NOT NULL,
                requests_count INTEGER NOT NULL DEFAULT 0,
                last_prompt TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, usage_date),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            '''
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_subject_dcoin_schema() -> bool:
    """Per-subject D'coin balances and subject-aware history."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_subject_dcoins (
                user_id BIGINT NOT NULL,
                subject TEXT NOT NULL,
                balance DOUBLE PRECISION NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            '''
        )
        if _is_postgres_enabled():
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='user_subject_dcoins' AND column_name='dcoin'
                LIMIT 1
                """
            )
            if cur.fetchone():
                cur.execute("ALTER TABLE user_subject_dcoins RENAME COLUMN dcoin TO balance")
        else:
            try:
                cur.execute("ALTER TABLE user_subject_dcoins RENAME COLUMN dcoin TO balance")
            except Exception:
                pass
        try:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_subject_dcoins_user_id ON user_subject_dcoins(user_id)"
            )
        except Exception:
            pass
        try:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_subject_dcoins_subject ON user_subject_dcoins(subject)"
            )
        except Exception:
            pass
        if _is_postgres_enabled():
            cur.execute("ALTER TABLE diamond_history ADD COLUMN IF NOT EXISTS subject TEXT")
            cur.execute("ALTER TABLE diamond_history ADD COLUMN IF NOT EXISTS change_type TEXT")
        else:
            try:
                cur.execute("ALTER TABLE diamond_history ADD COLUMN subject TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE diamond_history ADD COLUMN change_type TEXT")
            except Exception:
                pass
        conn.commit()
        return True
    except Exception:
        logger.exception("Failed to ensure subject D'coin schema")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def _migration_applied(cur, name: str) -> bool:
    try:
        cur.execute("SELECT 1 FROM _migrations WHERE name=? LIMIT 1", (name,))
        return bool(cur.fetchone())
    except Exception:
        return False


def _mark_migration_applied(cur, conn, name: str) -> None:
    try:
        if _is_postgres_enabled():
            cur.execute(
                "INSERT INTO _migrations(name) VALUES (?) ON CONFLICT DO NOTHING",
                (name,),
            )
        else:
            cur.execute("INSERT OR IGNORE INTO _migrations(name) VALUES (?)", (name,))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def ensure_dcoin_schema_migrations() -> None:
    """
    One-time: diamond_history.diamonds_change -> dcoin_change; duel sessions table rename;
    legacy users.diamonds backfill then DROP; add change_type column.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        # 1) diamond_history column rename
        if not _migration_applied(cur, "dh_dcoin_change_rename"):
            if _is_postgres_enabled():
                try:
                    cur.execute(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='diamond_history'
                          AND column_name='diamonds_change'
                        """
                    )
                    if cur.fetchone():
                        cur.execute(
                            "ALTER TABLE diamond_history RENAME COLUMN diamonds_change TO dcoin_change"
                        )
                    cur.execute(
                        "ALTER TABLE diamond_history ADD COLUMN IF NOT EXISTS change_type TEXT"
                    )
                    cur.execute(
                        "ALTER TABLE diamond_history ADD COLUMN IF NOT EXISTS subject TEXT"
                    )
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur = conn.cursor()
            else:
                try:
                    cur.execute("PRAGMA table_info(diamond_history)")
                    cols = {str(r[1]) for r in cur.fetchall()}
                except Exception:
                    cols = set()
                if "dcoin_change" not in cols and "diamonds_change" in cols:
                    try:
                        cur.execute(
                            "ALTER TABLE diamond_history RENAME COLUMN diamonds_change TO dcoin_change"
                        )
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        cur = conn.cursor()
                try:
                    cur.execute("ALTER TABLE diamond_history ADD COLUMN change_type TEXT")
                except Exception:
                    pass
                try:
                    cur.execute("ALTER TABLE diamond_history ADD COLUMN subject TEXT")
                except Exception:
                    pass
            _mark_migration_applied(cur, conn, "dh_dcoin_change_rename")

        # 2) Rename legacy duel table arena_duel_match_sessions -> open_duel_sessions
        if not _migration_applied(cur, "duel_open_sessions_rename"):
            legacy_tbl = "arena_duel_match_sessions"
            new_tbl = "open_duel_sessions"
            if _is_postgres_enabled():
                try:
                    cur.execute(
                        """
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema='public' AND table_name=?
                        """,
                        (legacy_tbl,),
                    )
                    old_exists = bool(cur.fetchone())
                    cur.execute(
                        """
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema='public' AND table_name=?
                        """,
                        (new_tbl,),
                    )
                    new_exists = bool(cur.fetchone())
                    if old_exists and not new_exists:
                        cur.execute(f"ALTER TABLE {legacy_tbl} RENAME TO {new_tbl}")
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur = conn.cursor()
            else:
                try:
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (legacy_tbl,),
                    )
                    old_exists = bool(cur.fetchone())
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (new_tbl,),
                    )
                    new_exists = bool(cur.fetchone())
                    if old_exists and not new_exists:
                        cur.execute(f"ALTER TABLE {legacy_tbl} RENAME TO {new_tbl}")
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur = conn.cursor()
            _mark_migration_applied(cur, conn, "duel_open_sessions_rename")

        # 3) Legacy users.diamonds -> user_subject_dcoins then DROP
        if not _migration_applied(cur, "users_drop_legacy_diamonds"):
            has_diamonds = False
            if _is_postgres_enabled():
                try:
                    cur.execute(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='users' AND column_name='diamonds'
                        """
                    )
                    has_diamonds = bool(cur.fetchone())
                except Exception:
                    has_diamonds = False
            else:
                try:
                    cur.execute("PRAGMA table_info(users)")
                    has_diamonds = any(str(r[1]) == "diamonds" for r in cur.fetchall())
                except Exception:
                    has_diamonds = False
            if has_diamonds:
                ensure_subject_dcoin_schema()
                try:
                    if _is_postgres_enabled():
                        cur.execute(
                            "SELECT id FROM users WHERE COALESCE(diamonds, 0) > 0"
                        )
                    else:
                        cur.execute(
                            "SELECT id FROM users WHERE COALESCE(diamonds, 0) > 0"
                        )
                    for row in cur.fetchall() or []:
                        _migrate_legacy_user_diamonds_to_subjects(int(row["id"]))
                except Exception:
                    logger.exception("Bulk legacy diamonds migration failed")
                try:
                    if _is_postgres_enabled():
                        cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS diamonds")
                        cur.execute(
                            "ALTER TABLE users DROP COLUMN IF EXISTS last_diamond_update"
                        )
                    else:
                        try:
                            cur.execute("ALTER TABLE users DROP COLUMN diamonds")
                        except Exception:
                            pass
                        try:
                            cur.execute("ALTER TABLE users DROP COLUMN last_diamond_update")
                        except Exception:
                            pass
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            _mark_migration_applied(cur, conn, "users_drop_legacy_diamonds")

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_support_lessons_schema() -> None:
    """
    Support / Lesson booking schema aligned with Lesson Sessions bot.
    Cross-DB friendly (SQLite + Postgres) by using TEXT primary keys.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        except Exception:
            pass

        # Admin/user prefs for support bot (and optional student-side booking prefs)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_users (
                telegram_id TEXT PRIMARY KEY,
                lang TEXT,
                first_name TEXT,
                full_name TEXT,
                username TEXT,
                reminder_pref TEXT DEFAULT '1h',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_bookings (
                id TEXT PRIMARY KEY,
                student_user_id BIGINT NOT NULL,
                student_telegram_id TEXT,
                branch TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                start_ts TEXT,
                purpose TEXT,
                status TEXT NOT NULL DEFAULT 'approved',
                handled_by_admin_id BIGINT,
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Reminders (4h/30m/pref1h/pref24h, plus optional teacher/admin reminders)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_reminders (
                id TEXT PRIMARY KEY,
                booking_id TEXT NOT NULL,
                telegram_id TEXT NOT NULL,
                admin_id BIGINT,
                reminder_target TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                scheduled_time TEXT,
                sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Closed dates with reason (admin managed)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_closed_dates (
                date TEXT PRIMARY KEY,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_holidays (
                date TEXT PRIMARY KEY
            )
            """
        )
        # Waitlist
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_waitlist (
                id TEXT PRIMARY KEY,
                date TEXT,
                time TEXT,
                branch TEXT,
                telegram_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Extra slots (admin-managed additional 30-min slots)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_extra_slots (
                id TEXT PRIMARY KEY,
                date TEXT,
                time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_bookings_student_user_id ON lesson_bookings(student_user_id)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_bookings_status ON lesson_bookings(status)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_bookings_start_ts ON lesson_bookings(start_ts)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_reminders_scheduled_time ON lesson_reminders(scheduled_time)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_reminders_sent ON lesson_reminders(sent)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_extra_slots_date ON lesson_extra_slots(date)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_branch_weekdays (
                branch TEXT PRIMARY KEY,
                weekdays TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_blocked_slots (
                id TEXT PRIMARY KEY,
                branch TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                reason TEXT,
                created_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(branch, date, time)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_branch_date_closed (
                branch TEXT NOT NULL,
                date TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (branch, date)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_recurring_slot_rules (
                id TEXT PRIMARY KEY,
                branch TEXT NOT NULL,
                weekday INTEGER NOT NULL,
                time TEXT NOT NULL,
                mode TEXT NOT NULL,
                reason TEXT,
                created_by BIGINT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(branch, weekday, time, mode)
            )
            """
        )
        # Commit core support schema before optional/legacy steps.
        # This prevents optional-step rollbacks from undoing required table creation on Postgres.
        conn.commit()
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='lesson_extra_slots' AND column_name='branch'
                """
            ) if _is_postgres_enabled() else cur.execute("PRAGMA table_info(lesson_extra_slots)")
            has_branch = bool(cur.fetchone()) if _is_postgres_enabled() else any(
                str((dict(r) if isinstance(r, dict) else {"name": r[1]}).get("name")) == "branch"
                for r in (cur.fetchall() or [])
            )
            if not has_branch:
                cur.execute("ALTER TABLE lesson_extra_slots ADD COLUMN branch TEXT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute(
                """
                INSERT INTO lesson_branch_weekdays(branch, weekdays)
                VALUES (?, ?)
                ON CONFLICT(branch) DO NOTHING
                """,
                ("branch_1", "1,3,5"),
            )
            cur.execute(
                """
                INSERT INTO lesson_branch_weekdays(branch, weekdays)
                VALUES (?, ?)
                ON CONFLICT(branch) DO NOTHING
                """,
                ("branch_2", "0,2,4"),
            )
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_blocked_slots_branch_date ON lesson_blocked_slots(branch, date)")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_lesson_recurring_slot_rules_lookup ON lesson_recurring_slot_rules(branch, weekday, time, mode, active)"
            )
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='lesson_bookings' AND column_name='end_ts'
                """
            ) if _is_postgres_enabled() else cur.execute("PRAGMA table_info(lesson_bookings)")
            has_end_ts = bool(cur.fetchone()) if _is_postgres_enabled() else any(
                str((dict(r) if isinstance(r, dict) else {"name": r[1]}).get("name")) == "end_ts"
                for r in (cur.fetchall() or [])
            )
            if not has_end_ts:
                cur.execute("ALTER TABLE lesson_bookings ADD COLUMN end_ts TEXT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        # Support lesson attendance/bonus state columns.
        for col_name, col_sql in (
            ("support_attendance_status", "TEXT"),
            ("support_attendance_marked_at", "TIMESTAMP"),
            ("support_attendance_penalty_applied", "INTEGER DEFAULT 0"),
            ("support_bonus_awarded", "INTEGER DEFAULT 0"),
            ("support_bonus_amount", "DOUBLE PRECISION DEFAULT 0"),
        ):
            try:
                if _is_postgres_enabled():
                    cur.execute(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='lesson_bookings' AND column_name=?
                        """,
                        (col_name,),
                    )
                    has_col = bool(cur.fetchone())
                else:
                    cur.execute("PRAGMA table_info(lesson_bookings)")
                    has_col = any(
                        str((dict(r) if isinstance(r, dict) else {"name": r[1]}).get("name")) == col_name
                        for r in (cur.fetchall() or [])
                    )
                if not has_col:
                    cur.execute(f"ALTER TABLE lesson_bookings ADD COLUMN {col_name} {col_sql}")
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        # One-time backfill: normalize time columns from '14' -> '14:00' etc.
        if not _migration_applied(cur, "support_lessons_time_backfill_hhmm"):
            from support_booking_time import normalize_time_hhmm

            def _backfill_table(table: str) -> None:
                try:
                    cur.execute(f"SELECT id, time FROM {table}")
                    rows = cur.fetchall() or []
                except Exception:
                    rows = []
                for r in rows:
                    try:
                        rid = (r.get("id") if isinstance(r, dict) else r[0])  # type: ignore[index]
                        rt = (r.get("time") if isinstance(r, dict) else r[1])  # type: ignore[index]
                        tm = normalize_time_hhmm(str(rt))
                        if tm and str(rt) != tm:
                            cur.execute(f"UPDATE {table} SET time=? WHERE id=?", (tm, str(rid)))
                    except Exception:
                        continue

            _backfill_table("lesson_bookings")
            _backfill_table("lesson_extra_slots")
            _backfill_table("lesson_blocked_slots")
            _mark_migration_applied(cur, conn, "support_lessons_time_backfill_hhmm")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()
    _backfill_lesson_bookings_end_ts()


def _parse_iso_utc(s: str | None):
    from datetime import datetime, timezone

    if not s:
        return None
    t = str(s).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _backfill_lesson_bookings_end_ts() -> None:
    """Set end_ts = start_ts + 60 minutes where missing (legacy rows)."""
    from datetime import timedelta, timezone

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, start_ts FROM lesson_bookings
            WHERE (end_ts IS NULL OR end_ts = '') AND start_ts IS NOT NULL AND start_ts != ''
            """
        )
        rows = cur.fetchall() or []
        for r in rows:
            rid = dict(r).get("id") if isinstance(r, dict) else r[0]
            st = dict(r).get("start_ts") if isinstance(r, dict) else r[1]
            dt = _parse_iso_utc(st)
            if not dt:
                continue
            end = (dt + timedelta(minutes=60)).isoformat()
            cur.execute("UPDATE lesson_bookings SET end_ts=? WHERE id=?", (end, str(rid)))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def student_has_active_upcoming_booking(student_user_id: int, now_iso_utc: str | None = None) -> bool:
    """True if student has pending/approved booking whose lesson end is still in the future."""
    from datetime import datetime, timezone

    ensure_support_lessons_schema()
    if now_iso_utc is None:
        now_iso_utc = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM lesson_bookings
            WHERE student_user_id = ?
              AND status IN ('pending', 'approved')
              AND end_ts IS NOT NULL
              AND end_ts > ?
            LIMIT 1
            """,
            (int(student_user_id), now_iso_utc),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()


def get_last_ended_lesson_end_ts(student_user_id: int, now_iso_utc: str | None = None) -> str | None:
    """Most recent lesson end_ts that is already in the past (for cooldown messaging)."""
    from datetime import datetime, timezone

    ensure_support_lessons_schema()
    if now_iso_utc is None:
        now_iso_utc = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT end_ts FROM lesson_bookings
            WHERE student_user_id = ?
              AND end_ts IS NOT NULL
              AND end_ts < ?
            ORDER BY end_ts DESC
            LIMIT 1
            """,
            (int(student_user_id), now_iso_utc),
        )
        row = cur.fetchone()
        if not row:
            return None
        return (dict(row) if isinstance(row, dict) else {"end_ts": row[0]}).get("end_ts")
    except Exception:
        return None
    finally:
        conn.close()


def get_next_lesson_booking_allowed_after_utc_iso(student_user_id: int, now_iso_utc: str | None = None) -> str | None:
    """
    If the student must wait (6 hours after last finished lesson), return UTC ISO when booking is allowed.
    Returns None if no cooldown applies (caller must still check active booking).
    """
    from datetime import datetime, timedelta, timezone

    ensure_support_lessons_schema()
    if now_iso_utc is None:
        now_iso_utc = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT end_ts FROM lesson_bookings
            WHERE student_user_id = ?
              AND end_ts IS NOT NULL
              AND end_ts < ?
            ORDER BY end_ts DESC
            LIMIT 1
            """,
            (int(student_user_id), now_iso_utc),
        )
        row = cur.fetchone()
        if not row:
            return None
        end_s = (dict(row) if isinstance(row, dict) else {"end_ts": row[0]}).get("end_ts")
        last_end = _parse_iso_utc(end_s)
        now = _parse_iso_utc(now_iso_utc)
        if not last_end or not now:
            return None
        unlock = last_end + timedelta(hours=6)
        if unlock > now:
            return unlock.isoformat()
        return None
    except Exception:
        return None
    finally:
        conn.close()


def ensure_lesson_otmen_requests_schema() -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_otmen_requests (
                id TEXT PRIMARY KEY,
                date_str TEXT NOT NULL,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                cancelled_at TIMESTAMP,
                cancelled_by_admin_id BIGINT
            )
            """
        )
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_otmen_requests_date ON lesson_otmen_requests(date_str)")
        except Exception:
            pass
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def _migrate_legacy_user_diamonds_to_subjects(user_id: int, forced_subject: str | None = None) -> None:
    """
    Legacy compatibility:
    If `user_subject_dcoins` has no balance for a user yet, but `users.diamonds` has a value,
    initialize `user_subject_dcoins` by distributing legacy total equally across the user's subjects.

    After migration, `users.diamonds` is no longer used for balances (we only seed subject rows once).
    """
    ensure_subject_dcoin_schema()

    forced_subj = (forced_subject or "").strip().title()

    conn = get_conn()
    cur = conn.cursor()
    try:
        # If user already has any subject balance, do nothing.
        cur.execute("SELECT COALESCE(SUM(balance), 0) as total FROM user_subject_dcoins WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        total_subject_balance = float((row or {}).get("total") or 0)
        if total_subject_balance > 0:
            return

        try:
            cur.execute("SELECT COALESCE(diamonds, 0) as legacy_total FROM users WHERE id=?", (user_id,))
        except Exception:
            return
        lrow = cur.fetchone()
        legacy_total = float((lrow or {}).get("legacy_total") or 0)
        if legacy_total <= 0:
            return

        # Determine subjects for this user.
        subjects = get_user_subjects(user_id) or []
        if forced_subj:
            if forced_subj not in subjects:
                subjects = [forced_subj]
        if not subjects:
            # Fallback: use users.subject if present, else English
            cur.execute("SELECT subject FROM users WHERE id=?", (user_id,))
            urow = cur.fetchone()
            raw_subj = (urow or {}).get("subject") if urow else None
            sub = (raw_subj or "").strip().title() if raw_subj else "English"
            subjects = [sub]

        subjects = list(dict.fromkeys([s.strip().title() for s in subjects if s and s.strip()]))
        if not subjects:
            subjects = ["English"]

        share = legacy_total / float(len(subjects))

        for subj in subjects:
            cur.execute(
                '''
                INSERT INTO user_subject_dcoins(user_id, subject, balance, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, subject)
                DO UPDATE SET balance=excluded.balance, updated_at=excluded.updated_at
                ''',
                (int(user_id), subj, share),
            )

        conn.commit()
        # Migration for older DBs (table exists but column missing).
        try:
            _ensure_arena_run_answers_is_unanswered_column()
        except Exception:
            pass
    finally:
        conn.close()


def get_user_subject_dcoins(user_id: int) -> dict[str, float]:
    ensure_subject_dcoin_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT subject, balance FROM user_subject_dcoins WHERE user_id=?",
            (user_id,),
        )
        rows = cur.fetchall() or []
        return {str(r["subject"]): float(r["balance"] or 0) for r in rows if r.get("subject")}
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.error("user_subject_dcoins missing in get_user_subject_dcoins; returning empty map")
        else:
            logger.exception("get_user_subject_dcoins failed for user_id=%s", user_id)
        return {}
    finally:
        conn.close()


def get_student_ai_daily_requests(user_id: int, usage_date: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT requests_count FROM student_ai_chat_usage WHERE user_id=? AND usage_date=?",
            (user_id, usage_date),
        )
        row = cur.fetchone()
        return int((row or {}).get("requests_count") or 0)
    except Exception:
        return 0
    finally:
        conn.close()


def increment_student_ai_daily_requests(user_id: int, usage_date: str, prompt: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            INSERT INTO student_ai_chat_usage (user_id, usage_date, requests_count, last_prompt, updated_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, usage_date)
            DO UPDATE SET
                requests_count = student_ai_chat_usage.requests_count + 1,
                last_prompt = excluded.last_prompt,
                updated_at = CURRENT_TIMESTAMP
            ''',
            (user_id, usage_date, (prompt or "")[:1000]),
        )
        conn.commit()
        return get_student_ai_daily_requests(user_id, usage_date)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return get_student_ai_daily_requests(user_id, usage_date)
    finally:
        conn.close()


def count_available_daily_tests(subject: str, level: str, created_by: int | None = None) -> int:
    """Count unused daily-test items (not reserved by any student yet)."""
    subj = (subject or "").strip().title()
    lvl = (level or "").strip().upper()
    conn = get_conn()
    cur = conn.cursor()
    if created_by is None:
        cur.execute(
            "SELECT COUNT(*) as c FROM daily_tests_bank WHERE active=1 AND first_used_at IS NULL AND subject=? AND level=?",
            (subj, lvl),
        )
    else:
        cur.execute(
            "SELECT COUNT(*) as c FROM daily_tests_bank WHERE active=1 AND first_used_at IS NULL AND subject=? AND level=? AND created_by=?",
            (subj, lvl, created_by),
        )
    row = cur.fetchone()
    conn.close()
    return int(row["c"]) if row and row["c"] is not None else 0


def get_daily_tests_unused_stock_by_subject_level() -> list[dict]:
    """Unused daily_tests_bank rows grouped by subject and level (admin stock report)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT subject, level, COUNT(*) AS c
        FROM daily_tests_bank
        WHERE active = 1 AND first_used_at IS NULL
        GROUP BY subject, level
        ORDER BY subject ASC, level ASC
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_daily_tests_stock_by_teacher(teacher_id: int, subject: str) -> dict:
    """Return remaining daily tests count per level for a specific teacher (subject-scoped)."""
    subj = (subject or "").strip().title()
    levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'MIXED']
    stock = {lvl: 0 for lvl in levels}
    total = 0

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT level, COUNT(*) as c
        FROM daily_tests_bank
        WHERE active=1 AND first_used_at IS NULL AND subject=? AND created_by=?
        GROUP BY level
        ''',
        (subj, teacher_id),
    )
    rows = cur.fetchall()
    for r in rows:
        lvl = (r["level"] or "").upper()
        if lvl in stock:
            stock[lvl] = int(r["c"])
            total += stock[lvl]
        else:
            try:
                total += int(r["c"])
            except Exception:
                pass
    # Backward-compatibility: older rows might have created_by NULL,
    # so teacher stock would incorrectly show zeros. If so, fallback to global stock.
    if total == 0:
        try:
            cur.execute(
                '''
                SELECT level, COUNT(*) as c
                FROM daily_tests_bank
                WHERE active=1 AND first_used_at IS NULL AND subject=?
                GROUP BY level
                ''',
                (subj,),
            )
            rows2 = cur.fetchall()
            stock = {lvl: 0 for lvl in levels}
            total = 0
            for r in rows2:
                lvl = (r["level"] or "").upper()
                if lvl in stock:
                    stock[lvl] = int(r["c"])
                    total += stock[lvl]
                else:
                    try:
                        total += int(r["c"])
                    except Exception:
                        pass
        except Exception:
            pass
    conn.close()
    return {"subject": subj, "stock": stock, "total": total}


def get_daily_test_reminder_candidates(test_date: str, reminder_slot: int) -> list[dict]:
    """
    Return students who:
    - haven't completed a daily test for `test_date`
    - haven't received a reminder for `reminder_slot` yet
    - have access enabled (best-effort via `is_access_active` in Python)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT *
        FROM users u
        WHERE u.login_type=2
          AND COALESCE(u.blocked, 0)=0
          AND NOT EXISTS (
              SELECT 1
              FROM daily_test_attempts a
              WHERE a.user_id=u.id AND a.test_date=? AND a.status='completed'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM daily_test_notifications n
              WHERE n.user_id=u.id AND n.test_date=? AND n.reminder_slot=?
          )
        ''',
        (test_date, test_date, reminder_slot),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    # Filter by access expiration in Python (keeps SQL portable)
    return [r for r in rows if is_access_active(r)]


def mark_daily_test_notification_sent(user_id: int, test_date: str, reminder_slot: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            INSERT INTO daily_test_notifications (user_id, test_date, reminder_slot)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, test_date, reminder_slot) DO NOTHING
            ''',
            (user_id, test_date, reminder_slot),
        )
        inserted = (getattr(cur, "rowcount", 0) or 0) > 0
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def count_available_daily_tests_global() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT COUNT(*) as c
        FROM daily_tests_bank
        WHERE active=1 AND first_used_at IS NULL
        '''
    )
    row = cur.fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def get_teachers_with_daily_test_permission() -> list[dict]:
    """Teachers (login_type=3) allowed to upload daily tests."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT *
        FROM users
        WHERE login_type=3
          AND COALESCE(can_upload_daily_tests, 0)=1
          AND COALESCE(blocked, 0)=0
        '''
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def mark_daily_test_stock_alert(subject: str, level: str, threshold: int) -> bool:
    """Record that we notified `threshold` remaining tests (idempotent)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            INSERT INTO daily_test_stock_alerts (subject, level, threshold)
            VALUES (?, ?, ?)
            ON CONFLICT (subject, level, threshold) DO NOTHING
            ''',
            (subject, level, threshold),
        )
        inserted = (getattr(cur, "rowcount", 0) or 0) > 0
        conn.commit()
        return inserted
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def cleanup_expired_daily_tests(days: int = 4) -> int:
    """
    Delete used daily-test bank questions after `days` have passed since first use.
    Student attempt history stays intact because question details are stored in attempt_items.
    """
    if not _is_postgres_enabled():
        return 0

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        DELETE FROM daily_tests_bank
        WHERE first_used_at IS NOT NULL
          AND first_used_at < (CURRENT_TIMESTAMP - (? * INTERVAL '1 day'))
        ''',
        (days,),
    )
    deleted = getattr(cur, "rowcount", 0) or 0
    conn.commit()
    conn.close()
    return int(deleted)


def _pick_unused_daily_test_bank_rows(
    cur,
    subject: str,
    level: str,
    test_date: str,
    total_questions: int,
) -> list:
    """
    Pick unused (first_used_at IS NULL) rows from daily_tests_bank using the daily type plan.
    Returns list of row mappings (same shape as before).
    """
    subj = (subject or "").strip().title()
    lvl = (level or "").strip().upper()
    plan = ensure_daily_test_type_plan(
        subject=subj, test_date=test_date, total_questions=total_questions
    )
    type_counts = [
        ("grammar_rules", int(plan.get("grammar_rules_count", 0))),
        ("grammar_sentence", int(plan.get("grammar_sentence_count", 0))),
        ("find_mistake", int(plan.get("find_mistake_count", 0))),
        ("error_spotting", int(plan.get("error_spotting_count", 0))),
    ]

    bank_rows = []
    bank_ids: list[int] = []

    for qt, qt_need in type_counts:
        if qt_need <= 0:
            continue
        cur.execute(
            '''
            SELECT id, question, option_a, option_b, option_c, option_d, correct_option_index
            FROM daily_tests_bank
            WHERE active=1
              AND first_used_at IS NULL
              AND subject=? AND level=?
              AND question_type=?
            ORDER BY RANDOM()
            LIMIT ?
            ''',
            (subj, lvl, qt, qt_need),
        )
        rows = cur.fetchall()
        for r in rows:
            bid = int(r["id"])
            if bid in bank_ids:
                continue
            bank_rows.append(r)
            bank_ids.append(bid)
            if len(bank_rows) >= total_questions:
                break
        if len(bank_rows) >= total_questions:
            break

    missing = total_questions - len(bank_rows)
    if missing > 0:
        try:
            if bank_ids:
                placeholders = ",".join(["?"] * len(bank_ids))
                q_any = f'''
                    SELECT id, question, option_a, option_b, option_c, option_d, correct_option_index
                    FROM daily_tests_bank
                    WHERE active=1 AND first_used_at IS NULL
                      AND subject=? AND level=?
                      AND id NOT IN ({placeholders})
                    ORDER BY RANDOM()
                    LIMIT ?
                '''
                cur.execute(q_any, tuple([subj, lvl] + bank_ids + [missing]))
            else:
                cur.execute(
                    '''
                    SELECT id, question, option_a, option_b, option_c, option_d, correct_option_index
                    FROM daily_tests_bank
                    WHERE active=1 AND first_used_at IS NULL
                      AND subject=? AND level=?
                    ORDER BY RANDOM()
                    LIMIT ?
                    ''',
                    (subj, lvl, missing),
                )
            rows2 = cur.fetchall()
            for r in rows2:
                bid = int(r["id"])
                if bid in bank_ids:
                    continue
                bank_rows.append(r)
                bank_ids.append(bid)
                if len(bank_rows) >= total_questions:
                    break
        except Exception:
            pass

    return bank_rows


def _ordered_daily_test_bank_rows(cur, bank_ids: list[int]) -> list:
    """Load bank rows in the same order as bank_ids; all must exist and be active."""
    if not bank_ids:
        return []
    placeholders = ",".join(["?"] * len(bank_ids))
    cur.execute(
        f'''
        SELECT id, question, option_a, option_b, option_c, option_d, correct_option_index
        FROM daily_tests_bank
        WHERE active=1 AND id IN ({placeholders})
        ''',
        tuple(bank_ids),
    )
    by_id = {int(r["id"]): r for r in cur.fetchall()}
    out = []
    for bid in bank_ids:
        r = by_id.get(int(bid))
        if r is None:
            return []
        out.append(r)
    return out


def ensure_daily_test_attempt_and_items(
    user_id: int,
    subject: str,
    level: str,
    test_date: str,
    *,
    total_questions: int = 10,
) -> tuple[int, str]:
    """
    Ensure the daily test attempt for (user_id, test_date) exists,
    and the daily_test_attempt_items rows are created/reserved.

    On PostgreSQL, all students share the same question IDs for (test_date, subject, level).

    Returns: (attempt_id, status)
    """
    import json

    from auth import level_for_daily_tests_bank

    subj = (subject or "").strip().title()
    lvl = level_for_daily_tests_bank(subj, level)

    with DB_WRITE_LOCK:
        # Some DBs may miss `daily_test_day_question_sets` until the first daily flow runs.
        # Guard the schema here to prevent "relation ... does not exist" crashes.
        ensure_daily_tests_schema()
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, status FROM daily_test_attempts WHERE user_id=? AND test_date=? AND subject=?",
            (user_id, test_date, subj),
        )
        row = cur.fetchone()
        if row:
            attempt_id = int(row["id"])
            status = row["status"]
        else:
            cur.execute(
                '''
                INSERT INTO daily_test_attempts (user_id, subject, level, test_date, total_questions)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                ''',
                (user_id, subj, lvl, test_date, total_questions),
            )
            attempt_id = int(cur.fetchone()["id"])
            status = "in_progress"

        cur.execute(
            "SELECT COUNT(*) as c FROM daily_test_attempt_items WHERE attempt_id=?",
            (attempt_id,),
        )
        items_count = cur.fetchone()["c"] or 0
        if items_count >= total_questions:
            conn.close()
            return attempt_id, status

        bank_rows = []
        bank_ids: list[int] = []

        if _is_postgres_enabled():
            try:
                cur.execute(
                    """
                    SELECT bank_ids_json FROM daily_test_day_question_sets
                    WHERE test_date=? AND subject=? AND level=?
                    """,
                    (test_date, subj, lvl),
                )
                day_row = cur.fetchone()
            except Exception as e:
                # Extra safety: if shared day-set table is still missing or migration failed,
                # behave as if there is no precomputed row and let the allocation branch below
                # create both the table row and the question set instead of crashing.
                msg = str(e)
                if "daily_test_day_question_sets" in msg and "does not exist" in msg.lower():
                    # PostgreSQL transaction is aborted after failed statement.
                    # Reset tx state so later queries (pick/insert) can proceed.
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cur = conn.cursor()
                    day_row = None
                else:
                    conn.close()
                    raise

            if day_row and day_row.get("bank_ids_json"):
                try:
                    bank_ids = [int(x) for x in json.loads(day_row["bank_ids_json"])]
                except Exception:
                    bank_ids = []
                if bank_ids:
                    bank_rows = _ordered_daily_test_bank_rows(cur, bank_ids)
                    if len(bank_rows) != len(bank_ids):
                        conn.close()
                        raise ValueError(
                            "Daily test day set is inconsistent with bank (missing or inactive questions). "
                            "Ask admin to check daily_tests_bank."
                        )
                    bank_ids = [int(r["id"]) for r in bank_rows]
                    if len(bank_rows) > total_questions:
                        bank_rows = bank_rows[:total_questions]
                        bank_ids = [int(r["id"]) for r in bank_rows]

            if not bank_rows:
                for _attempt in range(4):
                    picked = _pick_unused_daily_test_bank_rows(
                        cur, subj, lvl, test_date, total_questions
                    )
                    if len(picked) < total_questions:
                        conn.close()
                        raise ValueError(
                            f"Not enough daily tests in bank. Need {total_questions}, have {len(picked)}."
                        )
                    bank_ids_new = [int(r["id"]) for r in picked]
                    payload = json.dumps(bank_ids_new, ensure_ascii=False)
                    try:
                        cur.execute(
                            """
                            INSERT INTO daily_test_day_question_sets
                                (test_date, subject, level, total_questions, bank_ids_json)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (test_date, subject, level) DO NOTHING
                            RETURNING id
                            """,
                            (test_date, subj, lvl, total_questions, payload),
                        )
                    except Exception as e:
                        msg = str(e).lower()
                        if "daily_test_day_question_sets" in msg and "does not exist" in msg:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                            # Recreate missing schema and retry once.
                            ensure_daily_tests_schema()
                            cur = conn.cursor()
                            cur.execute(
                                """
                                INSERT INTO daily_test_day_question_sets
                                    (test_date, subject, level, total_questions, bank_ids_json)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT (test_date, subject, level) DO NOTHING
                                RETURNING id
                                """,
                                (test_date, subj, lvl, total_questions, payload),
                            )
                        else:
                            conn.close()
                            raise
                    ins = cur.fetchone()
                    if ins:
                        ph = ",".join(["?"] * len(bank_ids_new))
                        cur.execute(
                            f'''
                            UPDATE daily_tests_bank
                            SET first_used_at=CURRENT_TIMESTAMP
                            WHERE id IN ({ph})
                            ''',
                            tuple(bank_ids_new),
                        )
                        bank_rows = picked
                        bank_ids = bank_ids_new
                        break
                    cur.execute(
                        """
                        SELECT bank_ids_json FROM daily_test_day_question_sets
                        WHERE test_date=? AND subject=? AND level=?
                        """,
                        (test_date, subj, lvl),
                    )
                    dr = cur.fetchone()
                    if dr and dr.get("bank_ids_json"):
                        try:
                            bank_ids = [int(x) for x in json.loads(dr["bank_ids_json"])]
                        except Exception:
                            bank_ids = []
                        if bank_ids:
                            bank_rows = _ordered_daily_test_bank_rows(cur, bank_ids)
                            if len(bank_rows) == len(bank_ids):
                                if len(bank_rows) > total_questions:
                                    bank_rows = bank_rows[:total_questions]
                                    bank_ids = [int(r["id"]) for r in bank_rows]
                                break
                            bank_rows = []
                            bank_ids = []
                else:
                    conn.close()
                    raise ValueError(
                        "Could not allocate shared daily test set (concurrency). Try again."
                    )
        else:
            bank_rows = _pick_unused_daily_test_bank_rows(
                cur, subj, lvl, test_date, total_questions
            )
            if len(bank_rows) < total_questions:
                conn.close()
                raise ValueError(
                    f"Not enough daily tests in bank. Need {total_questions}, have {len(bank_rows)}."
                )
            bank_ids = [int(r["id"]) for r in bank_rows]
            placeholders = ",".join(["?"] * len(bank_ids))
            cur.execute(
                f'''
                UPDATE daily_tests_bank
                SET first_used_at=CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                ''',
                tuple(bank_ids),
            )

        # Insert usage tracking per-user (no-repeat safety + audit)
        usage_rows = [(user_id, bid) for bid in bank_ids]
        try:
            cur.executemany(
                '''
                INSERT INTO daily_test_usage (user_id, bank_test_id)
                VALUES (?, ?)
                ON CONFLICT (user_id, bank_test_id) DO NOTHING
                ''',
                usage_rows,
            )
        except Exception:
            pass

        items = []
        for idx, r in enumerate(bank_rows, start=1):
            options = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
            options_json = json.dumps(options, ensure_ascii=False)
            items.append(
                (
                    attempt_id,
                    int(r["id"]),
                    idx,
                    r["question"],
                    options_json,
                )
            )

        cur.execute("DELETE FROM daily_test_attempt_items WHERE attempt_id=?", (attempt_id,))
        cur.executemany(
            '''
            INSERT INTO daily_test_attempt_items
            (attempt_id, bank_test_id, question_index, question, options_json)
            VALUES (?, ?, ?, ?, ?)
            ''',
            items,
        )

        cur.execute(
            "UPDATE daily_test_attempts SET status='in_progress' WHERE id=?",
            (attempt_id,),
        )

        conn.commit()
        conn.close()
        return attempt_id, "in_progress"


def get_daily_test_attempt_items(attempt_id: int) -> list[dict]:
    import json

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT
            iti.id as attempt_item_id,
            iti.question_index,
            iti.question,
            iti.options_json,
            iti.selected_option,
            iti.is_correct,
            iti.answered_at,
            iti.timed_out,
            iti.bank_test_id,
            dtb.correct_option_index
        FROM daily_test_attempt_items iti
        JOIN daily_tests_bank dtb ON dtb.id = iti.bank_test_id
        WHERE iti.attempt_id=?
        ORDER BY iti.question_index
        ''',
        (attempt_id,),
    )
    rows = cur.fetchall()
    conn.close()
    # Keep options_json as-is; student bot will parse, but we normalize selected fields.
    return [dict(r) for r in rows]


def mark_daily_test_question_answered(
    attempt_id: int,
    question_index: int,
    selected_option: str,
    is_correct: bool,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        UPDATE daily_test_attempt_items
        SET selected_option=?, is_correct=?, answered_at=CURRENT_TIMESTAMP, timed_out=0
        WHERE attempt_id=? AND question_index=?
        ''',
        (selected_option, 1 if is_correct else 0, attempt_id, question_index),
    )
    conn.commit()
    conn.close()


def mark_daily_test_question_timed_out(attempt_id: int, question_index: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        UPDATE daily_test_attempt_items
        SET timed_out=1
        WHERE attempt_id=? AND question_index=? AND selected_option IS NULL
        ''',
        (attempt_id, question_index),
    )
    conn.commit()
    conn.close()


def finish_daily_test_attempt(
    attempt_id: int,
    correct: int,
    wrong: int,
    unanswered: int,
    net_dcoins: float,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        UPDATE daily_test_attempts
        SET
            finished_at=CURRENT_TIMESTAMP,
            status='completed',
            correct=?, wrong=?, unanswered=?,
            net_dcoins=?,
            current_question_index=?
        WHERE id=?
        ''',
        (correct, wrong, unanswered, float(net_dcoins), correct + wrong + unanswered, attempt_id),
    )
    conn.commit()
    conn.close()


def get_daily_test_attempt_history(user_id: int, limit: int = 14) -> list[dict]:
    """Daily tests attempt history for a single student (most recent first)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT
            test_date,
            started_at,
            finished_at,
            status,
            total_questions,
            correct,
            wrong,
            unanswered,
            net_dcoins
        FROM daily_test_attempts
        WHERE user_id=?
        ORDER BY test_date DESC
        LIMIT ?
        ''',
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_test_history_global(days: int = 14) -> list[dict]:
    """Daily tests history aggregated globally (most recent days first)."""
    tz = pytz.timezone("Asia/Tashkent")
    from datetime import timedelta
    start_date = (datetime.now(tz).date() - timedelta(days=days)).isoformat()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT
            test_date,
            COUNT(*) as completed_attempts,
            COALESCE(SUM(correct),0) as correct_total,
            COALESCE(SUM(wrong),0) as wrong_total,
            COALESCE(SUM(unanswered),0) as unanswered_total,
            COALESCE(AVG(net_dcoins),0) as avg_net_dcoins
        FROM daily_test_attempts
        WHERE status='completed'
          AND test_date >= ?
        GROUP BY test_date
        ORDER BY test_date DESC
        LIMIT ?
        ''',
        (start_date, days),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_test_history_for_teacher(teacher_id: int, days: int = 14) -> list[dict]:
    """
    Daily tests history aggregated for a teacher's students.
    Teacher scope = all students from all groups created/owned by this teacher.
    """
    tz = pytz.timezone("Asia/Tashkent")
    from datetime import timedelta
    start_date = (datetime.now(tz).date() - timedelta(days=days)).isoformat()

    groups = get_groups_by_teacher(teacher_id) or []
    user_ids: set[int] = set()
    for g in groups:
        for u in get_group_users(g["id"]):
            if u.get("login_type") in (1, 2):
                user_ids.add(u["id"])

    if not user_ids:
        return []

    placeholders = ",".join(["?"] * len(user_ids))
    params: list[Any] = [start_date, *list(user_ids), days]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f'''
        SELECT
            test_date,
            COUNT(*) as completed_attempts,
            COALESCE(SUM(correct),0) as correct_total,
            COALESCE(SUM(wrong),0) as wrong_total,
            COALESCE(SUM(unanswered),0) as unanswered_total,
            COALESCE(AVG(net_dcoins),0) as avg_net_dcoins
        FROM daily_test_attempts
        WHERE status='completed'
          AND test_date >= ?
          AND user_id IN ({placeholders})
        GROUP BY test_date
        ORDER BY test_date DESC
        LIMIT ?
        ''',
        tuple(params),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                dcoin_change DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subject TEXT,
                change_type TEXT,
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
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                feedback_text TEXT NOT NULL,
                is_anonymous INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                test_type TEXT NOT NULL,
                topic_id TEXT,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        logger.info("Migrasiya: test_history table created")
    except Exception:
        pass

    # test_history schema alignment for old DBs
    for col, ddl in (
        ("topic_id", "ALTER TABLE test_history ADD COLUMN topic_id TEXT"),
        ("correct_count", "ALTER TABLE test_history ADD COLUMN correct_count INTEGER DEFAULT 0"),
        ("wrong_count", "ALTER TABLE test_history ADD COLUMN wrong_count INTEGER DEFAULT 0"),
        ("skipped_count", "ALTER TABLE test_history ADD COLUMN skipped_count INTEGER DEFAULT 0"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: test_history.{col} ustuni qo'shildi")
        except Exception:
            # psycopg: after an error, the connection becomes "aborted" until rollback.
            # Do rollback + refresh cursor so remaining ALTER TABLE statements can continue.
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                cur = conn.cursor()
            except Exception:
                pass
            continue

    # Backfill from legacy column names if present and new values are empty.
    try:
        cur.execute(
            """
            UPDATE test_history
            SET correct_count = COALESCE(correct_count, 0) + COALESCE(correct_answers, 0)
            WHERE COALESCE(correct_answers, 0) <> 0
            """
        )
    except Exception:
        pass
    try:
        cur.execute(
            """
            UPDATE test_history
            SET wrong_count = COALESCE(wrong_count, 0) + COALESCE(wrong_answers, 0)
            WHERE COALESCE(wrong_answers, 0) <> 0
            """
        )
    except Exception:
        pass
    try:
        cur.execute(
            """
            UPDATE test_history
            SET skipped_count = COALESCE(skipped_count, 0) + COALESCE(skipped_answers, 0)
            WHERE COALESCE(skipped_answers, 0) <> 0
            """
        )
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

    # owner_admin_id columns (limited admins only see/manage their own students/groups)
    for col, ddl in (
        ("owner_admin_id", "ALTER TABLE users ADD COLUMN owner_admin_id INTEGER"),
        ("owner_admin_id", "ALTER TABLE groups ADD COLUMN owner_admin_id INTEGER"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: {ddl.split(' ')[2]}.{col} ustuni qo'shildi")
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
        id BIGSERIAL PRIMARY KEY,
        group_id BIGINT NOT NULL,
        date TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'open',
        opened_by TEXT,
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        notified_admin INTEGER DEFAULT 0,
        notified_teacher INTEGER DEFAULT 0,
        UNIQUE(group_id, date),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')

    # overdue_penalty_log schema alignment for old DBs
    try:
        cur.execute('''
        CREATE TABLE IF NOT EXISTS overdue_penalty_log (
            user_id BIGINT NOT NULL,
            group_id BIGINT NOT NULL,
            ym TEXT NOT NULL,
            penalty_date TEXT NOT NULL
        )
        ''')
    except Exception:
        pass
    for col, ddl in (
        ("group_id", "ALTER TABLE overdue_penalty_log ADD COLUMN group_id BIGINT"),
        ("penalty_date", "ALTER TABLE overdue_penalty_log ADD COLUMN penalty_date TEXT"),
    ):
        try:
            cur.execute(ddl)
            logger.info(f"Migrasiya: overdue_penalty_log.{col} ustuni qo'shildi")
        except Exception:
            pass
    try:
        cur.execute(
            "UPDATE overdue_penalty_log SET penalty_date = COALESCE(penalty_date, CURRENT_DATE::text)"
        )
    except Exception:
        pass
    try:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_overdue_penalty_log_uniq ON overdue_penalty_log(user_id, group_id, ym, penalty_date)"
        )
    except Exception:
        pass

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

    # Store last attendance panel message ids so admin/teacher bots can sync edits.
    for col, ddl in (
        ("admin_panel_chat_id", "ALTER TABLE attendance_sessions ADD COLUMN admin_panel_chat_id INTEGER"),
        ("admin_panel_message_id", "ALTER TABLE attendance_sessions ADD COLUMN admin_panel_message_id INTEGER"),
        ("teacher_panel_chat_id", "ALTER TABLE attendance_sessions ADD COLUMN teacher_panel_chat_id INTEGER"),
        ("teacher_panel_message_id", "ALTER TABLE attendance_sessions ADD COLUMN teacher_panel_message_id INTEGER"),
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

    # bot runtime start timestamp (used to limit month navigation/scheduling)
    try:
        cur.execute('''
        CREATE TABLE IF NOT EXISTS bot_runtime_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            started_at TEXT NOT NULL
        )
        ''')
        cur.execute('''
        INSERT INTO bot_runtime_state (id, started_at)
        VALUES (1, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
        ''')
    except Exception:
        pass
    
    conn.commit()
    conn.close()


def ensure_monthly_payments_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS monthly_payments (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        ym TEXT NOT NULL, -- YYYY-MM
        group_id BIGINT,
        subject TEXT,
        paid INTEGER DEFAULT 0,
        paid_at TIMESTAMP,
        notified_days TEXT, -- comma-separated days e.g. "1,5,15"
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_monthly_payments_user_ym_group ON monthly_payments(user_id, ym, group_id)')
    # IMPORTANT:
    # We need per-group payment tracking, so UNIQUE(user_id, ym) must NOT exist.
    # Older migrations may have created it, causing IntegrityError on pay_set.
    try:
        cur.execute('DROP INDEX IF EXISTS ux_monthly_payments_user_ym')
    except Exception:
        pass
    conn.commit()
    conn.close()


def set_bot_started_at_now():
    """Update bot started_at timestamp on every bot startup."""
    ensure_bot_runtime_state_table()
    import pytz
    tz = pytz.timezone("Asia/Tashkent")
    now = datetime.now(tz)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE bot_runtime_state SET started_at=%s WHERE id=1", (now,))
    conn.commit()
    conn.close()


def ensure_bot_runtime_state_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bot_runtime_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            started_at TIMESTAMP NOT NULL
        )
    ''')
    cur.execute('''
        INSERT INTO bot_runtime_state (id, started_at)
        VALUES (1, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    ''')
    conn.commit()
    conn.close()


def get_bot_started_at() -> str | None:
    ensure_bot_runtime_state_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT started_at FROM bot_runtime_state WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row["started_at"] if row else None


def get_bot_start_ym() -> str:
    """
    Return bot started month (YYYY-MM) to limit payment month navigation and penalties.
    """
    started_at = get_bot_started_at()
    if not started_at:
        # Fallback to current Uzbekistan month
        tz = pytz.timezone("Asia/Tashkent")
        return datetime.now(tz).strftime("%Y-%m")
    # started_at format: YYYY-MM-DD HH:MM:SS
    return str(started_at)[:7]


def ensure_overdue_penalty_log_table():
    """Track daily -2 D'coin penalty for overdue payments (one row per user,group,ym,date)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('''
        CREATE TABLE IF NOT EXISTS overdue_penalty_log (
            user_id BIGINT NOT NULL,
            group_id BIGINT NOT NULL,
            ym TEXT NOT NULL,
            penalty_date TIMESTAMP NOT NULL,
            penalty_amount INTEGER NOT NULL DEFAULT -2,
            PRIMARY KEY (user_id, group_id, ym, penalty_date),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(group_id) REFERENCES groups(id)
        )
        ''')

        # If table exists from an older schema, it may miss columns used by payment.py.
        # Make this idempotent by adding missing columns only.
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='overdue_penalty_log' AND column_name='group_id'
                LIMIT 1
                """
            )
            has_group_id = cur.fetchone() is not None
            if not has_group_id:
                cur.execute("ALTER TABLE overdue_penalty_log ADD COLUMN group_id BIGINT")
        except Exception:
            conn.rollback()

        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='overdue_penalty_log' AND column_name='penalty_date'
                LIMIT 1
                """
            )
            has_penalty_date = cur.fetchone() is not None
            if not has_penalty_date:
                cur.execute("ALTER TABLE overdue_penalty_log ADD COLUMN penalty_date TIMESTAMP")
        except Exception:
            conn.rollback()

        # Ensure penalty_amount exists and has a safe default.
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='overdue_penalty_log' AND column_name='penalty_amount'
                LIMIT 1
                """
            )
            has_penalty_amount = cur.fetchone() is not None
            if not has_penalty_amount:
                cur.execute("ALTER TABLE overdue_penalty_log ADD COLUMN penalty_amount INTEGER NOT NULL DEFAULT -2")
            else:
                cur.execute("UPDATE overdue_penalty_log SET penalty_amount=-2 WHERE penalty_amount IS NULL")
                cur.execute("ALTER TABLE overdue_penalty_log ALTER COLUMN penalty_amount SET DEFAULT -2")
        except Exception:
            conn.rollback()

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_attendance_sessions_schema():
    """
    Ensure attendance_sessions has columns expected by attendance_manager.py.
    Particularly: closed_at.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='attendance_sessions' AND column_name='closed_at'
                LIMIT 1
                """
            )
            has_closed_at = cur.fetchone() is not None
            if not has_closed_at:
                cur.execute("ALTER TABLE attendance_sessions ADD COLUMN closed_at TIMESTAMP")
        except Exception:
            conn.rollback()
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_temporary_group_assignments_schema() -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS temporary_group_assignments (
                id BIGSERIAL PRIMARY KEY,
                group_id BIGINT NOT NULL,
                owner_teacher_id BIGINT NOT NULL,
                temp_teacher_id BIGINT NOT NULL,
                lesson_date TEXT NOT NULL,
                lesson_start TEXT,
                lesson_end TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TIMESTAMP
            )
            '''
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_admin_student_shares_schema() -> None:
    """Limited admins can share a student with another admin (full co-management until unshared)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS admin_student_shares (
                id BIGSERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                peer_admin_id BIGINT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_by_admin_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TIMESTAMP,
                UNIQUE(student_id, peer_admin_id)
            )
            '''
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def share_student_between_admins(
    student_id: int,
    peer_admin_id: int,
    created_by_admin_id: int,
) -> tuple[bool, str | None]:
    """
    Owner admin shares a student with peer_admin_id. Idempotent if already active.
    Returns (ok, error_key) where error_key is one of:
    not_found, not_student, peer_is_owner, only_owner_can_share
    """
    user = get_user_by_id(int(student_id))
    if not user:
        return False, "not_found"
    if user.get("login_type") not in (1, 2):
        return False, "not_student"
    owner = user.get("owner_admin_id")
    if owner is None:
        return False, "only_owner_can_share"
    if int(peer_admin_id) == int(owner):
        return False, "peer_is_owner"
    if int(created_by_admin_id) != int(owner) and int(created_by_admin_id) not in ADMIN_CHAT_IDS:
        return False, "only_owner_can_share"

    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                INSERT INTO admin_student_shares
                    (student_id, peer_admin_id, status, created_by_admin_id, created_at, cancelled_at)
                VALUES (%s, %s, 'active', %s, CURRENT_TIMESTAMP, NULL)
                ON CONFLICT (student_id, peer_admin_id) DO UPDATE SET
                    status = 'active',
                    created_by_admin_id = EXCLUDED.created_by_admin_id,
                    created_at = CURRENT_TIMESTAMP,
                    cancelled_at = NULL
                """,
                (int(student_id), int(peer_admin_id), int(created_by_admin_id)),
            )
        else:
            cur.execute(
                """
                INSERT INTO admin_student_shares
                    (student_id, peer_admin_id, status, created_by_admin_id, created_at, cancelled_at)
                VALUES (?, ?, 'active', ?, CURRENT_TIMESTAMP, NULL)
                ON CONFLICT(student_id, peer_admin_id) DO UPDATE SET
                    status = 'active',
                    created_by_admin_id = excluded.created_by_admin_id,
                    created_at = CURRENT_TIMESTAMP,
                    cancelled_at = NULL
                """,
                (int(student_id), int(peer_admin_id), int(created_by_admin_id)),
            )
        conn.commit()
        return True, None
    except Exception as e:
        logger.error("share_student_between_admins failed: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False, "db_error"
    finally:
        conn.close()


def unshare_student_between_admins(
    student_id: int,
    peer_admin_id: int,
    acting_admin_id: int,
) -> tuple[bool, str | None]:
    """
    Owner or peer cancels an active share.
    Returns (ok, error_key): not_found, not_student, not_authorized, not_shared, db_error
    """
    user = get_user_by_id(int(student_id))
    if not user:
        return False, "not_found"
    if user.get("login_type") not in (1, 2):
        return False, "not_student"
    owner = user.get("owner_admin_id")
    allowed_actors = {int(peer_admin_id)}
    if owner is not None:
        allowed_actors.add(int(owner))
    if int(acting_admin_id) not in ADMIN_CHAT_IDS and int(acting_admin_id) not in allowed_actors:
        return False, "not_authorized"

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id FROM admin_student_shares
            WHERE student_id = ? AND peer_admin_id = ? AND status = 'active'
            LIMIT 1
            """,
            (int(student_id), int(peer_admin_id)),
        )
        if not cur.fetchone():
            return False, "not_shared"
        cur.execute(
            """
            UPDATE admin_student_shares
            SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
            WHERE student_id = ? AND peer_admin_id = ? AND status = 'active'
            """,
            (int(student_id), int(peer_admin_id)),
        )
        conn.commit()
        return True, None
    except Exception as e:
        logger.error("unshare_student_between_admins failed: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False, "db_error"
    finally:
        conn.close()


def is_student_shared_with_admin(student_id: int, admin_id: int) -> bool:
    """True if this admin is an active peer (not the owner) for the student."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM admin_student_shares
            WHERE student_id = ? AND peer_admin_id = ? AND status = 'active'
            LIMIT 1
            """,
            (int(student_id), int(admin_id)),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def get_shared_student_ids_for_admin(admin_id: int) -> set[int]:
    """Student IDs this admin can manage as a peer (shared owner access)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT student_id FROM admin_student_shares
            WHERE peer_admin_id = ? AND status = 'active'
            """,
            (int(admin_id),),
        )
        rows = cur.fetchall()
        out: set[int] = set()
        for r in rows:
            if isinstance(r, dict):
                sid = r.get("student_id")
            else:
                sid = r[0]
            if sid is not None:
                out.add(int(sid))
        return out
    finally:
        conn.close()


def get_peer_admins_for_student_share(student_id: int) -> list[int]:
    """Active peer admin telegram IDs for notifications / UI."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT peer_admin_id FROM admin_student_shares
            WHERE student_id = ? AND status = 'active'
            ORDER BY peer_admin_id
            """,
            (int(student_id),),
        )
        rows = cur.fetchall()
        peers: list[int] = []
        for r in rows:
            if isinstance(r, dict):
                pid = r.get("peer_admin_id")
            else:
                pid = r[0]
            if pid is not None:
                peers.append(int(pid))
        return peers
    finally:
        conn.close()


def ensure_grammar_attempts_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS grammar_attempts (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        topic_id TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        last_attempt_at TIMESTAMP,
        UNIQUE(user_id, topic_id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # Postgres-only: legacy DBs may store `last_attempt_at` as TEXT.
    if _is_postgres_enabled():
        try:
            cur.execute("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name='grammar_attempts' AND column_name='last_attempt_at'
            """)
            row = cur.fetchone()
            data_type = (row or {}).get('data_type') if row else None
            if data_type and str(data_type).lower() in ('text', 'character varying', 'character', 'varchar', 'nvarchar'):
                logger.warning(
                    "Legacy schema detected: grammar_attempts.last_attempt_at is %s, converting to TIMESTAMP",
                    data_type,
                )
                cur.execute("""
                    ALTER TABLE grammar_attempts
                    ALTER COLUMN last_attempt_at TYPE TIMESTAMP
                    USING (
                        CASE
                          WHEN last_attempt_at IS NULL THEN NULL
                          WHEN last_attempt_at::text = '' THEN NULL
                          WHEN last_attempt_at::text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}' THEN last_attempt_at::timestamp
                          ELSE NULL
                        END
                    )
                """)
        except Exception as e:
            # Don't crash the bot on schema migration errors;
            # we also handle TEXT in queries via defensive casting.
            conn.rollback()
            logger.error("Failed to migrate grammar_attempts.last_attempt_at type: %s", e)
    conn.commit()
    conn.close()


def ensure_daily_tests_schema():
    """
    Create schema needed for teacher-uploaded daily tests and student attempts.
    Runs on startup so it works for existing DBs too.
    """
    if not _is_postgres_enabled():
        # Daily tests feature is PostgreSQL-only in this implementation.
        return

    conn = get_conn()
    cur = conn.cursor()

    # Teacher permission flag
    try:
        cur.execute("ALTER TABLE users ADD COLUMN can_upload_daily_tests INTEGER DEFAULT 0")
    except Exception:
        # psycopg: after an error, the transaction is aborted until rollback.
        conn.rollback()
        cur = conn.cursor()

    # AI generator permission (teacher -> can generate vocab/daily tests)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN can_generate_ai INTEGER DEFAULT 0")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        cur = conn.cursor()

    # Daily test schema statements.
    # IMPORTANT: With psycopg, if any previous statement failed in the same transaction,
    # the connection becomes "aborted" until rollback. Therefore, we wrap each block.
    try:
        # Daily test question bank (uploaded by teachers)
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_tests_bank (
            id BIGSERIAL PRIMARY KEY,
            created_by BIGINT,
            subject TEXT NOT NULL,
            level TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option_index INTEGER NOT NULL CHECK (correct_option_index BETWEEN 1 AND 4),
            question_type TEXT,
            active INTEGER DEFAULT 1,
            first_used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # If daily_tests_bank already existed (created without question_type),
        # add the missing column.
        try:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='daily_tests_bank' AND column_name='question_type'
                LIMIT 1
                """
            )
            has_qt = cur.fetchone() is not None
            if not has_qt:
                cur.execute("ALTER TABLE daily_tests_bank ADD COLUMN question_type TEXT")
        except Exception:
            pass

        # One attempt per user per day
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_attempts (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            subject TEXT NOT NULL,
            level TEXT NOT NULL,
            test_date DATE NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'in_progress',
            total_questions INTEGER NOT NULL DEFAULT 20,
            correct INTEGER NOT NULL DEFAULT 0,
            wrong INTEGER NOT NULL DEFAULT 0,
            unanswered INTEGER NOT NULL DEFAULT 0,
            net_dcoins DOUBLE PRECISION NOT NULL DEFAULT 0,
            current_question_index INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, test_date, subject)
        )
        ''')

        # Postgres: if this table already exists with UNIQUE(user_id, test_date),
        # drop that constraint and replace with UNIQUE(user_id, test_date, subject).
        if _is_postgres_enabled():
            try:
                cur.execute("""
                    SELECT tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                      ON tc.constraint_name = ccu.constraint_name
                     AND tc.table_schema = ccu.table_schema
                    WHERE tc.table_name='daily_test_attempts'
                      AND tc.constraint_type='UNIQUE'
                    GROUP BY tc.constraint_name
                    HAVING
                      SUM(CASE WHEN ccu.column_name='user_id' THEN 1 ELSE 0 END) = 1
                      AND SUM(CASE WHEN ccu.column_name='test_date' THEN 1 ELSE 0 END) = 1
                      AND SUM(CASE WHEN ccu.column_name='subject' THEN 1 ELSE 0 END) = 0
                      AND COUNT(*) = 2
                """)
                legacy_constraints = [r["constraint_name"] for r in cur.fetchall()]
                for cname in legacy_constraints:
                    cur.execute(f"ALTER TABLE daily_test_attempts DROP CONSTRAINT IF EXISTS {cname}")
            except Exception:
                conn.rollback()

            try:
                cur.execute(
                    "ALTER TABLE daily_test_attempts ADD CONSTRAINT ux_daily_test_attempts_user_date_subject UNIQUE(user_id, test_date, subject)"
                )
            except Exception:
                # If it already exists or schema differs, ignore.
                pass

        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_attempt_items (
            id BIGSERIAL PRIMARY KEY,
            attempt_id BIGINT NOT NULL,
            bank_test_id BIGINT NOT NULL,
            question_index INTEGER NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT,
            selected_option TEXT,
            is_correct INTEGER NOT NULL DEFAULT 0,
            answered_at TIMESTAMP,
            timed_out INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(attempt_id, question_index),
            FOREIGN KEY(attempt_id) REFERENCES daily_test_attempts(id) ON DELETE CASCADE
        )
        ''')

        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_notifications (
            user_id BIGINT NOT NULL,
            test_date DATE NOT NULL,
            reminder_slot INTEGER NOT NULL, -- 0=09:00 initial, 1=14:00, 2=19:00
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, test_date, reminder_slot)
        )
        ''')

        # Per-user no-repeat tracking for selected bank tests
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_usage (
            user_id BIGINT NOT NULL,
            bank_test_id BIGINT NOT NULL,
            first_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cleaned_at TIMESTAMP,
            UNIQUE(user_id, bank_test_id),
            FOREIGN KEY(bank_test_id) REFERENCES daily_tests_bank(id) ON DELETE CASCADE
        )
        ''')

        # Stock alert tracking
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_stock_alerts (
            id BIGSERIAL PRIMARY KEY,
            subject TEXT,
            level TEXT,
            threshold INTEGER NOT NULL,
            notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(subject, level, threshold)
        )
        ''')

        # One random question set per calendar day + subject + level (shared by all students).
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_day_question_sets (
            id BIGSERIAL PRIMARY KEY,
            test_date DATE NOT NULL,
            subject TEXT NOT NULL,
            level TEXT NOT NULL,
            total_questions INTEGER NOT NULL,
            bank_ids_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(test_date, subject, level)
        )
        ''')
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_test_day_sets_lookup
                ON daily_test_day_question_sets (test_date, subject, level)
                """
            )
        except Exception:
            pass
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_daily_test_day_sets_date
                ON daily_test_day_question_sets (test_date)
                """
            )
        except Exception:
            pass

        # Daily question type plan for deterministic mix per date.
        cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_test_type_plans (
            test_date DATE NOT NULL,
            subject TEXT NOT NULL,
            grammar_rules_count INTEGER NOT NULL,
            grammar_sentence_count INTEGER NOT NULL,
            find_mistake_count INTEGER NOT NULL,
            error_spotting_count INTEGER NOT NULL,
            total_questions INTEGER NOT NULL DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (test_date, subject)
        )
        ''')
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_arena_group_schema() -> None:
    """
    Group Arena (teacher-generated quiz) storage.
    Uses `daily_tests_bank` rows as the question source and stores selected bank ids per session.
    """
    if not _is_postgres_enabled():
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_group_sessions (
                id BIGSERIAL PRIMARY KEY,
                group_id BIGINT NOT NULL,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                question_count INTEGER NOT NULL,
                bank_ids_json TEXT NOT NULL,
                created_by_teacher_id BIGINT,
                expected_players INTEGER NOT NULL DEFAULT 0,
                rewards_distributed INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ready', -- ready | sent | completed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            '''
        )

        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_group_session_attempts (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                correct INTEGER NOT NULL DEFAULT 0,
                wrong INTEGER NOT NULL DEFAULT 0,
                unanswered INTEGER NOT NULL DEFAULT 0,
                net_dcoins DOUBLE PRECISION NOT NULL DEFAULT 0,
                UNIQUE(user_id, session_id)
            )
            '''
        )
        conn.commit()
        # Migration for older DBs: add `is_unanswered` if table existed without the column.
        try:
            _ensure_arena_run_answers_is_unanswered_column()
        except Exception:
            pass
    finally:
        conn.close()

    # Backward compatible: add columns if table exists without them.
    if _is_postgres_enabled():
        conn2 = get_conn()
        cur2 = conn2.cursor()
        try:
            cur2.execute("ALTER TABLE arena_group_sessions ADD COLUMN IF NOT EXISTS expected_players INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            cur2.execute("ALTER TABLE arena_group_sessions ADD COLUMN IF NOT EXISTS rewards_distributed INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            cur2.execute("ALTER TABLE arena_group_sessions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP")
        except Exception:
            pass
        conn2.commit()
        conn2.close()


def ensure_arena_group_extended_schema() -> None:
    """Per-question answers, teacher live UI columns, promote-to-daily marker, refresh queue."""
    if not _is_postgres_enabled():
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS arena_group_session_answers (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                question_order INTEGER NOT NULL,
                bank_question_id BIGINT NOT NULL,
                selected_option_index INTEGER,
                is_correct INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, user_id, question_order)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS arena_group_teacher_refresh_queue (
                session_id BIGINT PRIMARY KEY,
                enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            "ALTER TABLE arena_group_sessions ADD COLUMN IF NOT EXISTS teacher_chat_id BIGINT"
        )
        cur.execute(
            "ALTER TABLE arena_group_sessions ADD COLUMN IF NOT EXISTS teacher_status_message_id BIGINT"
        )
        cur.execute(
            "ALTER TABLE arena_questions_bank ADD COLUMN IF NOT EXISTS promoted_to_daily_at TIMESTAMP"
        )
        conn.commit()
    except Exception:
        logger.exception("ensure_arena_group_extended_schema failed")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def insert_arena_group_session_answer(
    *,
    session_id: int,
    user_id: int,
    question_order: int,
    bank_question_id: int,
    selected_option_index: int | None,
    is_correct: bool,
) -> None:
    if not _is_postgres_enabled():
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_group_session_answers
                (session_id, user_id, question_order, bank_question_id, selected_option_index, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (session_id, user_id, question_order)
            DO UPDATE SET
                bank_question_id = excluded.bank_question_id,
                selected_option_index = excluded.selected_option_index,
                is_correct = excluded.is_correct
            """,
            (
                int(session_id),
                int(user_id),
                int(question_order),
                int(bank_question_id),
                selected_option_index,
                1 if is_correct else 0,
            ),
        )
        conn.commit()
        # Migration for older DBs: add `is_unanswered` if table existed without the column.
        try:
            _ensure_arena_run_answers_is_unanswered_column()
        except Exception:
            pass
    finally:
        conn.close()


def enqueue_arena_group_teacher_refresh(session_id: int) -> None:
    if not _is_postgres_enabled():
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_group_teacher_refresh_queue (session_id)
            VALUES (?)
            ON CONFLICT (session_id) DO UPDATE SET enqueued_at = CURRENT_TIMESTAMP
            """,
            (int(session_id),),
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def pop_arena_group_teacher_refresh_session() -> int | None:
    if not _is_postgres_enabled():
        return None
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT session_id FROM arena_group_teacher_refresh_queue
            ORDER BY enqueued_at ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        sid = int(row["session_id"])
        cur.execute(
            "DELETE FROM arena_group_teacher_refresh_queue WHERE session_id=?",
            (sid,),
        )
        conn.commit()
        return sid
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def set_arena_group_session_teacher_message(
    session_id: int, teacher_chat_id: int, message_id: int
) -> None:
    if not _is_postgres_enabled():
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE arena_group_sessions
            SET teacher_chat_id=?, teacher_status_message_id=?
            WHERE id=?
            """,
            (int(teacher_chat_id), int(message_id), int(session_id)),
        )
        conn.commit()
    finally:
        conn.close()


def user_is_present_for_group_on_date(user_id: int, group_id: int, date_str: str) -> bool:
    present = get_present_students_for_group_date(group_id, date_str)
    return any(int(u.get("id") or 0) == int(user_id) for u in present)


def get_group_arena_teacher_snapshot(session_id: int) -> dict | None:
    """Raw data for teacher live / export UI."""
    sess = get_arena_group_session(session_id)
    if not sess:
        return None
    gid = int(sess["group_id"])
    tz = pytz.timezone("Asia/Tashkent")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    present = get_present_students_for_group_date(gid, today)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM arena_group_session_attempts
            WHERE session_id=?
            ORDER BY user_id
            """,
            (int(session_id),),
        )
        attempts = [dict(r) for r in cur.fetchall() or []]
    finally:
        conn.close()
    return {"session": sess, "present": present, "attempts": attempts, "date_str": today}


def list_arena_group_session_answers_for_export(session_id: int) -> list[dict]:
    if not _is_postgres_enabled():
        return []
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT a.*, u.first_name, u.last_name
            FROM arena_group_session_answers a
            JOIN users u ON u.id = a.user_id
            WHERE a.session_id=?
            ORDER BY a.user_id, a.question_order
            """,
            (int(session_id),),
        )
        return [dict(r) for r in cur.fetchall() or []]
    finally:
        conn.close()


def promote_expired_arena_questions_to_daily() -> int:
    """
    Promote Group Arena runtime tmp questions into `daily_tests_bank` after 3 hours retention.
    (Replaces the legacy 24h promotion from `arena_questions_bank`.)
    """
    if not _is_postgres_enabled():
        return 0
    ensure_arena_group_schema()
    ensure_arena_questions_tmp_schema()
    ensure_daily_tests_schema()
    conn = get_conn()
    cur = conn.cursor()
    promoted_rows = 0
    try:
        cur.execute(
            """
            SELECT DISTINCT t.session_id, s.completed_at
            FROM arena_group_questions_tmp t
            JOIN arena_group_sessions s ON s.id = t.session_id
            WHERE s.status='completed'
              AND s.completed_at <= (CURRENT_TIMESTAMP - INTERVAL '3 hours')
              AND t.promoted_at IS NULL
            ORDER BY s.completed_at ASC
            LIMIT 20
            """
        )
        session_ids = [int(r["session_id"]) for r in cur.fetchall() or []]

        import json

        for sid in session_ids:
            # Load session subject/level for daily_tests_bank insertion.
            cur.execute(
                """
                SELECT subject, level
                FROM arena_group_sessions
                WHERE id=?
                """,
                (int(sid),),
            )
            sess_row = cur.fetchone() or {}
            subject = str(sess_row.get("subject") or "English").strip().title()
            base_level = str(sess_row.get("level") or "B2").strip().upper() or "B2"

            cur.execute(
                """
                SELECT q_index, payload_json
                FROM arena_group_questions_tmp
                WHERE session_id=? AND promoted_at IS NULL
                ORDER BY q_index ASC
                """,
                (int(sid),),
            )
            qrows = cur.fetchall() or []
            if not qrows:
                continue

            for qr in qrows:
                try:
                    payload = json.loads(qr["payload_json"] or "{}")
                except Exception:
                    payload = {}

                created_by = int(payload.get("created_by") or 0)
                level = str(payload.get("level") or base_level).strip().upper() or base_level
                question = str(payload.get("question") or "").strip()

                option_a = str(payload.get("option_a") or "").strip()
                option_b = str(payload.get("option_b") or "").strip()
                option_c = str(payload.get("option_c") or "").strip()
                option_d = str(payload.get("option_d") or "").strip()

                correct_option_index = int(payload.get("correct_option_index") or 1)
                correct_option_index = int(max(1, min(4, correct_option_index)))

                question_type = payload.get("question_type")

                if not question:
                    continue

                cur.execute(
                    """
                    INSERT INTO daily_tests_bank
                        (created_by, subject, level, question,
                         option_a, option_b, option_c, option_d,
                         correct_option_index, question_type, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        created_by,
                        subject,
                        level,
                        question,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        correct_option_index,
                        question_type,
                    ),
                )
                promoted_rows += 1

            # Cleanup tmp snapshot after successful promotion.
            cur.execute(
                """
                DELETE FROM arena_group_questions_tmp
                WHERE session_id=? AND promoted_at IS NULL
                """,
                (int(sid),),
            )
        conn.commit()
    except Exception:
        logger.exception("promote_expired_arena_questions_to_daily failed")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()
    return promoted_rows


def promote_expired_daily_arena_questions_to_daily() -> int:
    """
    Copy Daily/Boss Arena runtime tmp questions into `daily_tests_bank` after 3 hours retention.

    For each eligible finished daily run:
      - read all questions from `arena_*_questions_tmp.payload_json`
      - insert into `daily_tests_bank`
      - mark `arena_scheduled_runs.questions_promoted=1`
      - cleanup tmp question rows for that run
    """
    import json

    if not _is_postgres_enabled():
        return 0
    ensure_arena_extras_schema()
    ensure_arena_questions_tmp_schema()
    ensure_daily_tests_schema()

    # If older DBs exist without the column, auto-migrate before SELECT.
    try:
        _ensure_arena_scheduled_runs_questions_promoted_column()
    except Exception:
        pass

    conn = get_conn()
    cur = conn.cursor()
    promoted_runs = 0
    try:
        # Limit how long the promotion scheduler can hold locks.
        try:
            cur.execute("SET LOCAL statement_timeout = '10s'")
        except Exception:
            pass

        select_sql = """
            SELECT id, subject, run_kind
            FROM arena_scheduled_runs
            WHERE run_kind IN ('daily','boss')
              AND status='finished'
              AND questions_promoted=0
              AND finished_at <= (CURRENT_TIMESTAMP - INTERVAL '3 hours')
            ORDER BY finished_at ASC
            LIMIT 20
        """
        try:
            cur.execute(select_sql)
        except psycopg.errors.UndefinedColumn:
            # Transaction might be aborted; rollback and auto-migrate then retry once.
            try:
                conn.rollback()
            except Exception:
                pass
            _ensure_arena_scheduled_runs_questions_promoted_column()
            cur = conn.cursor()
            try:
                cur.execute("SET LOCAL statement_timeout = '10s'")
            except Exception:
                pass
            cur.execute(select_sql)
        runs = [dict(r) for r in cur.fetchall() or []]
        for r in runs:
            run_id = int(r["id"])
            subject = str(r.get("subject") or "English").strip().title()
            run_kind = str(r.get("run_kind") or "").strip().lower()

            if run_kind == "daily":
                qtable = "arena_daily_questions_tmp"
            else:
                qtable = "arena_boss_questions_tmp"

            cur.execute(
                f"""
                SELECT stage, q_index, payload_json
                FROM {qtable}
                WHERE run_id=?
                ORDER BY stage ASC, q_index ASC
                """,
                (run_id,),
            )
            qrows = cur.fetchall() or []

            for qr in qrows:
                payload = {}
                try:
                    payload = json.loads(qr["payload_json"] or "{}")
                except Exception:
                    payload = {}

                created_by = int(payload.get("created_by") or 0)
                level = str(payload.get("level") or "B2").strip().upper() or "B2"
                question = str(payload.get("question") or "").strip()
                option_a = str(payload.get("option_a") or "").strip()
                option_b = str(payload.get("option_b") or "").strip()
                option_c = str(payload.get("option_c") or "").strip()
                option_d = str(payload.get("option_d") or "").strip()
                correct_option_index = int(payload.get("correct_option_index") or 1)
                question_type = payload.get("question_type")

                if not question:
                    continue

                cur.execute(
                    """
                    INSERT INTO daily_tests_bank
                        (created_by, subject, level, question,
                         option_a, option_b, option_c, option_d,
                         correct_option_index, question_type, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        created_by,
                        subject,
                        level,
                        question,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        int(max(1, min(4, correct_option_index))),
                        question_type,
                    ),
                )

            # Mark promoted + cleanup.
            cur.execute(
                "UPDATE arena_scheduled_runs SET questions_promoted=1 WHERE id=?",
                (run_id,),
            )
            # Cleanup tmp question pool.
            cur.execute(f"DELETE FROM {qtable} WHERE run_id=?", (run_id,))

            # Best-effort cleanup (may already be deleted by coordinators).
            cur.execute("DELETE FROM arena_run_answers WHERE run_id=?", (run_id,))
            cur.execute("DELETE FROM arena_run_questions WHERE run_id=?", (run_id,))
            promoted_runs += 1

        conn.commit()
    except Exception:
        logger.exception("promote_expired_daily_arena_questions_to_daily failed")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()
    return promoted_runs


def promote_expired_duel_questions_tmp_to_daily() -> int:
    """
    Promote finished Duel (1v1/5v5) tmp questions into `daily_tests_bank` after 3 hours.
    """
    import json

    if not _is_postgres_enabled():
        return 0
    ensure_duel_matchmaking_schema()
    ensure_arena_questions_tmp_schema()
    ensure_daily_tests_schema()

    conn = get_conn()
    cur = conn.cursor()
    promoted_rows = 0
    try:
        cur.execute(
            """
            SELECT id, subject, level, mode
            FROM open_duel_sessions
            WHERE status='finished'
              AND finished_at <= (CURRENT_TIMESTAMP - INTERVAL '3 hours')
              AND mode IN ('1v1','5v5')
            ORDER BY finished_at ASC
            LIMIT 20
            """
        )
        sessions = [dict(r) for r in cur.fetchall() or []]

        for s in sessions:
            sess_id = int(s["id"])
            subject = str(s.get("subject") or "English").strip().title()
            base_level = str(s.get("level") or "A1").strip().upper() or "A1"

            mode = str(s.get("mode") or "").strip().lower()
            qtable = "duel_1v1_questions_tmp" if mode == "1v1" else "duel_5v5_questions_tmp"

            cur.execute(
                f"""
                SELECT q_index, payload_json
                FROM {qtable}
                WHERE session_id=? AND promoted_at IS NULL
                ORDER BY q_index ASC
                """,
                (sess_id,),
            )
            qrows = cur.fetchall() or []
            if not qrows:
                continue

            for qr in qrows:
                try:
                    payload = json.loads(qr["payload_json"] or "{}")
                except Exception:
                    payload = {}

                created_by = int(payload.get("created_by") or 0)
                level = str(payload.get("level") or base_level).strip().upper() or base_level
                question = str(payload.get("question") or "").strip()
                option_a = str(payload.get("option_a") or "").strip()
                option_b = str(payload.get("option_b") or "").strip()
                option_c = str(payload.get("option_c") or "").strip()
                option_d = str(payload.get("option_d") or "").strip()
                correct_option_index = int(payload.get("correct_option_index") or 1)
                correct_option_index = int(max(1, min(4, correct_option_index)))
                question_type = payload.get("question_type")

                if not question:
                    continue

                cur.execute(
                    """
                    INSERT INTO daily_tests_bank
                        (created_by, subject, level, question,
                         option_a, option_b, option_c, option_d,
                         correct_option_index, question_type, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        created_by,
                        subject,
                        level,
                        question,
                        option_a,
                        option_b,
                        option_c,
                        option_d,
                        correct_option_index,
                        question_type,
                    ),
                )
                promoted_rows += 1

            # Cleanup tmp snapshot after successful promotion.
            cur.execute(f"DELETE FROM {qtable} WHERE session_id=? AND promoted_at IS NULL", (sess_id,))

        conn.commit()
    except Exception:
        logger.exception("promote_expired_duel_questions_tmp_to_daily failed")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()
    return promoted_rows


def ensure_arena_questions_schema() -> None:
    """
    Separate bank for Arena questions.
    For now, Group Arena generator reuses `daily_tests_bank` content and copies rows into this table.
    """
    if not _is_postgres_enabled():
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_questions_bank (
                id BIGSERIAL PRIMARY KEY,
                created_by BIGINT,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option_index INTEGER NOT NULL CHECK (correct_option_index BETWEEN 1 AND 4),
                question_type TEXT,
                active INTEGER DEFAULT 1,
                first_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
            )
        try:
            cur.execute(
                "ALTER TABLE arena_questions_bank ADD COLUMN IF NOT EXISTS promoted_to_daily_at TIMESTAMP"
            )
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def ensure_user_subject_schema() -> None:
    """
    Ensure `user_subject` exists and is seeded from `users.subject`.

    Some flows (scheduled arena notifier) rely on `user_subject` for subject-based fanout.
    In older DBs this table may be missing, so we create it + backfill.
    """
    if not _is_postgres_enabled():
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_subject (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                subject TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, subject)
            )
            '''
        )

        # `users.subject` may store either a single subject (e.g. "Russian")
        # or a comma-separated list (e.g. "English, Russian").
        cur.execute(
            '''
            INSERT INTO user_subject (user_id, subject)
            SELECT
                u.id AS user_id,
                trim(s) AS subject
            FROM users u
            CROSS JOIN LATERAL unnest(string_to_array(u.subject, ',')) AS s
            WHERE u.subject IS NOT NULL
              AND trim(s) <> ''
            ON CONFLICT DO NOTHING
            '''
        )

        conn.commit()
    finally:
        conn.close()


# When daily_tests_bank.question_type is empty, cycle these for group arena staging/export.
GROUP_ARENA_QUESTION_TYPE_CYCLE = (
    "reading",
    "grammar",
    "sentence_error",
    "true_false",
    "synonym",
    "antonym",
    "gap_fill",
    "vocab_definition",
)


def copy_daily_tests_bank_rows_to_arena_questions(
    *,
    bank_ids: list[int],
    created_by: int,
) -> list[int]:
    """
    Copy daily_tests_bank rows into arena_questions_bank.
    Returns new arena_questions_bank ids in the same order as `bank_ids`.
    """
    if not bank_ids:
        return []
    ensure_arena_questions_schema()

    conn = get_conn()
    cur = conn.cursor()
    try:
        placeholders = ",".join(["?"] * len(bank_ids))
        cur.execute(
            f'''
            SELECT id, subject, level, question,
                   option_a, option_b, option_c, option_d,
                   correct_option_index, question_type
            FROM daily_tests_bank
            WHERE id IN ({placeholders})
              AND active=1
            ''',
            tuple(int(x) for x in bank_ids),
        )
        rows = cur.fetchall()
        by_id = {int(r["id"]): r for r in rows}

        arena_ids: list[int] = []
        for i, bid in enumerate(bank_ids):
            r = by_id.get(int(bid))
            if not r:
                continue
            qt_raw = r.get("question_type")
            qt = (str(qt_raw).strip() if qt_raw is not None else "") or ""
            if not qt:
                qt = GROUP_ARENA_QUESTION_TYPE_CYCLE[i % len(GROUP_ARENA_QUESTION_TYPE_CYCLE)]
            # Insert single row to allow grabbing RETURNING id.
            cur.execute(
                '''
                INSERT INTO arena_questions_bank
                    (created_by, subject, level, question,
                     option_a, option_b, option_c, option_d,
                     correct_option_index, question_type, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                RETURNING id
                ''',
                (
                    int(created_by),
                    str(r["subject"]),
                    str(r["level"]),
                    str(r["question"]),
                    str(r["option_a"]),
                    str(r["option_b"]),
                    str(r["option_c"]),
                    str(r["option_d"]),
                    int(r["correct_option_index"]),
                    qt,
                ),
            )
            new_id_row = cur.fetchone()
            if new_id_row:
                # Postgres (psycopg dict_row): {"id": ...}
                # SQLite: may be tuple-like (0-based).
                new_id = None
                try:
                    if isinstance(new_id_row, dict):
                        new_id = new_id_row.get("id")
                    else:
                        new_id = new_id_row[0]
                except Exception:
                    try:
                        new_id = new_id_row["id"]
                    except Exception:
                        new_id = None
                if new_id is not None:
                    arena_ids.append(int(new_id))

        conn.commit()
        return arena_ids
    finally:
        conn.close()


def ensure_arena_other_sessions_schema() -> None:
    """Create placeholder schemas for other arena types (daily/boss/duel)."""
    if not _is_postgres_enabled():
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_daily_sessions (
                id BIGSERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                question_count INTEGER NOT NULL,
                bank_ids_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ready',
                created_by_teacher_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_daily_session_attempts (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                UNIQUE(user_id, session_id)
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_boss_sessions (
                id BIGSERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                level TEXT NOT NULL,
                question_count INTEGER NOT NULL,
                bank_ids_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ready',
                created_by_teacher_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS arena_boss_session_attempts (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                UNIQUE(user_id, session_id)
            )
            '''
        )
        conn.commit()
    finally:
        conn.close()


def create_arena_group_session(
    *,
    group_id: int,
    subject: str,
    level: str,
    question_count: int,
    bank_ids: list[int],
    created_by_teacher_id: int,
) -> int:
    import json

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            INSERT INTO arena_group_sessions
                (group_id, subject, level, question_count, bank_ids_json, created_by_teacher_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ready')
            RETURNING id
            ''',
            (group_id, subject, level, int(question_count), json.dumps(bank_ids), created_by_teacher_id),
        )
        session_id = int(cur.fetchone()["id"])
        conn.commit()
        return session_id
    finally:
        conn.close()


def set_arena_group_session_status(session_id: int, status: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            'UPDATE arena_group_sessions SET status=? WHERE id=?',
            (status, int(session_id)),
        )
        conn.commit()
    finally:
        conn.close()


def cancel_group_arena_sessions_for_date(date_iso: str, group_ids: list[int], admin_note: str | None = None) -> int:
    """
    Cancel group arena sessions created on date for given groups.
    Returns affected session count.
    """
    if not group_ids:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    try:
        placeholders = ",".join(["?"] * len(group_ids))
        # SQLite/Postgres compatibility in this codebase uses DATE(created_at)=?
        cur.execute(
            f"""
            UPDATE arena_group_sessions
            SET status='cancelled', completed_at=CURRENT_TIMESTAMP
            WHERE group_id IN ({placeholders})
              AND DATE(created_at)=?
              AND status IN ('ready','sent')
            """,
            (*[int(gid) for gid in group_ids], str(date_iso)),
        )
        cnt = int(cur.rowcount or 0)
        conn.commit()
        return cnt
    except Exception:
        logger.exception(
            "cancel_group_arena_sessions_for_date failed date=%s groups=%s note=%s",
            date_iso,
            group_ids,
            admin_note,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return 0
    finally:
        conn.close()


def set_arena_group_session_expected_players(session_id: int, expected_players: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            UPDATE arena_group_sessions
            SET expected_players=?, rewards_distributed=0, status='sent'
            WHERE id=?
            ''',
            (int(expected_players), int(session_id)),
        )
        conn.commit()
    finally:
        conn.close()


def _arena_attempt_duration_seconds(row: dict) -> float:
    """Shorter duration wins ties on same correct count."""
    from datetime import datetime

    try:
        sa = row.get("started_at")
        fa = row.get("finished_at")
        if sa is None or fa is None:
            return float("inf")
        if isinstance(sa, (int, float)) and isinstance(fa, (int, float)):
            return max(0.0, float(fa) - float(sa))
        s = str(sa).replace("Z", "").replace("+00:00", "")
        f = str(fa).replace("Z", "").replace("+00:00", "")
        d0 = datetime.fromisoformat(s[:26]) if len(s) > 19 else datetime.fromisoformat(s)
        d1 = datetime.fromisoformat(f[:26]) if len(f) > 19 else datetime.fromisoformat(f)
        return max(0.0, (d1 - d0).total_seconds())
    except Exception:
        return float("inf")


def distribute_arena_group_rewards_if_ready(session_id: int) -> dict:
    """
    Top 3: 5 / 4 / 3 D'coin by highest correct, then fastest completion time.
    Once all expected players finished (finished_at set).
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            SELECT id, subject, expected_players, rewards_distributed
            FROM arena_group_sessions
            WHERE id=?
            ''',
            (int(session_id),),
        )
        sess = cur.fetchone()
        if not sess:
            return {"done": False, "max_correct": None, "winners": [], "winner_rewards": []}

        expected_players = int(sess["expected_players"] or 0)
        if expected_players <= 0:
            return {"done": False, "max_correct": None, "winners": [], "winner_rewards": []}
        if int(sess.get("rewards_distributed") or 0) == 1:
            return {"done": True, "max_correct": None, "winners": [], "winner_rewards": []}

        cur.execute(
            """
            SELECT COUNT(*) as c FROM arena_group_session_attempts
            WHERE session_id=? AND finished_at IS NOT NULL
            """,
            (int(session_id),),
        )
        attempts_count = int((cur.fetchone() or {}).get("c") or 0)
        if attempts_count < expected_players:
            return {"done": False, "max_correct": None, "winners": [], "winner_rewards": []}

        cur.execute(
            """
            SELECT user_id, correct, started_at, finished_at
            FROM arena_group_session_attempts
            WHERE session_id=? AND finished_at IS NOT NULL
            """,
            (int(session_id),),
        )
        rows = [dict(r) for r in cur.fetchall() or []]
        if not rows:
            return {"done": False, "max_correct": None, "winners": [], "winner_rewards": []}

        max_correct = max(int(r.get("correct") or 0) for r in rows)
        ranked = sorted(
            rows,
            key=lambda r: (-int(r.get("correct") or 0), _arena_attempt_duration_seconds(r)),
        )
        amounts = [5.0, 4.0, 3.0]
        winner_rewards: list[tuple[int, float]] = []
        subject = (sess.get("subject") or "").strip().title() or None
        for i, row in enumerate(ranked[:3]):
            uid = int(row["user_id"])
            amt = amounts[i]
            winner_rewards.append((uid, amt))
            try:
                add_dcoins(uid, amt, subject, change_type=f"group_arena_place_{i + 1}")
            except Exception:
                logger.exception(
                    "Failed to add arena group reward uid=%s session_id=%s place=%s",
                    uid,
                    session_id,
                    i + 1,
                )

        winners = [u for u, _ in winner_rewards]

        cur.execute(
            '''
            UPDATE arena_group_sessions
            SET rewards_distributed=1, status='completed', completed_at=CURRENT_TIMESTAMP
            WHERE id=?
            ''',
            (int(session_id),),
        )
        conn.commit()
        return {
            "done": True,
            "max_correct": max_correct,
            "winners": winners,
            "winner_rewards": winner_rewards,
        }
    finally:
        conn.close()


def get_arena_group_session(session_id: int) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            SELECT id, group_id, subject, level, question_count, bank_ids_json, created_by_teacher_id,
                   expected_players, rewards_distributed,
                   status, created_at
                   , teacher_chat_id, teacher_status_message_id
            FROM arena_group_sessions
            WHERE id=?
            ''',
            (int(session_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def mark_arena_group_session_attempt(
    *,
    session_id: int,
    user_id: int,
) -> bool:
    """
    Returns True if inserted (first time for this user & session), else False.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            INSERT INTO arena_group_session_attempts(session_id, user_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, session_id) DO NOTHING
            ''',
            (int(session_id), int(user_id)),
        )
        inserted = cur.rowcount or 0
        conn.commit()
        return bool(inserted)
    finally:
        conn.close()


def finish_arena_group_session_attempt(
    *,
    session_id: int,
    user_id: int,
    correct: int,
    wrong: int,
    unanswered: int,
    net_dcoins: float,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            UPDATE arena_group_session_attempts
            SET finished_at=CURRENT_TIMESTAMP,
                correct=?,
                wrong=?,
                unanswered=?,
                net_dcoins=?
            WHERE session_id=? AND user_id=?
            ''',
            (int(correct), int(wrong), int(unanswered), float(net_dcoins), int(session_id), int(user_id)),
        )
        conn.commit()
    finally:
        conn.close()


def populate_arena_group_questions_tmp(session_id: int) -> int:
    """
    Snapshot Group Arena session questions into `arena_group_questions_tmp`.
    Used for delayed promotion after the session is completed.
    """
    ensure_arena_group_schema()
    ensure_arena_questions_tmp_schema()

    import json

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT subject, level, question_count, bank_ids_json
            FROM arena_group_sessions
            WHERE id=?
            """,
            (int(session_id),),
        )
        sess = cur.fetchone()
        if not sess:
            return 0

        bank_ids = json.loads(sess["bank_ids_json"] or "[]")
        qcount = int(sess.get("question_count") or len(bank_ids) or 0)
        if not bank_ids or qcount <= 0:
            return 0

        # Reset tmp for this session.
        cur.execute("DELETE FROM arena_group_questions_tmp WHERE session_id=?", (int(session_id),))

        bank_ids_int = [int(x) for x in bank_ids]
        placeholders = ",".join(["?"] * len(bank_ids_int))

        def _fetch_rows(table: str) -> dict[int, dict]:
            cur.execute(
                f'''
                SELECT
                    id, created_by, level, question,
                    option_a, option_b, option_c, option_d,
                    correct_option_index, question_type
                FROM {table}
                WHERE id IN ({placeholders})
                  AND active=1
                ''',
                tuple(bank_ids_int),
            )
            rows = cur.fetchall() or []
            return {int(r["id"]): dict(r) for r in rows}

        by_id: dict[int, dict] = {}
        try:
            by_id = _fetch_rows("arena_questions_bank")
        except Exception:
            by_id = {}

        if not by_id:
            by_id = _fetch_rows("daily_tests_bank")

        ordered_payloads: list[tuple[int, dict]] = []
        for bid in bank_ids_int:
            r = by_id.get(int(bid))
            if not r:
                continue
            payload = {
                "question": str(r.get("question") or "").strip(),
                "option_a": str(r.get("option_a") or "").strip(),
                "option_b": str(r.get("option_b") or "").strip(),
                "option_c": str(r.get("option_c") or "").strip(),
                "option_d": str(r.get("option_d") or "").strip(),
                "correct_option_index": int(r.get("correct_option_index") or 1),
                "question_type": r.get("question_type"),
                "level": str(r.get("level") or sess.get("level") or "").strip() or None,
                "created_by": int(r.get("created_by") or 0),
            }
            ordered_payloads.append((int(bid), payload))
            if len(ordered_payloads) >= qcount:
                break

        if not ordered_payloads:
            return 0

        rows_to_insert = []
        for qix, (bank_qid, payload) in enumerate(ordered_payloads, start=1):
            rows_to_insert.append(
                (
                    int(session_id),
                    int(qix),
                    int(bank_qid),
                    json.dumps(payload, ensure_ascii=False),
                )
            )

        cur.executemany(
            """
            INSERT INTO arena_group_questions_tmp(session_id, q_index, bank_question_id, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, q_index) DO UPDATE SET
                bank_question_id=excluded.bank_question_id,
                payload_json=excluded.payload_json,
                promoted_at=NULL
            """,
            rows_to_insert,
        )
        conn.commit()
        return len(rows_to_insert)
    finally:
        conn.close()


def get_arena_group_session_questions(session_id: int) -> list[dict]:
    """
    Fetch selected rows and preserve teacher-selected order.
    New sessions use `arena_questions_bank`.
    Legacy sessions may still reference `daily_tests_bank` ids, so we fallback.
    """
    import json

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            SELECT bank_ids_json, question_count
            FROM arena_group_sessions
            WHERE id=?
            ''',
            (int(session_id),),
        )
        row = cur.fetchone()
        if not row:
            return []
        bank_ids = json.loads(row["bank_ids_json"] or "[]")
        qcount = int(row.get("question_count") or len(bank_ids))

        if not bank_ids:
            return []

        # Prefer runtime tmp snapshot if teacher already populated it.
        # If tmp isn't ready yet, fall back to the legacy sources.
        try:
            cur.execute(
                """
                SELECT q_index, bank_question_id, payload_json
                FROM arena_group_questions_tmp
                WHERE session_id=?
                ORDER BY q_index ASC
                """,
                (int(session_id),),
            )
            tmp_rows = cur.fetchall() or []
            if tmp_rows:
                ordered: list[dict] = []
                for tr in tmp_rows:
                    try:
                        payload = json.loads(tr["payload_json"] or "{}")
                    except Exception:
                        payload = {}
                    ordered.append(
                        {
                            "id": int(tr["bank_question_id"] or 0),
                            "question": payload.get("question"),
                            "option_a": payload.get("option_a"),
                            "option_b": payload.get("option_b"),
                            "option_c": payload.get("option_c"),
                            "option_d": payload.get("option_d"),
                            "correct_option_index": int(payload.get("correct_option_index") or 1),
                            "question_type": payload.get("question_type"),
                        }
                    )
                    if len(ordered) >= qcount:
                        break
                return ordered
        except Exception:
            pass

        placeholders = ",".join(["?"] * len(bank_ids))

        def _fetch_from(table: str) -> list[dict]:
            cur.execute(
                f'''
                SELECT id, question, option_a, option_b, option_c, option_d, correct_option_index, question_type
                FROM {table}
                WHERE id IN ({placeholders})
                  AND active=1
                ''',
                tuple(int(x) for x in bank_ids),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

        ordered: list[dict] = []
        arena_rows = []
        try:
            arena_rows = _fetch_from("arena_questions_bank")
        except Exception:
            arena_rows = []

        if arena_rows:
            by_id = {int(r["id"]): dict(r) for r in arena_rows}
            for bid in bank_ids:
                bdid = int(bid)
                if bdid in by_id:
                    ordered.append(by_id[bdid])
                if len(ordered) >= qcount:
                    break
            if ordered:
                return ordered

        # Legacy fallback: daily_tests_bank ids.
        legacy_rows = _fetch_from("daily_tests_bank")
        by_id = {int(r["id"]): dict(r) for r in legacy_rows}
        for bid in bank_ids:
            bdid = int(bid)
            if bdid in by_id:
                ordered.append(by_id[bdid])
            if len(ordered) >= qcount:
                break
        return ordered
    finally:
        conn.close()


def get_active_arena_group_session_by_group_id(group_id: int) -> dict | None:
    """
    Return the latest 'sent' arena session for a group.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            '''
            SELECT id, group_id, subject, level, question_count, bank_ids_json, created_by_teacher_id, status, created_at
            FROM arena_group_sessions
            WHERE group_id=? AND status='sent'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            ''',
            (int(group_id),),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _scale_daily_test_type_counts(total_questions: int) -> dict[str, int]:
    """
    Integer counts proportional to the historical 20-question mix (5+10+3+2),
    summing exactly to total_questions.
    """
    n = max(1, int(total_questions))
    ratios = (5, 10, 3, 2)
    s = sum(ratios)
    raw = [r * n / s for r in ratios]
    floors = [int(x) for x in raw]
    deficit = n - sum(floors)
    order = sorted(range(4), key=lambda i: raw[i] - floors[i], reverse=True)
    for k in range(deficit):
        floors[order[k]] += 1
    return {
        "grammar_rules_count": floors[0],
        "grammar_sentence_count": floors[1],
        "find_mistake_count": floors[2],
        "error_spotting_count": floors[3],
    }


def ensure_daily_test_type_plan(subject: str, test_date: str, total_questions: int = 10) -> dict:
    """
    Ensure (test_date, subject) has a deterministic question-type mix.
    Counts scale from the 20-question reference mix (5+10+3+2) so the four
    counts always sum to total_questions (e.g. 10 → 3+5+1+1).
    """
    subject = (subject or "").strip().title()
    if subject not in ("English", "Russian"):
        subject = "English"

    conn = get_conn()
    cur = conn.cursor()
    scaled = _scale_daily_test_type_counts(total_questions)
    default = {
        **scaled,
        "total_questions": int(total_questions),
    }
    try:
        cur.execute(
            """
            SELECT grammar_rules_count, grammar_sentence_count, find_mistake_count, error_spotting_count, total_questions
            FROM daily_test_type_plans
            WHERE test_date=? AND subject=?
            """,
            (test_date, subject),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        cur.execute(
            """
            INSERT INTO daily_test_type_plans
            (test_date, subject, grammar_rules_count, grammar_sentence_count, find_mistake_count, error_spotting_count, total_questions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_date,
                subject,
                default["grammar_rules_count"],
                default["grammar_sentence_count"],
                default["find_mistake_count"],
                default["error_spotting_count"],
                default["total_questions"],
            ),
        )
        conn.commit()
        return default
    except Exception:
        # If insert fails due to races or schema mismatch, best-effort fallback.
        conn.rollback()
        return default
    finally:
        conn.close()


def get_daily_test_type_plan_for_subjects(test_date: str, subjects: list[str]) -> dict:
    """
    Return plan counts for the first subject (primarily to format a human message).
    """
    for s in subjects:
        plan = ensure_daily_test_type_plan(s, test_date)
        if plan:
            return plan
    return ensure_daily_test_type_plan("English", test_date)


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

def create_user(first_name, last_name, phone, subject, login_type, owner_admin_id: int | None = None):
    logger.info(f"db.create_user(login_type={login_type}, subject={subject}, first_name={first_name}, last_name={last_name})")
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Login ID va parol generatsiya
        import random, string
        while True:
            login_id = 'ST' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            cur.execute("SELECT 1 FROM users WHERE login_id=%s", (login_id,))
            if not cur.fetchone(): break

        password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        cur.execute('''
            INSERT INTO users (login_id, password, first_name, last_name, phone, subject, login_type, blocked, access_enabled, owner_admin_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        ''', (
            login_id,
            password,
            first_name,
            last_name,
            phone,
            subject,
            login_type,
            1 if login_type == 2 else 0,
            1 if login_type == 3 else 0,
            owner_admin_id,
        ))
        row = cur.fetchone()
        conn.commit()
        return {'id': row["id"], 'login_id': login_id, 'password': password}
    finally:
        conn.close()

def verify_login(login_id, password):
    logger.info(f"db.verify_login(login_id={login_id})")
    conn = get_conn()
    cur = conn.cursor()
    login_id_clean = (login_id or "").strip().upper()
    password_clean = (password or "").strip()
    # Passwords are generated as uppercase alnum; accept lowercase input too.
    password_upper = password_clean.upper()
    cur.execute("SELECT * FROM users WHERE UPPER(login_id)=?", (login_id_clean,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return None, 'not_found'
    if user['blocked']:
        return None, 'blocked'
    stored_password = (user['password'] or "").strip()
    if (stored_password != password_clean and stored_password != password_upper) or user['password_used']:
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


def hard_delete_user_profile(user_id: int) -> bool:
    """Hard-delete user and operational relations from DB."""
    logger.info("db.hard_delete_user_profile(user_id=%s)", user_id)
    ensure_support_lessons_schema()
    ensure_admin_student_shares_schema()
    ensure_temporary_group_assignments_schema()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        try:
            uid = int(user_id)
            cur.execute("SELECT telegram_id, login_type FROM users WHERE id=?", (uid,))
            urow = cur.fetchone()
            if not urow:
                return False

            ukeys = set(urow.keys()) if hasattr(urow, "keys") else set()
            telegram_id = urow["telegram_id"] if "telegram_id" in ukeys else None
            telegram_id_s = str(telegram_id) if telegram_id is not None else None
            login_type = int((urow["login_type"] if "login_type" in ukeys else 0) or 0)
            is_student = login_type in (1, 2)
            is_teacher = login_type == 3

            # Student relations.
            if is_student:
                cur.execute("UPDATE users SET group_id=NULL WHERE id=?", (uid,))
                cur.execute("DELETE FROM user_groups WHERE user_id=?", (uid,))
                cur.execute(
                    """
                    UPDATE admin_student_shares
                    SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP
                    WHERE student_id=? AND status='active'
                    """,
                    (uid,),
                )
                # Remove all share rows for this student (runtime relation cleanup).
                cur.execute("DELETE FROM admin_student_shares WHERE student_id=?", (uid,))

            # Teacher relations + delete teacher-owned groups.
            if is_teacher:
                cur.execute("SELECT id FROM groups WHERE teacher_id=?", (uid,))
                teacher_group_ids = [int((dict(r) if isinstance(r, dict) else {"id": r[0]}).get("id")) for r in (cur.fetchall() or [])]
                for gid in teacher_group_ids:
                    cur.execute("UPDATE users SET group_id=NULL WHERE group_id=?", (gid,))
                    cur.execute("DELETE FROM user_groups WHERE group_id=?", (gid,))
                    for tbl in ("attendance", "attendance_sessions", "monthly_payments", "overdue_penalty_log"):
                        try:
                            cur.execute(f"DELETE FROM {tbl} WHERE group_id=?", (gid,))
                        except Exception:
                            pass
                    try:
                        cur.execute("DELETE FROM temporary_group_assignments WHERE group_id=?", (gid,))
                    except Exception:
                        pass
                    try:
                        cur.execute("DELETE FROM arena_group_sessions WHERE group_id=?", (gid,))
                    except Exception:
                        pass
                    cur.execute("DELETE FROM groups WHERE id=?", (gid,))
                cur.execute("DELETE FROM user_groups WHERE user_id=?", (uid,))
                # If assigned as teacher elsewhere, unlink.
                cur.execute("UPDATE groups SET teacher_id=NULL WHERE teacher_id=?", (uid,))

            # Support/lesson cleanup (best-effort).
            try:
                if telegram_id_s is not None:
                    cur.execute(
                        """
                        DELETE FROM lesson_reminders
                        WHERE booking_id IN (
                            SELECT id FROM lesson_bookings
                            WHERE student_user_id=?
                        ) OR telegram_id=?
                        """,
                        (uid, telegram_id_s),
                    )
                    cur.execute("DELETE FROM lesson_waitlist WHERE telegram_id=?", (telegram_id_s,))
                    cur.execute("DELETE FROM lesson_users WHERE telegram_id=?", (telegram_id_s,))
                    cur.execute("DELETE FROM lesson_bookings WHERE student_user_id=? OR student_telegram_id=?", (uid, telegram_id_s))
                else:
                    cur.execute(
                        """
                        DELETE FROM lesson_reminders
                        WHERE booking_id IN (
                            SELECT id FROM lesson_bookings
                            WHERE student_user_id=?
                        )
                        """,
                        (uid,),
                    )
                    cur.execute("DELETE FROM lesson_bookings WHERE student_user_id=?", (uid,))
            except Exception:
                logger.exception("hard_delete_user_profile: support cleanup failed uid=%s", uid)
                try:
                    conn.rollback()
                except Exception:
                    pass
                cur = conn.cursor()

            # Broad cleanup by common user-id columns to ensure profile disappears from runtime/rating areas.
            target_cols = (
                "user_id",
                "student_user_id",
                "teacher_id",
                "owner_teacher_id",
                "temp_teacher_id",
                "opponent_user_id",
                "last_opponent_user_id",
                "created_by_user_id",
                "added_by",
                "admin_id",
                "handled_by_admin_id",
            )
            try:
                if _is_postgres_enabled():
                    cur.execute(
                        """
                        SELECT table_name, column_name
                        FROM information_schema.columns
                        WHERE table_schema='public'
                          AND column_name = ANY(%s)
                        """,
                        (list(target_cols),),
                    )
                    rows = cur.fetchall() or []
                else:
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    rows = []
                    for tr in cur.fetchall() or []:
                        tname = (dict(tr) if isinstance(tr, dict) else {"name": tr[0]}).get("name")
                        if not tname:
                            continue
                        try:
                            cur.execute(f"PRAGMA table_info({tname})")
                            cols = cur.fetchall() or []
                            for c in cols:
                                cname = (dict(c) if isinstance(c, dict) else {"name": c[1]}).get("name")
                                if cname in target_cols:
                                    rows.append({"table_name": tname, "column_name": cname})
                        except Exception:
                            continue
                for r in rows:
                    table_name = (dict(r) if isinstance(r, dict) else {"table_name": r[0]}).get("table_name")
                    column_name = (dict(r) if isinstance(r, dict) else {"column_name": r[1]}).get("column_name")
                    if not table_name or not column_name:
                        continue
                    if table_name in ("users", "groups"):
                        continue
                    try:
                        cur.execute(f"DELETE FROM {table_name} WHERE {column_name}=?", (uid,))
                    except Exception:
                        continue
            except Exception:
                logger.exception("hard_delete_user_profile: broad cleanup scan failed uid=%s", uid)

            # Final hard delete user row.
            cur.execute("DELETE FROM users WHERE id=?", (uid,))
            changed = int(cur.rowcount or 0) > 0
            conn.commit()
            return changed
        except Exception:
            logger.exception("hard_delete_user_profile failed user_id=%s", user_id)
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()


def soft_delete_user_profile(user_id: int) -> bool:
    """Backward-compatible alias: now performs hard delete."""
    return hard_delete_user_profile(user_id)


def logout_user_by_telegram(telegram_id: str):
    """User-initiated logout: unlink telegram_id so they can login again."""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        # Clear telegram link and allow re-login with the same login/password if needed
        cur.execute(
            "UPDATE users SET telegram_id=NULL, logged_in=0, password_used=0 WHERE telegram_id=?",
            (telegram_id,)
        )
        conn.commit()
        conn.close()


def update_user_telegram_id(user_id: int, telegram_id: str):
    """Update user's telegram_id"""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET telegram_id=? WHERE id=?", (telegram_id, user_id))
            conn.commit()
            logger.info(f"db.update_user_telegram_id: set telegram_id={telegram_id} for user_id={user_id}")
        except psycopg.IntegrityError:
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


def get_user_by_name_search(name: str, limit: int = 20) -> list[dict]:
    """Case-insensitive search by first name, last name, or full name (SQLite/Postgres)."""
    name = (name or "").strip()
    if len(name) < 1:
        return []
    conn = get_conn()
    cur = conn.cursor()
    like = f"%{name.lower()}%"
    cur.execute(
        """
        SELECT * FROM users
        WHERE LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')) LIKE ?
           OR LOWER(COALESCE(first_name, '')) LIKE ?
           OR LOWER(COALESCE(last_name, '')) LIKE ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (like, like, like, int(limit)),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def search_student_users_for_group_pick(query: str, limit: int = 500) -> list[dict]:
    """
    DB-backed search for students (login_type 1/2) when adding to a group.
    Matches first/last/full name, login_id, or telegram_id substring.
    Caller should apply admin scope via _scope_users_for_admin.
    """
    q = (query or "").strip()
    if len(q) < 1:
        return []
    conn = get_conn()
    cur = conn.cursor()
    like = f"%{q.lower()}%"
    tg_like = f"%{q}%"
    lim = max(1, min(2000, int(limit)))
    cur.execute(
        """
        SELECT * FROM users
        WHERE login_type IN (1, 2)
          AND (
            LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')) LIKE ?
            OR LOWER(COALESCE(first_name, '')) LIKE ?
            OR LOWER(COALESCE(last_name, '')) LIKE ?
            OR LOWER(COALESCE(login_id, '')) LIKE ?
            OR CAST(telegram_id AS TEXT) LIKE ?
          )
        ORDER BY id DESC
        LIMIT ?
        """,
        (like, like, like, like, tg_like, lim),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


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

def save_test_result(user_id, subject, score, level, max_score: int = 500):
    """Placement test uses score 0..500 (50 questions x 10)."""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO test_results (user_id, subject, score, level, max_score)
            VALUES (?,?,?,?,?)
        ''', (user_id, subject, score, level, int(max_score)))
        conn.commit()
        conn.close()


def get_latest_test_result(user_id: int) -> dict | None:
    """Most recent test_results row for user (any subject)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM test_results
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (int(user_id),),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def extract_cefr_level_code(level_raw: str) -> str:
    """Normalize level strings (e.g. 'A2 (Elementary)') to CEFR code for group matching."""
    s = (level_raw or "").strip().upper()
    for code in ("MIXED", "C2", "C1", "B2", "B1", "A2", "A1"):
        if code in s:
            return code
    if len(s) >= 2 and s[0] in "ABC" and s[1].isdigit():
        return s[:2]
    parts = s.split()
    return parts[0] if parts else ""


def get_latest_test_result_for_subject(user_id: int, subject: str) -> dict | None:
    """Oxirgi placement/natija yozuvi (fan bo‘yicha)."""
    subj = (subject or "").strip()
    if not subj:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM test_results
        WHERE user_id = ? AND LOWER(TRIM(subject)) = LOWER(?)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (int(user_id), subj.strip()),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


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

def get_recent_results(limit: int = 15):
    conn = get_conn()
    cur = conn.cursor()
    lim = max(1, min(100, int(limit or 15)))
    # Placement test results are stored in `test_results` with `max_score=500`.
    # For backward compatibility (older DBs), detect if `max_score` column exists.
    has_max_score = False
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='test_results' AND column_name='max_score'
                LIMIT 1
                """
            )
            has_max_score = cur.fetchone() is not None
        else:
            cur.execute("PRAGMA table_info(test_results)")
            cols = {str(r["name"]) for r in cur.fetchall()}
            has_max_score = "max_score" in cols
    except Exception:
        has_max_score = False

    if has_max_score:
        cur.execute(
            "SELECT * FROM test_results WHERE max_score=? ORDER BY created_at DESC LIMIT ?",
            (500, lim),
        )
    else:
        cur.execute("SELECT * FROM test_results ORDER BY created_at DESC LIMIT ?", (lim,))
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

def create_group(name, teacher_id, level='All', subject=None, lesson_date=None, lesson_start=None, lesson_end=None, tz='Asia/Tashkent', owner_admin_id: int | None = None):
    """Yangi guruhi yaratish"""
    logger.info(
        f"create_group called with: name={name}, teacher_id={teacher_id}, level={level}, subject={subject}, "
        f"lesson_date={lesson_date}, lesson_start={lesson_start}, lesson_end={lesson_end}, tz={tz}, owner_admin_id={owner_admin_id}"
    )
    
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO groups (name, teacher_id, level, subject, lesson_date, lesson_start, lesson_end, tz, owner_admin_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (name, teacher_id, level, subject, lesson_date, lesson_start, lesson_end, tz, owner_admin_id))
        row = cur.fetchone()
        conn.commit()
        group_id = row["id"]
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


def create_temporary_group_assignment(
    group_id: int,
    owner_teacher_id: int,
    temp_teacher_id: int,
    lesson_date: str,
    lesson_start: str | None = None,
    lesson_end: str | None = None,
) -> int:
    ensure_temporary_group_assignments_schema()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO temporary_group_assignments
            (group_id, owner_teacher_id, temp_teacher_id, lesson_date, lesson_start, lesson_end, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            """,
            (int(group_id), int(owner_teacher_id), int(temp_teacher_id), lesson_date, lesson_start, lesson_end),
        )
        assignment_id = int(getattr(cur, "lastrowid", 0) or 0)
        if _is_postgres_enabled():
            cur.execute("SELECT currval(pg_get_serial_sequence('temporary_group_assignments','id')) AS id")
            row = cur.fetchone()
            if row:
                assignment_id = int(row["id"])
        conn.commit()
        conn.close()
        return assignment_id


def get_active_temporary_assignments_by_owner(owner_teacher_id: int) -> list[dict]:
    ensure_temporary_group_assignments_schema()
    tz = pytz.timezone("Asia/Tashkent")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tga.*, g.name AS group_name, g.level AS group_level
        FROM temporary_group_assignments tga
        JOIN groups g ON g.id = tga.group_id
        WHERE tga.owner_teacher_id=? AND tga.status='active' AND tga.lesson_date >= ?
        ORDER BY tga.lesson_date ASC, COALESCE(tga.lesson_start, '') ASC
        """,
        (int(owner_teacher_id), today),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_active_temporary_assignments_for_pair(owner_teacher_id: int, group_id: int, temp_teacher_id: int) -> list[dict]:
    ensure_temporary_group_assignments_schema()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM temporary_group_assignments
        WHERE owner_teacher_id=?
          AND group_id=?
          AND temp_teacher_id=?
          AND status='active'
        ORDER BY lesson_date ASC, COALESCE(lesson_start, '') ASC
        """,
        (int(owner_teacher_id), int(group_id), int(temp_teacher_id)),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_temporary_teachers_for_group_on_date(group_id: int, lesson_date: str) -> list[dict]:
    """
    Return temporary teacher user rows assigned to this group on exact lesson_date.
    """
    ensure_temporary_group_assignments_schema()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT u.*
        FROM temporary_group_assignments tga
        JOIN users u ON u.id = tga.temp_teacher_id
        WHERE tga.group_id=?
          AND tga.lesson_date=?
          AND tga.status='active'
        ORDER BY u.first_name, u.last_name, u.id
        """,
        (int(group_id), str(lesson_date)),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_groups_with_temporary_access_for_teacher(teacher_id: int) -> list[dict]:
    ensure_temporary_group_assignments_schema()
    tz = pytz.timezone("Asia/Tashkent")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT g.*
        FROM temporary_group_assignments tga
        JOIN groups g ON g.id = tga.group_id
        WHERE tga.temp_teacher_id=?
          AND tga.status='active'
          AND tga.lesson_date >= ?
        ORDER BY g.name
        """,
        (int(teacher_id), today),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def teacher_has_temporary_group_access(teacher_id: int, group_id: int) -> bool:
    ensure_temporary_group_assignments_schema()
    tz = pytz.timezone("Asia/Tashkent")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM temporary_group_assignments
        WHERE temp_teacher_id=?
          AND group_id=?
          AND status='active'
          AND lesson_date >= ?
        LIMIT 1
        """,
        (int(teacher_id), int(group_id), today),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row)


def cancel_temporary_assignments_for_pair(owner_teacher_id: int, group_id: int, temp_teacher_id: int) -> int:
    ensure_temporary_group_assignments_schema()
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE temporary_group_assignments
            SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP
            WHERE owner_teacher_id=?
              AND group_id=?
              AND temp_teacher_id=?
              AND status='active'
            """,
            (int(owner_teacher_id), int(group_id), int(temp_teacher_id)),
        )
        affected = int(cur.rowcount or 0)
        conn.commit()
        conn.close()
        return affected

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
            cur.execute("INSERT INTO user_groups (user_id, group_id) VALUES (%s, %s)", (user_id, group_id))
        except psycopg.IntegrityError:
            # User already in this group
            conn.close()
            return
        
        # Legacy support (old column)
        cur.execute("UPDATE users SET group_id=? WHERE id=?", (group_id, user_id))
        # When admin assigns a group, student should be able to access student bot.
        cur.execute("UPDATE users SET blocked=0, access_enabled=1 WHERE id=?", (user_id,))

        # Keep users.subject CSV in sync with group fanlari (bir nechta guruh / fan)
        cur.execute("SELECT subject FROM groups WHERE id=?", (group_id,))
        gr_sub = cur.fetchone()
        gsub = (gr_sub["subject"] or "").strip() if gr_sub else ""
        if gsub:
            cur.execute("SELECT subject FROM users WHERE id=?", (user_id,))
            urow = cur.fetchone()
            old = (urow["subject"] or "").strip() if urow else ""
            parts = [p.strip() for p in old.split(",") if p.strip()]
            if gsub not in parts:
                parts.append(gsub)
                cur.execute("UPDATE users SET subject=? WHERE id=?", (",".join(parts), user_id))
        
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
    """Update group lesson days (lesson_date is canonical for schedule UI; lesson_days kept in sync)."""
    with DB_WRITE_LOCK:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE groups SET lesson_date=?, lesson_days=? WHERE id=?",
            (days, days, group_id),
        )
        conn.commit()
        conn.close()


RUSSIAN_GROUP_LEVELS = (
    'Начальный уровень (А1)',
    'Базовый уровень (А2)',
    'Средний (Б1)',
    'Продвинутый средний (Б2)',
)


def _russian_level_rank(level: str) -> int | None:
    raw = (level or '').strip()
    if raw in RUSSIAN_GROUP_LEVELS:
        return RUSSIAN_GROUP_LEVELS.index(raw)
    low = raw.lower().replace('ё', 'е')
    if 'началь' in low or 'а1' in low:
        return 0
    if 'базов' in low or 'элементар' in low or 'а2' in low:
        return 1
    if 'средн' in low or low == 'b1' or 'б1' in low:
        return 2
    if 'продвинут' in low or low == 'b2' or 'б2' in low:
        return 3
    return None


def normalize_russian_group_level(level: str | None) -> str | None:
    rank = _russian_level_rank(level or "")
    if rank is None:
        return None
    return RUSSIAN_GROUP_LEVELS[rank]


def is_higher_level(new_level, current_level):
    """Yangi level avvalgisidan yuqorimi"""
    nr = _russian_level_rank(new_level)
    cr = _russian_level_rank(current_level)
    if nr is not None and cr is not None:
        return nr > cr
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
    """Foydalanuvchining barcha fanlarini olish (guruhlar + users.subject qatoridagi CSV)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT g.subject FROM groups g
        JOIN user_groups ug ON g.id = ug.group_id
        WHERE ug.user_id = ? AND g.subject IS NOT NULL AND TRIM(g.subject) != ''
    """, (user_id,))
    subjects = [row["subject"] for row in cur.fetchall()]
    cur.execute("SELECT subject FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row and row["subject"]:
        for part in str(row["subject"]).split(","):
            s = part.strip()
            if s and s not in subjects:
                subjects.append(s)
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
        gid = int(group_id)
        # Unlink students first
        cur.execute("UPDATE users SET group_id=NULL WHERE group_id=?", (gid,))

        # Remove group memberships.
        cur.execute("DELETE FROM user_groups WHERE group_id=?", (gid,))

        # Cleanup group-scoped operational tables (best-effort).
        try:
            cur.execute("DELETE FROM attendance WHERE group_id=?", (gid,))
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM attendance_sessions WHERE group_id=?", (gid,))
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM monthly_payments WHERE group_id=?", (gid,))
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM overdue_penalty_log WHERE group_id=?", (gid,))
        except Exception:
            pass

        # Finally delete the group row.
        cur.execute("DELETE FROM groups WHERE id=?", (gid,))
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
        try:
            if paid:
                cur.execute(
                    '''
                    INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                    VALUES(?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, ym, group_id) DO UPDATE SET
                        paid=1,
                        paid_at=CURRENT_TIMESTAMP,
                        subject=COALESCE(excluded.subject, monthly_payments.subject)
                    ''',
                    (user_id, ym, group_id, subject),
                )
            else:
                cur.execute(
                    '''
                    INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at)
                    VALUES(?, ?, ?, ?, 0, NULL)
                    ON CONFLICT(user_id, ym, group_id) DO UPDATE SET
                        paid=0,
                        paid_at=NULL,
                        subject=COALESCE(excluded.subject, monthly_payments.subject)
                    ''',
                    (user_id, ym, group_id, subject),
                )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
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
        # Portable for both SQLite and PostgreSQL regardless of unique indexes.
        cur.execute(
            "UPDATE monthly_payments SET notified_days=? WHERE user_id=? AND ym=?",
            (new_days, user_id, ym),
        )
        if cur.rowcount == 0:
            cur.execute(
                '''
                INSERT INTO monthly_payments(user_id, ym, group_id, subject, paid, paid_at, notified_days)
                VALUES(?, ?, NULL, NULL, 0, NULL, ?)
                ''',
                (user_id, ym, new_days),
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
              attempts=COALESCE(grammar_attempts.attempts,0)+1,
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
        # Portable upsert: update first, insert if missing.
        cur.execute(
            "UPDATE attendance SET status=?, created_at=CURRENT_TIMESTAMP WHERE user_id=? AND group_id=? AND date=?",
            (status, user_id, group_id, date),
        )
        if cur.rowcount == 0:
            cur.execute(
                '''
                INSERT INTO attendance (user_id, group_id, date, status)
                VALUES (?, ?, ?, ?)
                ''',
                (user_id, group_id, date, status),
            )
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


def get_present_students_for_group_date(group_id: int, date_str: str) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT u.*
        FROM attendance a
        JOIN users u ON u.id = a.user_id
        WHERE a.group_id=? AND a.date=? AND LOWER(COALESCE(a.status,''))='present'
          AND u.login_type IN (1,2)
        ''',
        (group_id, date_str),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# ====================== DIAMOND BOSHQARUVI ======================

def _is_missing_subject_dcoins_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "user_subject_dcoins" in msg
        and ("does not exist" in msg or "no such table" in msg)
    )


def _subject_dcoins_table_exists(cur) -> bool:
    try:
        if _is_postgres_enabled():
            cur.execute("SELECT to_regclass('user_subject_dcoins') AS reg")
            row = cur.fetchone() or {}
            if bool(row.get("reg")):
                return True
            cur.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name='user_subject_dcoins'
                  AND table_schema = ANY (current_schemas(true))
                LIMIT 1
                """
            )
            return bool(cur.fetchone())
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_subject_dcoins'"
        )
        return bool(cur.fetchone())
    except Exception:
        return False


def _ensure_subject_dcoins_ready(cur, *, context: str) -> bool:
    try:
        ensure_subject_dcoin_schema()
    except Exception:
        logger.exception("ensure_subject_dcoin_schema() failed in %s", context)
    if _subject_dcoins_table_exists(cur):
        return True
    logger.error(
        "user_subject_dcoins table missing in %s after ensure; unexpected runtime degradation fallback",
        context,
    )
    return False


def validate_dcoin_runtime_ready(*, context: str = "startup") -> bool:
    """Validate critical D'coin table readiness for the running process."""
    try:
        ensure_subject_dcoin_schema()
        ensure_dcoin_schema_migrations()
    except Exception:
        logger.exception("D'coin schema ensure/migration failed during %s", context)
        return False

    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _subject_dcoins_table_exists(cur):
            logger.error("D'coin runtime not ready during %s: user_subject_dcoins is missing", context)
            return False
        cur.execute("SELECT 1 FROM user_subject_dcoins LIMIT 1")
        # Dry-run write-path probe: parse UPDATE without mutating rows.
        cur.execute("UPDATE user_subject_dcoins SET updated_at=updated_at WHERE 1=0")
        conn.rollback()
        logger.info("D'coin runtime readiness OK during %s", context)
        return True
    except Exception:
        logger.exception("D'coin runtime readiness probe failed during %s", context)
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()

def add_dcoins(user_id, amount, subject: str | None = None, *, change_type: str | None = None) -> None:
    """Talabaga D'coin qo'shish (ixtiyoriy: fan kesimida)."""
    with DB_WRITE_LOCK:
        ensure_subject_dcoin_schema()
        conn = get_conn()
        cur = conn.cursor()
        from datetime import datetime
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        subj = (subject or "").strip().title()
        if not subj:
            try:
                subjects = get_user_subjects(user_id) or []
                if subjects:
                    subj = str(subjects[0]).strip().title()
            except Exception:
                subj = ""
        if not subj:
            subj = "English"

        if not _ensure_subject_dcoins_ready(cur, context="add_dcoins"):
            conn.close()
            return

        # New model: always keep per-subject balances as source-of-truth.
        try:
            cur.execute(
                '''
                INSERT INTO user_subject_dcoins (user_id, subject, balance, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, subject)
                DO UPDATE SET
                    balance = user_subject_dcoins.balance + excluded.balance,
                    updated_at = excluded.updated_at
                ''',
                (user_id, subj, amount, now),
            )
        except Exception as e:
            if not _is_missing_subject_dcoins_error(e):
                raise
            try:
                conn.rollback()
            except Exception:
                pass
            if not _ensure_subject_dcoins_ready(cur, context="add_dcoins:retry"):
                conn.close()
                return
            cur.execute(
                '''
                INSERT INTO user_subject_dcoins (user_id, subject, balance, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, subject)
                DO UPDATE SET
                    balance = user_subject_dcoins.balance + excluded.balance,
                    updated_at = excluded.updated_at
                ''',
                (user_id, subj, amount, now),
            )

        # Subject-aware history.
        cur.execute(
            '''
            INSERT INTO diamond_history (user_id, dcoin_change, subject, created_at, change_type)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (user_id, amount, subj or None, now, change_type),
        )

        conn.commit()
        conn.close()

def get_dcoins(user_id, subject: str | None = None) -> float:
    """Talabaning D'coin balansi (jami yoki fan bo'yicha)."""
    def _ensure_schema_and_retry():
        try:
            ensure_subject_dcoin_schema()
        except Exception:
            logger.exception("ensure_subject_dcoin_schema() failed inside get_dcoins")

    _ensure_schema_and_retry()
    conn = get_conn()
    cur = conn.cursor()
    subj = (subject or "").strip().title()
    try:
        if subj:
            try:
                cur.execute(
                    "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                    (user_id, subj),
                )
            except Exception as e:
                if not _is_missing_subject_dcoins_error(e):
                    raise
                try:
                    conn.rollback()
                except Exception:
                    pass
                _ensure_schema_and_retry()
                if not _ensure_subject_dcoins_ready(cur, context="get_dcoins:subject"):
                    logger.error("user_subject_dcoins table is still missing after ensure (subject mode); returning 0.0")
                    return 0.0
                cur.execute(
                    "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                    (user_id, subj),
                )
            row = cur.fetchone()
            if not row or float((row or {}).get("balance") or 0) <= 0:
                _migrate_legacy_user_diamonds_to_subjects(user_id, forced_subject=subj)
                cur.execute(
                    "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                    (user_id, subj),
                )
                row = cur.fetchone()
            return float(row["balance"] or 0) if row else 0.0

        # Total subject balances only (legacy users.diamonds is deprecated).
        try:
            cur.execute("SELECT COALESCE(SUM(balance), 0) as total FROM user_subject_dcoins WHERE user_id=?", (user_id,))
        except Exception as e:
            if not _is_missing_subject_dcoins_error(e):
                raise
            try:
                conn.rollback()
            except Exception:
                pass
            _ensure_schema_and_retry()
            if not _ensure_subject_dcoins_ready(cur, context="get_dcoins:total"):
                logger.error("user_subject_dcoins table is still missing after ensure (total mode); returning 0.0")
                return 0.0
            cur.execute("SELECT COALESCE(SUM(balance), 0) as total FROM user_subject_dcoins WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        total = float((row or {}).get("total") or 0)
        if total <= 0:
            _migrate_legacy_user_diamonds_to_subjects(user_id, forced_subject=None)
            cur.execute("SELECT COALESCE(SUM(balance), 0) as total FROM user_subject_dcoins WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            total = float((row or {}).get("total") or 0)
        return total
    finally:
        conn.close()


def try_consume_dcoins(
    user_id: int,
    amount: float,
    subject: str,
    *,
    arena_type: str | None = None,
    change_type: str | None = None,
) -> bool:
    """Deduct amount from a specific subject balance if enough funds."""
    amount = float(amount)
    if amount <= 0:
        return True
    subj = (subject or "").strip().title()
    if not subj:
        return False
    with DB_WRITE_LOCK:
        ensure_subject_dcoin_schema()
        conn = get_conn()
        cur = conn.cursor()
        try:
            if not _ensure_subject_dcoins_ready(cur, context="try_consume_dcoins"):
                return False
            cur.execute(
                "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                (user_id, subj),
            )
            row = cur.fetchone()
            have = float(row["balance"] or 0) if row else 0.0
            if have <= 0:
                _migrate_legacy_user_diamonds_to_subjects(user_id, forced_subject=subj)
                cur.execute(
                    "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                    (user_id, subj),
                )
                row = cur.fetchone()
                have = float(row["balance"] or 0) if row else 0.0
            if have < amount:
                return False
            from datetime import datetime
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "UPDATE user_subject_dcoins SET balance=balance-?, updated_at=? WHERE user_id=? AND subject=?",
                (amount, now, user_id, subj),
            )
            ct = change_type or (f"arena_fee:{arena_type}" if arena_type else "consume")
            cur.execute(
                "INSERT INTO diamond_history (user_id, dcoin_change, subject, created_at, change_type) VALUES (?, ?, ?, ?, ?)",
                (user_id, -amount, subj, now, ct),
            )
            conn.commit()
            return True
        except Exception as e:
            if _is_missing_subject_dcoins_error(e):
                logger.error("user_subject_dcoins missing in try_consume_dcoins; rejecting consume request")
            else:
                logger.exception("try_consume_dcoins failed for user_id=%s subject=%s", user_id, subj)
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass


def consume_dcoins_allow_negative(
    user_id: int,
    amount: float,
    subject: str,
    *,
    change_type: str = "consume_allow_negative",
) -> float:
    """
    Deduct amount from subject balance even if it becomes negative.
    Returns new balance after deduction (best-effort).
    """
    amount = float(amount)
    if amount <= 0:
        return float(get_dcoins(user_id, subject))
    subj = (subject or "").strip().title()
    if not subj:
        subj = "English"

    with DB_WRITE_LOCK:
        ensure_subject_dcoin_schema()
        conn = get_conn()
        cur = conn.cursor()
        try:
            if not _ensure_subject_dcoins_ready(cur, context="consume_dcoins_allow_negative"):
                return float(get_dcoins(user_id, subj))
            cur.execute(
                "SELECT balance FROM user_subject_dcoins WHERE user_id=? AND subject=?",
                (user_id, subj),
            )
            row = cur.fetchone()
            have = float(row["balance"] or 0) if row else 0.0
            from datetime import datetime
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if row is None:
                cur.execute(
                    """
                    INSERT INTO user_subject_dcoins (user_id, subject, balance, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (user_id, subject)
                    DO UPDATE SET balance=user_subject_dcoins.balance, updated_at=excluded.updated_at
                    """,
                    (user_id, subj, have, now),
                )
                have = float(get_dcoins(user_id, subj))

            cur.execute(
                "UPDATE user_subject_dcoins SET balance=balance-?, updated_at=? WHERE user_id=? AND subject=?",
                (amount, now, user_id, subj),
            )
            cur.execute(
                "INSERT INTO diamond_history (user_id, dcoin_change, subject, created_at, change_type) VALUES (?, ?, ?, ?, ?)",
                (user_id, -amount, subj, now, change_type),
            )
            conn.commit()
            return have - amount
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.exception(
                "consume_dcoins_allow_negative failed for user_id=%s subject=%s",
                user_id,
                subj,
            )
            return float(get_dcoins(user_id, subj))
        finally:
            try:
                conn.close()
            except Exception:
                pass

def get_leaderboard_global(limit=10, offset=0):
    """Global reyting (butun markaz boyicha)"""
    ensure_subject_dcoin_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_global"):
            return []
        cur.execute(
            '''
            SELECT u.id, u.first_name, u.last_name, COALESCE(SUM(sd.balance), 0) as dcoin_balance
            FROM users u
            LEFT JOIN user_subject_dcoins sd ON sd.user_id = u.id
            WHERE u.access_enabled=1 AND u.login_type IN (1,2)
            GROUP BY u.id, u.first_name, u.last_name
            HAVING COALESCE(SUM(sd.balance), 0) > 0
            ORDER BY dcoin_balance DESC
            LIMIT ? OFFSET ?
            ''',
            (limit, offset),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: global table missing")
            return []
        raise
    finally:
        conn.close()


def get_leaderboard_by_subject(subject: str, limit=10, offset=0):
    """Fan bo'yicha reyting."""
    ensure_subject_dcoin_schema()
    subj = (subject or "").strip().title()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_by_subject"):
            return []
        cur.execute(
            '''
            SELECT u.id, u.first_name, u.last_name, COALESCE(sd.balance, 0) as dcoin_balance
            FROM users u
            JOIN user_subject_dcoins sd ON sd.user_id = u.id
            WHERE sd.subject=? AND sd.balance > 0 AND u.login_type IN (1,2) AND u.access_enabled=1
            ORDER BY sd.balance DESC
            LIMIT ? OFFSET ?
            ''',
            (subj, limit, offset),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: subject table missing")
            return []
        raise
    finally:
        conn.close()

def get_leaderboard_by_group(group_id, limit=10, offset=0):
    """GuruH bo'yicha reyting"""
    ensure_subject_dcoin_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_by_group"):
            return []
        cur.execute(
            '''
            SELECT u.id, u.first_name, u.last_name, COALESCE(SUM(sd.balance), 0) as dcoin_balance
            FROM users u
            LEFT JOIN user_subject_dcoins sd ON sd.user_id = u.id
            WHERE u.group_id=? AND u.login_type IN (1,2)
            GROUP BY u.id, u.first_name, u.last_name
            HAVING COALESCE(SUM(sd.balance), 0) > 0
            ORDER BY dcoin_balance DESC
            LIMIT ? OFFSET ?
            ''',
            (group_id, limit, offset),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: group table missing")
            return []
        raise
    finally:
        conn.close()

def get_leaderboard_count():
    """Global reytingdagi umumiy foydalanuvchi soni"""
    ensure_subject_dcoin_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_count"):
            return 0
        cur.execute(
            '''
            SELECT COUNT(*) as count FROM (
                SELECT u.id
                FROM users u
                LEFT JOIN user_subject_dcoins sd ON sd.user_id = u.id
                WHERE u.access_enabled=1 AND u.login_type IN (1,2)
                GROUP BY u.id
                HAVING COALESCE(SUM(sd.balance), 0) > 0
            ) t
            '''
        )
        row = cur.fetchone()
        return row['count'] if row else 0
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: count table missing")
            return 0
        raise
    finally:
        conn.close()


def get_leaderboard_count_by_subject(subject: str):
    ensure_subject_dcoin_schema()
    subj = (subject or "").strip().title()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_count_by_subject"):
            return 0
        cur.execute(
            '''
            SELECT COUNT(*) as count
            FROM users u
            JOIN user_subject_dcoins sd ON sd.user_id=u.id
            WHERE sd.subject=? AND sd.balance > 0 AND u.login_type IN (1,2) AND u.access_enabled=1
            ''',
            (subj,),
        )
        row = cur.fetchone()
        return row['count'] if row else 0
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: subject count table missing")
            return 0
        raise
    finally:
        conn.close()


def get_staff_leaderboard_by_subject(subject: str, limit: int = 10, offset: int = 0) -> list[dict]:
    """Alias for admin/teacher bot D'coin leaderboard (per-subject)."""
    return get_leaderboard_by_subject(subject, limit=limit, offset=offset)


def get_staff_leaderboard_student_count(subject: str) -> int:
    """Total students on subject leaderboard (for pagination); not global across subjects."""
    return get_leaderboard_count_by_subject(subject)


def get_subject_dcoin_history_rows(subject: str, owner_admin_id: int | None = None) -> list[dict]:
    """Return D'coin history rows for a subject, newest first."""
    ensure_subject_dcoin_schema()
    subj = (subject or "").strip().title()
    if not subj:
        return []

    conn = get_conn()
    cur = conn.cursor()
    try:
        if owner_admin_id is not None:
            cur.execute(
                """
                SELECT
                    u.first_name,
                    u.last_name,
                    u.login_id,
                    dh.created_at,
                    dh.dcoin_change,
                    COALESCE(dh.change_type, '') AS change_type,
                    dh.subject
                FROM diamond_history dh
                JOIN users u ON u.id = dh.user_id
                WHERE LOWER(COALESCE(dh.subject, '')) = LOWER(?)
                  AND u.login_type IN (1, 2)
                  AND (
                    u.owner_admin_id = ?
                    OR u.id IN (
                        SELECT student_id
                        FROM admin_student_shares
                        WHERE peer_admin_id = ? AND status = 'active'
                    )
                  )
                ORDER BY dh.created_at DESC
                """,
                (subj, owner_admin_id, owner_admin_id),
            )
        else:
            cur.execute(
                """
                SELECT
                    u.first_name,
                    u.last_name,
                    u.login_id,
                    dh.created_at,
                    dh.dcoin_change,
                    COALESCE(dh.change_type, '') AS change_type,
                    dh.subject
                FROM diamond_history dh
                JOIN users u ON u.id = dh.user_id
                WHERE LOWER(COALESCE(dh.subject, '')) = LOWER(?)
                  AND u.login_type IN (1, 2)
                ORDER BY dh.created_at DESC
                """,
                (subj,),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


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


def get_group_level_for_subject(user_id: int, subject: str) -> str | None:
    """First group level for this student matching the subject (for multi-subject daily tests)."""
    want = (subject or "").strip().title()
    for g in get_user_groups(user_id):
        if (g.get("subject") or "").strip().title() == want:
            lv = g.get("level")
            if lv is not None and str(lv).strip():
                return str(lv).strip()
    return None


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
    ensure_subject_dcoin_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if not _ensure_subject_dcoins_ready(cur, context="get_leaderboard_count_by_group"):
            return 0
        cur.execute(
            '''
            SELECT COUNT(*) as count FROM (
                SELECT u.id
                FROM users u
                LEFT JOIN user_subject_dcoins sd ON sd.user_id = u.id
                WHERE u.group_id=? AND u.login_type IN (1,2)
                GROUP BY u.id
                HAVING COALESCE(SUM(sd.balance), 0) > 0
            ) t
            ''',
            (group_id,),
        )
        row = cur.fetchone()
        return row['count'] if row else 0
    except Exception as e:
        if _is_missing_subject_dcoins_error(e):
            logger.exception("Leaderboard fallback: group count table missing")
            return 0
        raise
    finally:
        conn.close()


def get_user_rating_info(user_id):
    """Foydalanuvchining reyting ma'lumotlarini olish"""
    conn = get_conn()
    cur = conn.cursor()
    
    ensure_subject_dcoin_schema()
    # Global rank by total subject balances
    cur.execute(
        """
        WITH totals AS (
            SELECT u.id, COALESCE(SUM(sd.balance), 0) as total
            FROM users u
            LEFT JOIN user_subject_dcoins sd ON sd.user_id=u.id
            GROUP BY u.id
        )
        SELECT COUNT(*) + 1 as global_rank
        FROM totals
        WHERE total > COALESCE((SELECT total FROM totals WHERE id=?), 0)
        """,
        (user_id,),
    )
    global_rank_row = cur.fetchone()
    global_rank = global_rank_row['global_rank'] if global_rank_row else None
    
    # Group rank
    cur.execute(
        """
        WITH totals AS (
            SELECT u.id, u.group_id, COALESCE(SUM(sd.balance), 0) as total
            FROM users u
            LEFT JOIN user_subject_dcoins sd ON sd.user_id=u.id
            GROUP BY u.id, u.group_id
        )
        SELECT COUNT(*) + 1 as group_rank
        FROM totals
        WHERE group_id = (SELECT group_id FROM users WHERE id = ?)
          AND total > COALESCE((SELECT total FROM totals WHERE id = ?), 0)
        """,
        (user_id, user_id),
    )
    group_rank_row = cur.fetchone()
    group_rank = group_rank_row['group_rank'] if group_rank_row else None
    
    conn.close()
    
    return {
        'global_rank': global_rank,
        'group_rank': group_rank
    }


def get_rating_leaderboard(user_id, period, subject: str | None = None):
    """Reyting jadvalini olish (daily, weekly, monthly)"""
    conn = get_conn()
    cur = conn.cursor()
    
    subj = (subject or "").strip().title()
    subject_filter = ""
    subject_params: tuple = ()
    if subj:
        subject_filter = " AND dh.subject = ? "
        subject_params = (subj,)

    if period == 'daily':
        # Kunlik reyting - bugungi kun olgan D'coinlar
        cur.execute("""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(CASE 
                       WHEN DATE(dh.created_at) = CURRENT_DATE THEN dh.dcoin_change 
                       ELSE 0 END), 0) as score,
                   COALESCE(SUM(CASE 
                       WHEN DATE(dh.created_at) = CURRENT_DATE THEN dh.dcoin_change 
                       ELSE 0 END), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE DATE(dh.created_at) = CURRENT_DATE
            {subject_filter}
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """, subject_params)
    elif period == 'weekly':
        # Haftalik reyting - oxirgi 7 kun
        cur.execute(f"""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(dh.dcoin_change), 0) as score,
                   COALESCE(SUM(dh.dcoin_change), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE dh.created_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
            {subject_filter}
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """, subject_params)
    elif period == 'monthly':
        # Oylik reyting - oxirgi 30 kun
        cur.execute(f"""
            SELECT u.first_name, u.last_name, 
                   COALESCE(SUM(dh.dcoin_change), 0) as score,
                   COALESCE(SUM(dh.dcoin_change), 0) as dcoin
            FROM users u
            JOIN diamond_history dh ON u.id = dh.user_id
            WHERE dh.created_at >= (CURRENT_TIMESTAMP - INTERVAL '30 days')
            {subject_filter}
            AND u.login_type IN (1, 2)
            GROUP BY u.id
            ORDER BY score DESC
            LIMIT 10
        """, subject_params)
    else:
        conn.close()
        return []
    
    rows = cur.fetchall()
    conn.close()
    
    leaderboard = []
    for row in rows:
        name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
        score = row['score'] or 0
        dcoin = row['dcoin'] or 0
        
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
    is_anon_bool = bool(is_anonymous)
    anon_int = 1 if is_anon_bool else 0
    anon_bool = is_anon_bool

    # Best-effort: detect column type in PostgreSQL to avoid psycopg type mismatch.
    # (Some deployments have feedback.is_anonymous as INTEGER, others as BOOLEAN.)
    inferred_use_bool = None
    try:
        cur.execute(
            "SELECT data_type FROM information_schema.columns WHERE table_name='feedback' AND column_name='is_anonymous'",
        )
        row = cur.fetchone()
        if row and row.get("data_type"):
            inferred_use_bool = str(row["data_type"]).lower() in ("boolean", "bool")
    except Exception:
        inferred_use_bool = None

    try:
        # Primary path: choose value type based on inferred column type.
        anon_param = anon_bool if inferred_use_bool else anon_int
        cur.execute('''
            INSERT INTO feedback (user_id, feedback_text, is_anonymous, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, feedback_text, anon_param, now))
    except Exception:
        # Fallback for BOOLEAN-backed schemas.
        conn.rollback()
        anon_param = anon_int if inferred_use_bool else anon_bool
        cur.execute('''
            INSERT INTO feedback (user_id, feedback_text, is_anonymous, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, feedback_text, anon_param, now))

    conn.commit()
    conn.close()


def get_student_monthly_stats(user_id):
    """Get student's monthly statistics"""
    # Make sure we have a compatible schema for existing databases.
    # Particularly: Postgres legacy DBs may store `grammar_attempts.last_attempt_at` as TEXT.
    ensure_grammar_attempts_table()
    conn = get_conn()
    cur = conn.cursor()
    
    # Get current month start
    cur.execute("SELECT DATE_TRUNC('month', CURRENT_TIMESTAMP) as month_start")
    month_start = cur.fetchone()['month_start']
    
    # === WORDS LEARNED — tuzatilgan versiya ===
    cur.execute('''
        SELECT COUNT(*) as words_learned
        FROM diamond_history 
        WHERE user_id = ? 
          AND dcoin_change > 0 
          AND created_at >= ?
    ''', (user_id, month_start))
    
    words_result = cur.fetchone()
    words_learned = words_result['words_learned'] if words_result else 0
    
    # Count grammar topics completed
    if _is_postgres_enabled():
        # Postgres: `last_attempt_at` might be TEXT in legacy DBs.
        # Cast only values that look like a datetime prefix to avoid runtime errors.
        cur.execute('''
            SELECT COUNT(DISTINCT topic_id) as topics_completed
            FROM grammar_attempts ga
            WHERE ga.user_id = ?
              AND (
                CASE
                  WHEN ga.last_attempt_at IS NULL THEN NULL
                  WHEN ga.last_attempt_at::text = '' THEN NULL
                  WHEN ga.last_attempt_at::text ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}' THEN ga.last_attempt_at::timestamptz
                  ELSE NULL
                END
              ) >= ?
        ''', (user_id, month_start))
    else:
        # SQLite: keep the original comparison.
        cur.execute('''
            SELECT COUNT(DISTINCT topic_id) as topics_completed
            FROM grammar_attempts ga
            WHERE ga.user_id = ?
              AND ga.last_attempt_at >= ?
        ''', (user_id, month_start))
    
    topics_result = cur.fetchone()
    topics_completed = topics_result['topics_completed'] if topics_result else 0
    
    # Count tests taken
    try:
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
    except Exception:
        # If legacy schema misses columns, keep progress safe.
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

    # Defensive insert: some legacy DBs can miss some columns.
    # We build INSERT dynamically based on existing columns to avoid runtime crashes.
    existing_cols: set[str] = set()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='test_history'
                """
            )
            existing_cols = {str(r["column_name"]) for r in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(test_history)")
            # sqlite rows: (cid, name, type, notnull, dflt_value, pk)
            existing_cols = {str(r["name"]) for r in cur.fetchall()}
    except Exception:
        # If introspection fails, assume full schema and let DB raise if it's truly incompatible.
        existing_cols = set()

    # Keep column/value order consistent with table schema.
    insert_cols: list[str] = ["user_id", "test_type"]
    values: list[Any] = [user_id, test_type]

    if "topic_id" in existing_cols:
        insert_cols.append("topic_id")
        values.append(topic_id)

    if "correct_count" in existing_cols:
        insert_cols.append("correct_count")
        values.append(correct_count)
    if "wrong_count" in existing_cols:
        insert_cols.append("wrong_count")
        values.append(wrong_count)
    if "skipped_count" in existing_cols:
        insert_cols.append("skipped_count")
        values.append(skipped_count)

    insert_cols.append("created_at")
    values.append(now)

    placeholders = ", ".join(["?"] * len(insert_cols))
    cols_sql = ", ".join(insert_cols)

    cur.execute(
        f"INSERT INTO test_history ({cols_sql}) VALUES ({placeholders})",
        tuple(values),
    )
    
    conn.commit()
    conn.close()


def ensure_duel_matchmaking_schema() -> None:
    """Create persistent duel queue/session tables for both SQLite and PostgreSQL."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS open_duel_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    mode TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    level TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    required_players INTEGER NOT NULL,
                    created_by_user_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_duel_match_participants (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    team_no INTEGER NOT NULL DEFAULT 1,
                    paid_fee INTEGER NOT NULL DEFAULT 1,
                    refunded_fee INTEGER NOT NULL DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result_correct INTEGER NOT NULL DEFAULT 0,
                    result_wrong INTEGER NOT NULL DEFAULT 0,
                    result_unanswered INTEGER NOT NULL DEFAULT 0,
                    is_winner INTEGER NOT NULL DEFAULT 0,
                    last_opponent_user_id BIGINT,
                    UNIQUE(session_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_duel_revenge_tokens (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    opponent_user_id BIGINT NOT NULL,
                    mode TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS open_duel_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    level TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    required_players INTEGER NOT NULL,
                    created_by_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_duel_match_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    team_no INTEGER NOT NULL DEFAULT 1,
                    paid_fee INTEGER NOT NULL DEFAULT 1,
                    refunded_fee INTEGER NOT NULL DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result_correct INTEGER NOT NULL DEFAULT 0,
                    result_wrong INTEGER NOT NULL DEFAULT 0,
                    result_unanswered INTEGER NOT NULL DEFAULT 0,
                    is_winner INTEGER NOT NULL DEFAULT 0,
                    last_opponent_user_id INTEGER,
                    UNIQUE(session_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_duel_revenge_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    opponent_user_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_duel_sessions_open ON open_duel_sessions(mode, subject, level, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_duel_participants_session ON arena_duel_match_participants(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_duel_revenge_user ON arena_duel_revenge_tokens(user_id, used, expires_at)")
        conn.commit()
    finally:
        conn.close()


def create_duel_session(mode: str, subject: str, level: str, created_by_user_id: int, required_players: int, expires_at: str) -> int:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO open_duel_sessions(mode, subject, level, status, required_players, created_by_user_id, expires_at)
            VALUES (?, ?, ?, 'open', ?, ?, ?)
            RETURNING id
            """,
            (mode, subject, level, int(required_players), int(created_by_user_id), expires_at),
        )
        sid = int(cur.fetchone()["id"])
        conn.commit()
        return sid
    finally:
        conn.close()


def get_open_duel_session(mode: str, subject: str, level: str) -> dict | None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM open_duel_sessions
            WHERE mode=? AND subject=? AND level=? AND status='open'
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            """,
            (mode, subject, level),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_open_duel_sessions_for_mode(mode: str) -> list[dict]:
    """All open duel sessions for a mode (any subject/level), oldest first."""
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM open_duel_sessions
            WHERE mode=? AND status='open'
            ORDER BY created_at ASC, id ASC
            """,
            (mode,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def cleanup_student_subject_side_effects(user_id: int, subject: str) -> None:
    """
    After removing a subject from a student, clear per-subject data that would be stale.
    Safe for SQLite/Postgres; ignores missing tables/columns.
    """
    uid = int(user_id)
    subj = (subject or "").strip()
    if not subj:
        return
    subj_title = subj.title()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM user_subject_dcoins WHERE user_id=? AND LOWER(subject)=LOWER(?)", (uid, subj))
        cur.execute("DELETE FROM test_results WHERE user_id=? AND LOWER(subject)=LOWER(?)", (uid, subj))
        cur.execute(
            "DELETE FROM words WHERE added_by=? AND LOWER(subject)=LOWER(?)",
            (uid, subj),
        )
        cur.execute(
            "DELETE FROM diamond_history WHERE user_id=? AND LOWER(COALESCE(subject,''))=LOWER(?)",
            (uid, subj),
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def ensure_diamondvoy_history_table() -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS diamondvoy_history (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT,
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    subject TEXT,
                    bot_scope TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS diamondvoy_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    subject TEXT,
                    bot_scope TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def log_diamondvoy_query(
    user_id: int | None,
    query: str,
    response: str | None,
    *,
    subject: str | None = None,
    bot_scope: str | None = None,
) -> None:
    ensure_diamondvoy_history_table()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO diamondvoy_history (user_id, query_text, response_text, subject, bot_scope)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, (query or "")[:8000], (response or "")[:16000] if response else None, subject, bot_scope),
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def delete_diamondvoy_history_older_than_days(days: int = 30) -> int:
    ensure_diamondvoy_history_table()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cutoff = datetime.utcnow() - timedelta(days=int(days))
        cur.execute("DELETE FROM diamondvoy_history WHERE created_at < ?", (cutoff,))
        n = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
        return n
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return 0
    finally:
        conn.close()


def get_duel_session(session_id: int) -> dict | None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM open_duel_sessions WHERE id=?", (int(session_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def join_duel_session(session_id: int, user_id: int, chat_id: int, team_no: int = 1) -> bool:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_duel_match_participants(session_id, user_id, chat_id, team_no)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (session_id, user_id) DO NOTHING
            """,
            (int(session_id), int(user_id), int(chat_id), int(team_no)),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def count_duel_participants(session_id: int) -> int:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM arena_duel_match_participants WHERE session_id=?", (int(session_id),))
        row = cur.fetchone()
        return int((row or {}).get("cnt") or 0)
    finally:
        conn.close()


def list_duel_participants(session_id: int) -> list[dict]:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT *
            FROM arena_duel_match_participants
            WHERE session_id=?
            ORDER BY joined_at ASC, id ASC
            """,
            (int(session_id),),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def mark_duel_session_started(session_id: int) -> None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE open_duel_sessions SET status='running', started_at=CURRENT_TIMESTAMP WHERE id=?",
            (int(session_id),),
        )
        conn.commit()
    finally:
        conn.close()


def mark_duel_session_finished(session_id: int) -> None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE open_duel_sessions SET status='finished', finished_at=CURRENT_TIMESTAMP WHERE id=?",
            (int(session_id),),
        )
        conn.commit()
    finally:
        conn.close()


def cancel_expired_open_duel_sessions(now_iso: str) -> list[dict]:
    """Cancel expired sessions and return participants who must be refunded."""
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id FROM open_duel_sessions
            WHERE status='open' AND expires_at IS NOT NULL AND expires_at <= ?
            """,
            (now_iso,),
        )
        sids = [int(r["id"]) for r in cur.fetchall()]
        if not sids:
            return []
        refunds: list[dict] = []
        for sid in sids:
            cur.execute("UPDATE open_duel_sessions SET status='canceled', finished_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
            cur.execute(
                """
                SELECT session_id, user_id, chat_id
                FROM arena_duel_match_participants
                WHERE session_id=? AND refunded_fee=0
                """,
                (sid,),
            )
            refunds.extend([dict(r) for r in cur.fetchall()])
        conn.commit()
        return refunds
    finally:
        conn.close()


def mark_duel_participant_refunded(session_id: int, user_id: int) -> None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE arena_duel_match_participants SET refunded_fee=1 WHERE session_id=? AND user_id=?",
            (int(session_id), int(user_id)),
        )
        conn.commit()
    finally:
        conn.close()


def save_duel_participant_result(
    session_id: int,
    user_id: int,
    *,
    correct: int,
    wrong: int,
    unanswered: int,
    is_winner: bool,
    last_opponent_user_id: int | None = None,
) -> None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE arena_duel_match_participants
            SET result_correct=?, result_wrong=?, result_unanswered=?, is_winner=?, last_opponent_user_id=?
            WHERE session_id=? AND user_id=?
            """,
            (int(correct), int(wrong), int(unanswered), 1 if is_winner else 0, last_opponent_user_id, int(session_id), int(user_id)),
        )
        conn.commit()
    finally:
        conn.close()


def create_revenge_token(user_id: int, opponent_user_id: int, mode: str, subject: str, expires_at_iso: str) -> None:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_duel_revenge_tokens(user_id, opponent_user_id, mode, subject, expires_at, used)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (int(user_id), int(opponent_user_id), mode, subject, expires_at_iso),
        )
        conn.commit()
    finally:
        conn.close()


def consume_valid_revenge_token(user_id: int, opponent_user_id: int, mode: str, subject: str, now_iso: str) -> bool:
    ensure_duel_matchmaking_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id
            FROM arena_duel_revenge_tokens
            WHERE user_id=? AND opponent_user_id=? AND mode=? AND subject=? AND used=0 AND expires_at > ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id), int(opponent_user_id), mode, subject, now_iso),
        )
        row = cur.fetchone()
        if not row:
            return False
        cur.execute("UPDATE arena_duel_revenge_tokens SET used=1 WHERE id=?", (int(row["id"]),))
        conn.commit()
        return True
    finally:
        conn.close()


# --- Scheduled Daily/Boss arena, duel daily quota, streak (D'coin extras) ---

def ensure_arena_extras_schema() -> None:
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_scheduled_runs (
                    id BIGSERIAL PRIMARY KEY,
                    run_kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    run_date TEXT NOT NULL,
                    start_hhmm TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    min_players INTEGER NOT NULL DEFAULT 4,
                    max_players INTEGER NOT NULL DEFAULT 15,
                    current_stage INTEGER NOT NULL DEFAULT 0,
                    questions_generated_at TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    questions_promoted INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_kind, subject, run_date, start_hhmm)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_participants (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fee_charged INTEGER NOT NULL DEFAULT 0,
                    eliminated_after_stage INTEGER,
                    stage_scores_json TEXT,
                    UNIQUE(run_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_questions (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_answers (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL DEFAULT 0,
                    is_unanswered INTEGER NOT NULL DEFAULT 0,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, user_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_daily_usage (
                    user_id BIGINT NOT NULL,
                    usage_date TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    plays INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, usage_date, mode)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_dcoin_streak (
                    user_id BIGINT PRIMARY KEY,
                    consecutive_qualifying_days INTEGER NOT NULL DEFAULT 0,
                    last_qualify_date TEXT,
                    win_streak INTEGER NOT NULL DEFAULT 0,
                    last_win_date TEXT,
                    cycle_day_index INTEGER NOT NULL DEFAULT 0,
                    last_cycle_award_date TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_season_notify (
                    subject TEXT NOT NULL,
                    season_ym TEXT NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(subject, season_ym)
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_scheduled_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    run_date TEXT NOT NULL,
                    start_hhmm TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    min_players INTEGER NOT NULL DEFAULT 4,
                    max_players INTEGER NOT NULL DEFAULT 15,
                    current_stage INTEGER NOT NULL DEFAULT 0,
                    questions_generated_at TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    questions_promoted INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_kind, subject, run_date, start_hhmm)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fee_charged INTEGER NOT NULL DEFAULT 0,
                    eliminated_after_stage INTEGER,
                    stage_scores_json TEXT,
                    UNIQUE(run_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_run_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    is_correct INTEGER NOT NULL DEFAULT 0,
                    is_unanswered INTEGER NOT NULL DEFAULT 0,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, user_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_daily_usage (
                    user_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    plays INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, usage_date, mode)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_dcoin_streak (
                    user_id INTEGER PRIMARY KEY,
                    consecutive_qualifying_days INTEGER NOT NULL DEFAULT 0,
                    last_qualify_date TEXT,
                    win_streak INTEGER NOT NULL DEFAULT 0,
                    last_win_date TEXT,
                    cycle_day_index INTEGER NOT NULL DEFAULT 0,
                    last_cycle_award_date TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_season_notify (
                    subject TEXT NOT NULL,
                    season_ym TEXT NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(subject, season_ym)
                )
                """
            )
        conn.commit()
        # Migration for older DBs: add `is_unanswered` if it was missing.
        try:
            _ensure_arena_run_answers_is_unanswered_column()
        except Exception:
            pass
        # NOTE:
        # Do NOT auto-migrate `arena_scheduled_runs.questions_promoted` here.
        # It was causing startup hangs in some Postgres deployments.
        # We will handle it inside the promotion scheduler at runtime.
    finally:
        conn.close()


def _ensure_arena_run_answers_is_unanswered_column() -> None:
    """
    Best-effort migration: add `is_unanswered` column if it exists as an older schema.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        try:
            # Postgres supports IF NOT EXISTS; sqlite might not.
            cur.execute("ALTER TABLE arena_run_answers ADD COLUMN IF NOT EXISTS is_unanswered INTEGER NOT NULL DEFAULT 0")
        except Exception:
            try:
                cur.execute("ALTER TABLE arena_run_answers ADD COLUMN is_unanswered INTEGER NOT NULL DEFAULT 0")
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()


def _ensure_arena_scheduled_runs_questions_promoted_column() -> None:
    """
    Best-effort migration: add `arena_scheduled_runs.questions_promoted` if missing.
    Uses information_schema check to avoid relying on CREATE TABLE IF NOT EXISTS
    for already-existing deployments.
    """
    if not _is_postgres_enabled():
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Keep ALTER fast; avoid scheduler deadlocks due to locks.
        try:
            cur.execute("SET LOCAL statement_timeout = '10s'")
        except Exception:
            pass

        # Check column existence in Postgres system catalog.
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='arena_scheduled_runs'
              AND column_name='questions_promoted'
            LIMIT 1
            """
        )
        exists = cur.fetchone() is not None
        if exists:
            return

        # Add the column with default 0 so existing rows are safe.
        try:
            cur.execute(
                "ALTER TABLE arena_scheduled_runs ADD COLUMN IF NOT EXISTS questions_promoted INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            cur.execute(
                "ALTER TABLE arena_scheduled_runs ADD COLUMN questions_promoted INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()
    finally:
        conn.close()


def get_or_create_scheduled_arena_run(
    *,
    run_kind: str,
    subject: str,
    run_date: str,
    start_hhmm: str,
    min_players: int = 4,
    max_players: int = 15,
) -> int:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id FROM arena_scheduled_runs
            WHERE run_kind=? AND subject=? AND run_date=? AND start_hhmm=?
            """,
            (run_kind, subject, run_date, start_hhmm),
        )
        row = cur.fetchone()
        if row:
            return int(row["id"])
        cur.execute(
            """
            INSERT INTO arena_scheduled_runs(run_kind, subject, run_date, start_hhmm, min_players, max_players, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            RETURNING id
            """,
            (run_kind, subject, run_date, start_hhmm, int(min_players), int(max_players)),
        )
        rid = int(cur.fetchone()["id"])
        conn.commit()
        return rid
    finally:
        conn.close()


def get_scheduled_arena_run(run_id: int) -> dict | None:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM arena_scheduled_runs WHERE id=?", (int(run_id),))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_scheduled_arena_run(run_id: int, **kwargs: Any) -> None:
    ensure_arena_extras_schema()
    if not kwargs:
        return
    keys = [k for k in kwargs if kwargs[k] is not None]
    if not keys:
        return
    sets = ", ".join(f"{k}=?" for k in keys)
    vals = [kwargs[k] for k in keys] + [int(run_id)]
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE arena_scheduled_runs SET {sets} WHERE id=?",
            tuple(vals),
        )
        conn.commit()
    finally:
        conn.close()


def register_arena_run_participant(run_id: int, user_id: int, chat_id: int) -> bool:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_run_participants(run_id, user_id, chat_id)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id, user_id) DO NOTHING
            """,
            (int(run_id), int(user_id), int(chat_id)),
        )
        conn.commit()
        return (cur.rowcount or 0) > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def count_arena_run_participants(run_id: int) -> int:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) as c FROM arena_run_participants WHERE run_id=?",
            (int(run_id),),
        )
        return int((cur.fetchone() or {}).get("c") or 0)
    finally:
        conn.close()


def list_arena_run_participants(run_id: int) -> list[dict]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM arena_run_participants WHERE run_id=? ORDER BY id ASC",
            (int(run_id),),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def delete_arena_run_questions(run_id: int) -> None:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM arena_run_answers WHERE run_id=?", (int(run_id),))
        cur.execute("DELETE FROM arena_run_questions WHERE run_id=?", (int(run_id),))
        conn.commit()
    finally:
        conn.close()


def ensure_arena_run_questions_user_id_column() -> None:
    """Boss pool: per-user assignment; daily rows keep user_id NULL."""
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                "ALTER TABLE arena_run_questions ADD COLUMN IF NOT EXISTS user_id BIGINT"
            )
        else:
            try:
                cur.execute("ALTER TABLE arena_run_questions ADD COLUMN user_id INTEGER")
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()


def ensure_arena_questions_tmp_schema() -> None:
    """
    Runtime temporary question pools for delayed promotion to `daily_tests_bank`.

    - Daily arena: `arena_daily_questions_tmp`
    - Boss arena: `arena_boss_questions_tmp`
    - Duel: `duel_1v1_questions_tmp`, `duel_5v5_questions_tmp`
    - Group arena: `arena_group_questions_tmp`
    """
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_daily_questions_tmp (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_boss_questions_tmp (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_1v1_questions_tmp (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_5v5_questions_tmp (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_group_questions_tmp (
                    id BIGSERIAL PRIMARY KEY,
                    session_id BIGINT NOT NULL,
                    q_index INTEGER NOT NULL,
                    bank_question_id BIGINT NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_daily_questions_tmp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_boss_questions_tmp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    stage INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(run_id, stage, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_1v1_questions_tmp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duel_5v5_questions_tmp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_group_questions_tmp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    q_index INTEGER NOT NULL,
                    bank_question_id INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_at TIMESTAMP,
                    UNIQUE(session_id, q_index)
                )
                """
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def insert_arena_run_question(
    run_id: int,
    stage: int,
    q_index: int,
    payload_json: str,
    user_id: Optional[int] = None,
) -> None:
    ensure_arena_run_questions_user_id_column()
    ensure_arena_extras_schema()
    ensure_arena_questions_tmp_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO arena_run_questions(run_id, stage, q_index, payload_json, user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(run_id), int(stage), int(q_index), payload_json, user_id),
        )
        # Also write the same payload into type-specific tmp tables for delayed promotion.
        try:
            cache = getattr(insert_arena_run_question, "_run_kind_cache", None)
            if cache is None:
                cache = {}
                setattr(insert_arena_run_question, "_run_kind_cache", cache)

            run_kind = cache.get(int(run_id))
            if run_kind is None:
                cur.execute("SELECT run_kind FROM arena_scheduled_runs WHERE id=?", (int(run_id),))
                rr = cur.fetchone()
                run_kind = (rr or {}).get("run_kind") if rr else None
                cache[int(run_id)] = run_kind

            if run_kind == "daily":
                cur.execute(
                    """
                    INSERT INTO arena_daily_questions_tmp(run_id, stage, q_index, payload_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (run_id, stage, q_index) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        promoted_at=NULL
                    """,
                    (int(run_id), int(stage), int(q_index), payload_json),
                )
            elif run_kind == "boss":
                cur.execute(
                    """
                    INSERT INTO arena_boss_questions_tmp(run_id, stage, q_index, payload_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (run_id, stage, q_index) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        promoted_at=NULL
                    """,
                    (int(run_id), int(stage), int(q_index), payload_json),
                )
        except Exception:
            # Tmp promotion is best-effort; never break the running event.
            pass

        conn.commit()
    finally:
        conn.close()


def insert_duel_questions_tmp(
    mode: str,
    session_id: int,
    questions: list[dict],
    *,
    level: str | None = None,
) -> None:
    """Insert duel runtime questions into the correct tmp pool table."""
    ensure_arena_questions_tmp_schema()
    if not questions:
        return

    import json

    mode = (mode or "").strip().lower()
    if mode == "1v1":
        table = "duel_1v1_questions_tmp"
    elif mode == "5v5":
        table = "duel_5v5_questions_tmp"
    else:
        return

    conn = get_conn()
    cur = conn.cursor()
    try:
        rows = []
        for i, q in enumerate(questions, start=1):
            payload = {
                "question": str(q.get("question") or "").strip(),
                "option_a": str(q.get("option_a") or "").strip(),
                "option_b": str(q.get("option_b") or "").strip(),
                "option_c": str(q.get("option_c") or "").strip(),
                "option_d": str(q.get("option_d") or "").strip(),
                "correct_option_index": int(q.get("correct_option_index") or 1),
                "level": str(level or "").strip() or None,
                "created_by": int(q.get("created_by") or 0),
                "question_type": q.get("question_type"),
            }
            rows.append((int(session_id), int(i), json.dumps(payload, ensure_ascii=False)))

        cur.executemany(
            f"""
            INSERT INTO {table}(session_id, q_index, payload_json)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, q_index) DO UPDATE SET
                payload_json=excluded.payload_json,
                promoted_at=NULL
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def fetch_arena_run_questions(
    run_id: int,
    stage: int | None = None,
    user_id: Optional[int] = None,
) -> list[dict]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if stage is not None and user_id is not None:
            cur.execute(
                """
                SELECT * FROM arena_run_questions
                WHERE run_id=? AND stage=? AND user_id=?
                ORDER BY q_index ASC
                """,
                (int(run_id), int(stage), int(user_id)),
            )
        elif stage is not None:
            cur.execute(
                """
                SELECT * FROM arena_run_questions
                WHERE run_id=? AND stage=? AND user_id IS NULL
                ORDER BY q_index ASC
                """,
                (int(run_id), int(stage)),
            )
        else:
            cur.execute(
                "SELECT * FROM arena_run_questions WHERE run_id=? ORDER BY stage ASC, q_index ASC",
                (int(run_id),),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def record_arena_run_answer(
    run_id: int,
    user_id: int,
    stage: int,
    q_index: int,
    is_correct: int,
    is_unanswered: int = 0,
) -> None:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            DELETE FROM arena_run_answers
            WHERE run_id=? AND user_id=? AND stage=? AND q_index=?
            """,
            (int(run_id), int(user_id), int(stage), int(q_index)),
        )
        cur.execute(
            """
            INSERT INTO arena_run_answers(run_id, user_id, stage, q_index, is_correct, is_unanswered)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(run_id), int(user_id), int(stage), int(q_index), int(is_correct), int(is_unanswered)),
        )
        conn.commit()
    finally:
        conn.close()


def get_arena_run_user_stage_answer_stats(
    *,
    run_id: int,
    user_id: int,
    stage: int,
) -> dict[str, int]:
    """
    Returns {correct, wrong, unanswered} for a single (run_id, user_id, stage).
    """
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END), 0) AS correct,
                COALESCE(SUM(CASE WHEN is_unanswered=1 THEN 1 ELSE 0 END), 0) AS unanswered,
                COALESCE(SUM(CASE WHEN is_correct=0 AND is_unanswered=0 THEN 1 ELSE 0 END), 0) AS wrong
            FROM arena_run_answers
            WHERE run_id=? AND user_id=? AND stage=?
            """,
            (int(run_id), int(user_id), int(stage)),
        )
        row = cur.fetchone() or {}
        return {
            "correct": int(row.get("correct") or 0),
            "wrong": int(row.get("wrong") or 0),
            "unanswered": int(row.get("unanswered") or 0),
        }
    finally:
        conn.close()


def list_arena_run_users_stage_answer_stats(
    *,
    run_id: int,
    stage: int,
) -> list[dict]:
    """
    Returns rows with {user_id, correct, wrong, unanswered} for a given stage.
    """
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                user_id,
                COALESCE(SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END), 0) AS correct,
                COALESCE(SUM(CASE WHEN is_unanswered=1 THEN 1 ELSE 0 END), 0) AS unanswered,
                COALESCE(SUM(CASE WHEN is_correct=0 AND is_unanswered=0 THEN 1 ELSE 0 END), 0) AS wrong
            FROM arena_run_answers
            WHERE run_id=? AND stage=?
            GROUP BY user_id
            ORDER BY user_id ASC
            """,
            (int(run_id), int(stage)),
        )
        rows = cur.fetchall() or []
        return [dict(r) for r in rows]
    finally:
        conn.close()


def leaderboard_users_through_stage(run_id: int, through_stage: int) -> list[tuple[int, int]]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT user_id, COALESCE(SUM(is_correct), 0) AS s
            FROM arena_run_answers
            WHERE run_id=? AND stage <= ?
            GROUP BY user_id
            ORDER BY s DESC, user_id ASC
            """,
            (int(run_id), int(through_stage)),
        )
        return [(int(r["user_id"]), int(r["s"])) for r in cur.fetchall()]
    finally:
        conn.close()


def leaderboard_users_single_stage(run_id: int, stage: int) -> list[tuple[int, int]]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT user_id, COALESCE(SUM(is_correct), 0) AS s
            FROM arena_run_answers
            WHERE run_id=? AND stage=?
            GROUP BY user_id
            ORDER BY s DESC, user_id ASC
            """,
            (int(run_id), int(stage)),
        )
        return [(int(r["user_id"]), int(r["s"])) for r in cur.fetchall()]
    finally:
        conn.close()


def mark_participant_eliminated(run_id: int, user_id: int, after_stage: int) -> None:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE arena_run_participants
            SET eliminated_after_stage=?
            WHERE run_id=? AND user_id=?
            """,
            (int(after_stage), int(run_id), int(user_id)),
        )
        conn.commit()
    finally:
        conn.close()


def list_non_eliminated_participants(run_id: int) -> list[dict]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT * FROM arena_run_participants
            WHERE run_id=? AND eliminated_after_stage IS NULL
            ORDER BY id ASC
            """,
            (int(run_id),),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def boss_aggregate_stats(run_id: int) -> tuple[int, int]:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS c, COALESCE(SUM(is_correct), 0) AS s
            FROM arena_run_answers
            WHERE run_id=?
            """,
            (int(run_id),),
        )
        row = cur.fetchone() or {}
        return int(row.get("c") or 0), int(row.get("s") or 0)
    finally:
        conn.close()


def assign_boss_question_pool_to_user(run_id: int, user_id: int, count: int = 3) -> list[dict]:
    ensure_arena_run_questions_user_id_column()
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE arena_run_questions SET user_id=?
            WHERE rowid IN (
                SELECT rowid FROM arena_run_questions
                WHERE run_id=? AND user_id IS NULL AND stage=0
                ORDER BY q_index ASC
                LIMIT ?
            )
            """,
            (int(user_id), int(run_id), int(count)),
        )
        conn.commit()
        cur.execute(
            """
            SELECT * FROM arena_run_questions
            WHERE run_id=? AND user_id=? AND stage=0
            ORDER BY q_index ASC
            """,
            (int(run_id), int(user_id)),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def assign_boss_question_pool_to_user_pg(run_id: int, user_id: int, count: int = 3) -> list[dict]:
    ensure_arena_run_questions_user_id_column()
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE arena_run_questions AS q SET user_id=?
            FROM (
                SELECT id FROM arena_run_questions
                WHERE run_id=? AND user_id IS NULL AND stage=0
                ORDER BY q_index ASC
                LIMIT ?
            ) AS sub
            WHERE q.id = sub.id
            """,
            (int(user_id), int(run_id), int(count)),
        )
        conn.commit()
        cur.execute(
            """
            SELECT * FROM arena_run_questions
            WHERE run_id=? AND user_id=? AND stage=0
            ORDER BY q_index ASC
            """,
            (int(run_id), int(user_id)),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def assign_boss_question_pool_to_user_auto(run_id: int, user_id: int, count: int = 3) -> list[dict]:
    if _is_postgres_enabled():
        return assign_boss_question_pool_to_user_pg(run_id, user_id, count)
    return assign_boss_question_pool_to_user(run_id, user_id, count)


def sum_user_boss_stage_answers(run_id: int, user_id: int) -> int:
    """Correct count for boss (stage=0)."""
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COALESCE(SUM(is_correct), 0) AS s
            FROM arena_run_answers
            WHERE run_id=? AND user_id=? AND stage=0
            """,
            (int(run_id), int(user_id)),
        )
        row = cur.fetchone() or {}
        return int(row.get("s") or 0)
    finally:
        conn.close()


def is_arena_run_participant(run_id: int, user_id: int) -> bool:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM arena_run_participants WHERE run_id=? AND user_id=? LIMIT 1",
            (int(run_id), int(user_id)),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def duel_plays_today(user_id: int, mode: str, usage_date: str) -> int:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT plays FROM duel_daily_usage
            WHERE user_id=? AND usage_date=? AND mode=?
            """,
            (int(user_id), usage_date, mode),
        )
        row = cur.fetchone()
        return int((row or {}).get("plays") or 0)
    finally:
        conn.close()


def increment_duel_daily_usage(user_id: int, mode: str, usage_date: str) -> int:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        uid, d, m = int(user_id), usage_date, mode
        cur.execute(
            "SELECT plays FROM duel_daily_usage WHERE user_id=? AND usage_date=? AND mode=?",
            (uid, d, m),
        )
        row = cur.fetchone()
        if row:
            n = int(row["plays"] or 0) + 1
            cur.execute(
                "UPDATE duel_daily_usage SET plays=? WHERE user_id=? AND usage_date=? AND mode=?",
                (n, uid, d, m),
            )
        else:
            n = 1
            cur.execute(
                "INSERT INTO duel_daily_usage(user_id, usage_date, mode, plays) VALUES (?, ?, ?, 1)",
                (uid, d, m),
            )
        conn.commit()
        return n
    finally:
        conn.close()


def can_start_duel_today(user_id: int, mode: str, usage_date: str, limit_per_day: int = 5) -> bool:
    return duel_plays_today(user_id, mode, usage_date) < int(limit_per_day)


def _get_or_create_streak_row(conn, cur, user_id: int) -> dict:
    cur.execute("SELECT * FROM user_dcoin_streak WHERE user_id=?", (int(user_id),))
    row = cur.fetchone()
    if row:
        return dict(row)
    cur.execute(
        "INSERT INTO user_dcoin_streak(user_id) VALUES (?)",
        (int(user_id),),
    )
    conn.commit()
    cur.execute("SELECT * FROM user_dcoin_streak WHERE user_id=?", (int(user_id),))
    return dict(cur.fetchone() or {})


def process_duel_win_streak_bonus(user_id: int, subject: str, win_date: str) -> None:
    """Har 5 ketma-ket duel g'alaba: +10 D'coin (bir marta)."""
    ensure_arena_extras_schema()
    subj = (subject or "English").strip().title() or "English"
    conn = get_conn()
    cur = conn.cursor()
    try:
        r = _get_or_create_streak_row(conn, cur, user_id)
        last = (r.get("last_win_date") or "").strip()
        ws = int(r.get("win_streak") or 0)
        if last == win_date:
            conn.close()
            return
        if last:
            from datetime import datetime, timedelta

            try:
                pd = datetime.strptime(last, "%Y-%m-%d").date()
                wd = datetime.strptime(win_date, "%Y-%m-%d").date()
                if (wd - pd).days != 1:
                    ws = 0
            except Exception:
                ws = 0
        ws += 1
        bonus = 0
        if ws >= 5:
            bonus = 10
            ws = 0
        cur.execute(
            """
            UPDATE user_dcoin_streak
            SET win_streak=?, last_win_date=?, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=?
            """,
            (ws, win_date, int(user_id)),
        )
        conn.commit()
        conn.close()
        if bonus > 0:
            add_dcoins(int(user_id), float(bonus), subj, change_type="streak_duel_5wins")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def process_daily_activity_streak_award(user_id: int, subject: str, qualify_date: str) -> None:
    """
    Kunlik 90%+ test yoki boshqa qualifying event: tsikl 1..30 kun, N-kunida +N D'coin.
    Ketma-ket emas bo'lsa tsikl 1 dan.
    """
    ensure_arena_extras_schema()
    subj = (subject or "English").strip().title() or "English"
    conn = get_conn()
    cur = conn.cursor()
    try:
        r = _get_or_create_streak_row(conn, cur, user_id)
        last = (r.get("last_qualify_date") or "").strip()
        cycle = int(r.get("consecutive_qualifying_days") or 0)
        if last == qualify_date:
            conn.close()
            return
        from datetime import datetime

        if last:
            try:
                pd = datetime.strptime(last, "%Y-%m-%d").date()
                qd = datetime.strptime(qualify_date, "%Y-%m-%d").date()
                if (qd - pd).days == 1:
                    if cycle >= 30:
                        cycle = 1
                    else:
                        cycle = cycle + 1
                else:
                    cycle = 1
            except Exception:
                cycle = 1
        else:
            cycle = 1
        award = float(cycle)
        cur.execute(
            """
            UPDATE user_dcoin_streak
            SET consecutive_qualifying_days=?,
                last_qualify_date=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=?
            """,
            (cycle, qualify_date, int(user_id)),
        )
        conn.commit()
        conn.close()
        if award > 0:
            add_dcoins(int(user_id), award, subj, change_type=f"streak_daily_cycle_{cycle}")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def season_leaderboard_top_users(subject: str, limit: int = 10) -> list[dict]:
    ensure_subject_dcoin_schema()
    subj = (subject or "").strip().title()
    return get_leaderboard_by_subject(subj, limit=limit, offset=0)


def mark_season_notified(subject: str, season_ym: str) -> bool:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        if _is_postgres_enabled():
            cur.execute(
                """
                INSERT INTO arena_season_notify(subject, season_ym)
                VALUES (?, ?)
                ON CONFLICT(subject, season_ym) DO NOTHING
                """,
                (subject, season_ym),
            )
        else:
            cur.execute(
                "INSERT OR IGNORE INTO arena_season_notify(subject, season_ym) VALUES (?, ?)",
                (subject, season_ym),
            )
        rc = cur.rowcount or 0
        conn.commit()
        return rc > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def was_season_notified(subject: str, season_ym: str) -> bool:
    ensure_arena_extras_schema()
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM arena_season_notify WHERE subject=? AND season_ym=? LIMIT 1",
            (subject, season_ym),
        )
        return bool(cur.fetchone())
    finally:
        conn.close()


