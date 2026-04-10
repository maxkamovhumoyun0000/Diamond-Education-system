import random
import re
import string
from datetime import datetime, timedelta
import logging
from typing import Callable, Awaitable, Any

from config import OTP_LENGTH, MAX_LOGIN_ATTEMPTS, DATABASE_URL
from db import create_user, verify_login as db_verify_login, activate_user as db_activate_user, get_user_by_login_id, get_user_by_telegram, update_user_telegram_id, get_conn
from logging_config import get_logger
from login_id_validator import generate_secure_login_id, validate_login_id, audit_login_id

logger = get_logger(__name__)
IS_POSTGRES = (DATABASE_URL or "").strip().lower().startswith(("postgresql://", "postgres://"))

def get_current_time():
    """Get current datetime"""
    return datetime.now()

def get_current_time_iso():
    """Get current datetime in ISO format"""
    return datetime.now().isoformat()

# Simple login state storage (moved from auth_middleware.py)
_login_states = {}

def get_login_state(telegram_id: str) -> dict:
    """Get login state for user (moved from auth_middleware.py)"""
    return _login_states.get(telegram_id, {})

def set_login_state(telegram_id: str, state: dict):
    """Set login state for user (moved from auth_middleware.py)"""
    _login_states[telegram_id] = state

def clear_login_state(telegram_id: str):
    """Clear login state for user (moved from auth_middleware.py)"""
    _login_states.pop(telegram_id, None)


def generate_login_id(login_type: int = 1, length=5, max_attempts=10):
    """
    Generate a secure login ID with validation
    
    Args:
        login_type: 1/2 for student, 3 for teacher
        length: length of random suffix
        max_attempts: maximum attempts to generate valid ID
    
    Returns:
        Valid login ID string
    """
    for attempt in range(max_attempts):
        candidate = generate_secure_login_id(login_type, length)
        validation = validate_login_id(candidate)
        
        if validation['valid']:
            logger.info(f"Generated valid login ID: {candidate}")
            return candidate
        else:
            logger.warning(f"Generated invalid login ID (attempt {attempt + 1}): {candidate} - {validation['errors']}")
    
    # If we couldn't generate a valid ID, try with longer suffix
    logger.error(f"Failed to generate valid login ID after {max_attempts} attempts, trying longer suffix")
    return generate_secure_login_id(login_type, length + 2)


def generate_password(length=6):
    # 6-character alphanumeric password
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def _correct_count_from_score(score: int) -> int:
    return max(0, int(score) // 10)


def english_cefr_code_from_score(score: int) -> str:
    """English placement: CEFR code from correct-count 0–50 (raw score 0–500, score//10)."""
    c = max(0, min(50, _correct_count_from_score(score)))
    if c <= 13:
        return "A1"
    if c <= 22:
        return "A2"
    if c <= 28:
        return "B1"
    if c <= 37:
        return "B1"
    if c <= 45:
        return "B2"
    return "C1"


def english_level_display_from_score(score: int) -> str:
    """English placement / UI: exact CEFR + name (two B1 bands)."""
    c = max(0, min(50, _correct_count_from_score(score)))
    if c <= 13:
        return "A1 (Beginner)"
    if c <= 22:
        return "A2 (Elementary)"
    if c <= 28:
        return "B1 (Pre Intermediate)"
    if c <= 37:
        return "B1 (Intermediate)"
    if c <= 45:
        return "B2 (Upper-Intermediate)"
    return "C1 (Advanced)"


def russian_level_display_from_score(score: int) -> str:
    """Russian placement: A1/A2/B1/B2 by correct-count 0-50."""
    c = max(0, min(50, _correct_count_from_score(score)))
    if c >= 49:
        return "Продвинутый средний (Б2)"
    if c >= 40:
        return "Средний (Б1)"
    if c >= 15:
        return "Базовый уровень (А2)"
    return "Начальный уровень (А1)"


def level_display_from_score(score: int, subject: str) -> str:
    """Placement / profile line: descriptive text for the given subject."""
    subj = (subject or "English").lower()
    if subj in ("русский", "russian", "ru"):
        return russian_level_display_from_score(score)
    return english_level_display_from_score(score)


_LEGACY_LEVEL_TO_CEFR: dict[str, str] = {
    "a1 (beginner)": "A1",
    "beginner": "A1",
    "a1": "A1",
    "a2 (elementary)": "A2",
    "elementry (a2)": "A2",
    "elementary": "A2",
    "a2": "A2",
    "b1 (pre intermediate)": "B1",
    "b1 (intermediate)": "B1",
    "pre intermediate": "B1",
    "intermediate": "B1",
    "b1": "B1",
    "b2 (upper-intermediate)": "B2",
    "upper intermediate": "B2",
    "upper-intermediate": "B2",
    "b2": "B2",
    "c1 (advanced)": "C1",
    "advanced": "C1",
    "c1": "C1",
    "mixed": "MIXED",
}


def normalize_level_to_cefr(level: str | None) -> str:
    """
    Map stored user/group level strings to CEFR codes for English-track logic.
    Legacy display strings (e.g. 'A1 (Beginner)') map to A1..C1.
    Non-English Russian tier strings are returned unchanged (vocab treats unknown as 'all levels').
    """
    if level is None:
        return "A1"
    s = str(level).strip()
    if not s:
        return "A1"
    paren = re.match(r"^([ABC][12]|C1)\s*\(", s, re.IGNORECASE)
    if paren:
        return paren.group(1).upper()
    su = s.upper().replace(" ", "")
    if su in ("A1", "A2", "B1", "B2", "C1"):
        return su
    if su == "MIXED":
        return "MIXED"
    sl = re.sub(r"\s+", " ", s.lower().strip())
    if sl in _LEGACY_LEVEL_TO_CEFR:
        return _LEGACY_LEVEL_TO_CEFR[sl]
    # Cyrillic or other non-CEFR: pass through
    if re.search(r"[\u0400-\u04ff]", s):
        return s
    return "A1"


def russian_tier_text_to_cefr_code(s: str | None) -> str | None:
    """Map Russian tier phrases (DB/UI) to CEFR-style codes used in daily_tests_bank."""
    low = (s or "").lower().replace("ё", "е")
    if "продвинут" in low or "б2" in low:
        return "B2"
    if "средн" in low or "б1" in low:
        return "B1"
    if "базов" in low or "а2" in low:
        return "A2"
    if "началь" in low:
        return "A1"
    if "элементар" in low:
        return "A2"
    return None


def level_for_daily_tests_bank(subject: str | None, level: str | None) -> str:
    """Normalize stored group/user level to keys in daily_tests_bank (Russian tiers -> A1/A2/B1/B2)."""
    subj = (subject or "").strip().title()
    raw = (level or "").strip()
    if not raw:
        return "A1"
    if subj == "Russian":
        ru = russian_tier_text_to_cefr_code(raw)
        if ru:
            return ru
        c = normalize_level_to_cefr(raw)
        if c in ("A1", "A2", "B1", "B2", "C1"):
            return c
        return "A1"
    c = normalize_level_to_cefr(raw)
    if c in ("A1", "A2", "B1", "B2", "C1", "MIXED"):
        return c
    return "A1"


def compute_level(score: int, subject: str = "English"):
    # score is stored as 10 points per correct answer
    subj = (subject or "English").lower()
    if subj in ("русский", "russian", "ru"):
        return russian_level_display_from_score(score)
    return english_cefr_code_from_score(score)


def create_user_sync(
    first_name: str,
    last_name: str,
    phone: str,
    subject: str,
    login_type: int,
    owner_admin_id: int | None = None,
):
    """Create user with secure login ID generation"""
    max_attempts = 10
    login_id = None
    
    for attempt in range(max_attempts):
        candidate = generate_login_id(login_type=login_type)
        
        # Validate the generated login ID
        validation = validate_login_id(candidate)
        if not validation['valid']:
            logger.warning(f"Generated invalid login ID: {candidate} - {validation['errors']}")
            continue
        
        # Check if login_id already exists
        if not get_user_by_login_id(candidate):
            login_id = candidate
            # Audit the login ID
            audit_result = audit_login_id(login_id, f"create_user_sync: {first_name} {last_name}")
            if audit_result['requires_attention']:
                logger.warning(f"Login ID requires attention: {audit_result}")
            break
        else:
            logger.info(f"Login ID collision detected: {candidate}")
    
    if not login_id:
        raise ValueError(f'Login ID generation failed after {max_attempts} attempts')

    password = generate_password(6)
    result = create_user(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        subject=subject,
        login_type=login_type,
        owner_admin_id=owner_admin_id,
    )
    # Update with generated login_id and password
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        UPDATE users SET login_id=?, password=? WHERE id=?
    ''', (login_id, password, result['id']))
    conn.commit()
    conn.close()
    
    logger.info(f"Created user with secure login ID: {login_id}")
    return {
        'id': result['id'],
        'login_id': login_id,
        'password': password,
        'first_name': first_name,
        'last_name': last_name,
        'phone': phone,
        'subject': subject,
        'login_type': login_type,
    }


def verify_login(login_id: str, password: str):
    return db_verify_login(login_id, password)


def activate_user(user_id: int, telegram_id: str):
    return db_activate_user(user_id, telegram_id)


def reset_user(login_id: str):
    user = get_user_by_login_id(login_id)
    if not user:
        return False
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE users SET blocked=0, failed_logins=0 WHERE login_id=?', (login_id,))
    conn.commit()
    conn.close()
    return True


def login_user(user_id: int, telegram_id: str = None):
    """Log in user and start session"""
    conn = get_conn()
    cur = conn.cursor()
    
    now = get_current_time_iso()
    
    # Update session info
    cur.execute('''
        UPDATE users 
        SET logged_in=1, last_activity=?, session_started=?, failed_logins=0
        WHERE id=?
    ''', (now, now, user_id))
    
    # Update telegram_id if provided
    if telegram_id:
        cur.execute('UPDATE users SET telegram_id=? WHERE id=?', (telegram_id, user_id))
    
    conn.commit()
    conn.close()
    return True


def logout_user(user_id: int):
    """Log out user and end session"""
    conn = get_conn()
    cur = conn.cursor()
    
    now = get_current_time_iso()
    
    # Update login status and add logout_time
    cur.execute('''
        UPDATE users 
        SET logged_in=0, logout_time=?
        WHERE id=?
    ''', (now, user_id))
    
    conn.commit()
    conn.close()
    return True


def is_user_logged_in(user_id: int) -> bool:
    """Check if user is logged in"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT logged_in FROM users WHERE id=?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        return False
    return bool(result["logged_in"] if isinstance(result, dict) or hasattr(result, "keys") else result[0])


def update_user_activity(user_id: int):
    """Update user's last activity timestamp"""
    conn = get_conn()
    cur = conn.cursor()
    now = get_current_time_iso()
    cur.execute('UPDATE users SET last_activity=? WHERE id=?', (now, user_id))
    conn.commit()
    conn.close()


def check_session_timeout(user_id: int, timeout_minutes: int = 20160) -> bool:  # 14 days = 14 * 24 * 60 = 20160 minutes
    """Session policy: keep active until explicit logout."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT logged_in FROM users WHERE id=?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        return False
    return bool(result["logged_in"] if isinstance(result, dict) or hasattr(result, "keys") else result[0])


def verify_login_with_type(login_id: str, password: str, expected_login_type: int):
    """Verify login and check if user type matches expected type"""
    user, _status = db_verify_login(login_id, password)
    if not user:
        return None
    # Allow student bot to accept both login_type 1 and 2 (legacy/variants)
    if expected_login_type == 2:
        if user.get('login_type') not in (1, 2):
            return None
    else:
        if user.get('login_type') != expected_login_type:
            return None
    
    return user


def verify_login_with_type_and_status(login_id: str, password: str, expected_login_type: int):
    """Verify login and return rich status for better UX messages."""
    user, status = db_verify_login(login_id, password)
    if not user:
        return None, status
    if expected_login_type == 2:
        if user.get('login_type') not in (1, 2):
            return None, 'wrong_type'
    else:
        if user.get('login_type') != expected_login_type:
            return None, 'wrong_type'
    return user, 'ok'


def get_user_by_telegram_safe(telegram_id: str):
    """Get user by telegram_id safely"""
    try:
        return get_user_by_telegram(telegram_id)
    except Exception:
        return None


def restore_sessions_on_startup():
    """Restore sessions on restart without forcing re-login."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all users who were logged in before restart
    cur.execute('SELECT id, telegram_id, last_activity FROM users WHERE logged_in=1 AND telegram_id IS NOT NULL')
    logged_in_users = cur.fetchall()
    
    restored_count = 0
    now_iso = get_current_time_iso()
    
    for user in logged_in_users:
        user_id = user['id']
        telegram_id = user['telegram_id']
        last_activity = user['last_activity']
        
        try:
            # Keep session until user explicitly logs out.
            # Also normalize empty last_activity to avoid downstream checks failing.
            if not last_activity:
                cur.execute(
                    "UPDATE users SET last_activity=? WHERE id=? AND logged_in=1",
                    (now_iso, user_id),
                )
            restored_count += 1
        except Exception:
            restored_count += 1
    
    conn.commit()
    conn.close()
    
    # 60 kunlik tozalash
    cleanup_inactive_accounts()
    
    print("✅ Sessions restored + 14/60 kunlik cleanup bajarildi")
    return restored_count


def validate_user_session(user_id: int) -> bool:
    """Validate session for middleware (no auto-timeout)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT logged_in FROM users WHERE id=?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        return False
    return bool(result["logged_in"] if isinstance(result, dict) or hasattr(result, "keys") else result[0])


def delete_inactive_accounts():
    """Delete accounts that have been inactive for 60 days from last_activity"""
    conn = get_conn()
    cur = conn.cursor()
    
    now = get_current_time()
    cutoff_date = now - timedelta(days=60)  # 60 days from last_activity
    
    # Find users inactive for 60+ days (both logged out and never logged in)
    cur.execute('''
        SELECT id, telegram_id, first_name, last_name, last_activity 
        FROM users 
        WHERE last_activity IS NOT NULL AND last_activity < ?
    ''', (cutoff_date.isoformat(),))
    
    inactive_users = cur.fetchall()
    deleted_count = 0
    
    for user in inactive_users:
        user_id = user['id']
        # Delete user from all related tables
        try:
            # Delete from user_groups
            cur.execute('DELETE FROM user_groups WHERE user_id=?', (user_id,))
            # Delete from test_results
            cur.execute('DELETE FROM test_results WHERE user_id=?', (user_id,))
            # Delete from attendance
            cur.execute('DELETE FROM attendance WHERE user_id=?', (user_id,))
            # Delete from diamonds
            cur.execute('DELETE FROM diamonds WHERE user_id=?', (user_id,))
            # Delete from grammar_attempts
            cur.execute('DELETE FROM grammar_attempts WHERE user_id=?', (user_id,))
            # Delete from vocabulary_preferences
            cur.execute('DELETE FROM vocabulary_preferences WHERE user_id=?', (user_id,))
            # Finally delete user
            cur.execute('DELETE FROM users WHERE id=?', (user_id,))
            deleted_count += 1
            logger.info(f"Deleted inactive user {user_id} (inactive for 60+ days)")
        except Exception:
            # If deletion fails, skip this user
            pass
    
    conn.commit()
    conn.close()
    return deleted_count


def cleanup_inactive_accounts():
    """Cleanup accounts that have been inactive for 60 days from last_activity - can be called periodically"""
    try:
        # First, migrate existing logged out users
        migrate_logout_time_column()
        
        # Then delete inactive accounts
        deleted = delete_inactive_accounts()
        if deleted > 0:
            print(f"[CLEANUP] Deleted {deleted} inactive accounts (inactive for 60+ days)")
        return deleted
    except Exception as e:
        print(f"[CLEANUP] Error deleting inactive accounts: {e}")
        return 0


def migrate_logout_time_column():
    """Migrate existing logged out users to use logout_time column"""
    conn = get_conn()
    cur = conn.cursor()
    # For users who are already logged out, set logout_time to last_activity
    cur.execute('''
        UPDATE users 
        SET logout_time = last_activity 
        WHERE logged_in = 0 
        AND logout_time IS NULL 
        AND last_activity IS NOT NULL
    ''')
    
    migrated_count = cur.rowcount
    conn.commit()
    conn.close()
    
    if migrated_count > 0:
        logger.info(f"Migrated {migrated_count} users to use logout_time column")
    
    return migrated_count


def auto_logout_inactive_users():
    """Automatically log out users who have been inactive for 14 days"""
    conn = get_conn()
    cur = conn.cursor()
    
    now = get_current_time()
    cutoff_date = now - timedelta(days=14)
    
    # Find users logged in but inactive for 14+ days
    cur.execute('''
        SELECT id, telegram_id, first_name, last_name, last_activity 
        FROM users 
        WHERE logged_in=1 AND last_activity < ?
    ''', (cutoff_date.isoformat(),))
    
    inactive_users = cur.fetchall()
    logged_out_count = 0
    
    for user in inactive_users:
        user_id = user['id']
        try:
            logout_user(user_id)
            logged_out_count += 1
            print(f"[AUTO-LOGOUT] User {user_id} logged out due to 14+ days inactivity")
        except Exception as e:
            print(f"[AUTO-LOGOUT] Error logging out user {user_id}: {e}")
    
    conn.commit()
    conn.close()
    
    if logged_out_count > 0:
        print(f"[AUTO-LOGOUT] Logged out {logged_out_count} inactive users (14+ days)")
    
    return logged_out_count


def run_periodic_cleanup():
    """Run cleanup tasks - should be called every 48 hours"""
    print(f"[CLEANUP] Starting periodic cleanup at {datetime.now()}")
    
    # Auto-logout inactive users (14 days)
    auto_logout_inactive_users()
    
    # Delete inactive accounts (60 days from last_activity)
    cleanup_inactive_accounts()

    # Daily tests retention (4 days)
    try:
        from db import cleanup_expired_daily_tests
        deleted_daily = cleanup_expired_daily_tests(days=4)
        if deleted_daily > 0:
            print(f"[CLEANUP] Daily tests cleanup: deleted {deleted_daily} expired bank items")
    except Exception as e:
        print(f"[CLEANUP] Daily tests cleanup error: {e}")
    
    print(f"[CLEANUP] Periodic cleanup completed at {datetime.now()}")


# ============== MOVED FROM auth_middleware.py ==============

from i18n import t, detect_lang_from_user

async def process_login_message(message, expected_login_type: int):
    """Process login message and authenticate user (two-step: login_id then password)"""
    from aiogram.types import Message
    text = message.text.strip() if message.text else ''
    telegram_id = str(message.from_user.id)
    lang = detect_lang_from_user(message.from_user)
    
    # Get current login state
    login_state = get_login_state(telegram_id)
    
    # Check if user is entering login_id (first step)
    if not login_state.get('login_id'):
        # First step: asking for login_id
        login_id = text.strip()
        
        # Validate login_id format (basic check)
        if len(login_id) < 3:
            await message.answer(t(lang, 'login_id_too_short'))
            return False
        
        # Check if login_id exists and get user type
        from db import get_user_by_login_id
        user = get_user_by_login_id(login_id)
        
        if not user:
            await message.answer(t(lang, 'login_credentials_error'))
            return False
        
        # Check if user type matches this bot
        logger.info(f"Login validation: user_type={user.get('login_type')}, expected_type={expected_login_type}")
        
        if expected_login_type == 2:
            # Student bot: accept both login_type 1 and 2
            if user.get('login_type') not in (1, 2):
                await message.answer(t(lang, 'wrong_bot_type_teacher'), parse_mode='HTML')
                return False
        else:
            # Non-student bots require exact match
            if user.get('login_type') != expected_login_type:
                logger.info(f"Login type mismatch: got {user.get('login_type')}, expected {expected_login_type}")
                if user.get('login_type') in (1, 2):
                    # Student trying to login to teacher bot
                    await message.answer(t(lang, 'wrong_bot_type_student'), parse_mode='HTML')
                else:
                    # Teacher trying to login to student bot
                    await message.answer(t(lang, 'wrong_bot_type_teacher'), parse_mode='HTML')
                return False
        
        # Store login_id and ask for password
        set_login_state(telegram_id, {'step': 'ask_password', 'login_id': login_id})
        await message.answer(t(lang, 'enter_password'))
        return False
    
    # User is entering password (second step)
    else:
        password = text.strip()
        login_id = login_state['login_id']
        
        # Verify login with type check
        user, status = verify_login_with_type_and_status(login_id, password, expected_login_type)

        if not user:
            if status == 'blocked':
                await message.answer(t(lang, 'login_blocked_error'))
            elif status == 'wrong_type':
                await message.answer(t(lang, 'wrong_bot_type_student' if expected_login_type == 2 else 'wrong_bot_type_teacher'), parse_mode='HTML')
            else:
                await message.answer(t(lang, 'login_credentials_error'))
            # Clear login state on failed attempt
            clear_login_state(telegram_id)
            return False
        
        # Check if user is blocked
        if user.get('blocked'):
            await message.answer(t(lang, 'login_blocked_error'))
            clear_login_state(telegram_id)
            return False
        
        # Log in user
        try:
            activate_user(user['id'], telegram_id)
        except Exception as e:
            if e.__class__.__name__ in ("IntegrityError", "UniqueViolation"):
                # Telegram id already linked to another account - inform user
                await message.answer(t(lang, 'telegram_already_linked_error'))
                clear_login_state(telegram_id)
                return False
            # Unexpected error during activation
            logger.exception('activate_user failed')
            await message.answer(t(lang, 'system_error_try_later_contact_admin'))
            clear_login_state(telegram_id)
            return False

        clear_login_state(telegram_id)
        await message.answer(t(lang, 'login_success'))
        
        # Check if this is a "new student" account (placement test user) and
        # it is the first time after account preparation.
        # NOTE: `password_used` can be reset on logout, so we also require `login_type==1`
        # to prevent placement test from repeating on subsequent logins.
        if user.get('password_used') == 0 and expected_login_type == 2 and int(user.get('login_type') or 0) == 1:
            # This is a new student, start placement test
            from student_bot import start_placement_test
            try:
                await start_placement_test(int(telegram_id))
            except Exception as e:
                logger.error(f"Error starting placement test for new user {user['id']}: {e}")
                # If placement test fails, send to main menu
                await message.answer(t(lang, 'select_from_menu'))
        
        return True


# ============== AuthMiddleware class (moved from auth_middleware.py) ==============

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class AuthMiddleware(BaseMiddleware):
    """Middleware to handle authentication and session management"""
    
    def __init__(self, bot_type: str, expected_login_type: int):
        """
        bot_type: 'student' or 'teacher'
        expected_login_type: 2 for student, 3 for teacher
        """
        self.bot_type = bot_type
        self.expected_login_type = expected_login_type
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict
    ) -> Any:
        
        # Skip authentication for /start command
        if isinstance(event, Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)

        if self.bot_type == 'student':
            lang = detect_lang_from_user(event.from_user)
            from force_subscribe import check_subscription_and_notify

            if not await check_subscription_and_notify(event.bot, event, lang=lang):
                return
        
        # Get telegram_id
        telegram_id = str(event.from_user.id)
        
        # Check if user is in the middle of login flow (two-step login)
        login_state = get_login_state(telegram_id)
        if login_state.get('step') in ('ask_login', 'ask_password'):
            # User is in login flow, let the bot handlers handle it
            return await handler(event, data)
        
        # Check if user exists and is logged in
        user = get_user_by_telegram_safe(telegram_id)
        
        if not user:
            # User not found, send to login
            await self._send_to_login(event)
            return
        
        # Check if user type matches this bot
        if self.expected_login_type == 2:
            # Student bot accepts both legacy student types 1 and 2
            if user.get('login_type') not in (1, 2):
                await self._send_wrong_bot_type_message(event, user)
                return
        else:
            if user.get('login_type') != self.expected_login_type:
                await self._send_wrong_bot_type_message(event, user)
                return
        
        # Validate session (preserves sessions across restarts)
        if not validate_user_session(user['id']):
            # === 140 KUNLIK TO'LIQ AVTOMATIK O'CHIRISH (startupda ham ishlaydi) ===
            logout_user(user['id'])
            
            await self._send_session_expired_message(event)
            return
        
        # Update activity
        update_user_activity(user['id'])
        
        # For students: check if they are in any active group
        if self.expected_login_type == 2:  # Student bot
            from db import check_user_group_access, auto_block_users_not_in_groups
            if not check_user_group_access(user['id']):
                # Auto-block student if not in any active group
                auto_block_users_not_in_groups()
                await self._send_blocked_no_group_message(event)
                return
        
        # Add user to data
        data['user'] = user
        
        # Continue with handler
        return await handler(event, data)
    
    @staticmethod
    async def _ack_callback_query(event: Message | CallbackQuery) -> None:
        """Inline tugmalar so‘rofka holatida qolmasin."""
        if isinstance(event, CallbackQuery):
            try:
                await event.answer()
            except Exception:
                pass

    async def _send_to_login(self, event: Message | CallbackQuery):
        """Send user to login flow"""
        await self._ack_callback_query(event)
        lang = detect_lang_from_user(event.from_user)
        
        if self.bot_type == 'student':
            title_key = 'student_login_title'
        else:  # teacher
            title_key = 'teacher_login_title'
        
        message = t(lang, title_key) + "\n\n" + t(lang, 'login_instructions')
        
        if isinstance(event, Message):
            await event.answer(message)
        else:
            await event.message.answer(message)
    
    async def _send_wrong_bot_type_message(self, event: Message | CallbackQuery, user: dict):
        """Send message when user tries to access wrong bot type"""
        await self._ack_callback_query(event)
        lang = detect_lang_from_user(event.from_user)
        
        if user.get('login_type') in (1, 2):
            # Student trying to access non-student bot
            message = "❌ Bu login ID o'quvchi uchun! Iltimos <b>Student bot</b>dan foydalaning."
        else:
            # Teacher trying to access student bot
            message = "❌ Bu login ID o'qituvchi uchun! Iltimos <b>Teacher bot</b>dan foydalaning."
        
        if isinstance(event, Message):
            await event.answer(message, parse_mode='HTML')
        else:
            await event.message.answer(message, parse_mode='HTML')
    
    async def _send_blocked_no_group_message(self, event: Message | CallbackQuery):
        """Send message when student is blocked due to not being in any group"""
        await self._ack_callback_query(event)
        lang = detect_lang_from_user(event.from_user)
        
        message = "❌ <b>Guruhga biriktirilmagan!</b>\n\n" \
                 "Siz hech qanday faol guruhga a'zo emassiz.\n" \
                 "Botdan foydalanish uchun admin bilan bog'laning " \
                 "va guruhga biriktirilishini so'rang."
        
        if isinstance(event, Message):
            await event.answer(message, parse_mode='HTML')
        else:
            await event.message.answer(message, parse_mode='HTML')
    
    async def _send_session_expired_message(self, event: Message | CallbackQuery):
        """Send message when session expires"""
        await self._ack_callback_query(event)
        lang = detect_lang_from_user(event.from_user)
        
        message = t(lang, 'session_expired')
        
        if isinstance(event, Message):
            await event.answer(message, parse_mode='HTML')
        else:
            await event.message.answer(message, parse_mode='HTML')
